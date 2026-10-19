import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from dataclasses import replace, asdict
from datetime import timedelta
from unittest.mock import patch
from ds_trader.data import parse_csv, DataError, instant
from ds_trader.demo import demo_csv
from ds_trader.strategy import Parameters, Strategy
from ds_trader.simulation import Replay, Settings, settle, metrics
from ds_trader.storage import Store, export_report
from ds_trader.explain import explain

def changed(change):
    reader=csv.DictReader(io.StringIO(demo_csv()));fields=reader.fieldnames;rows=list(reader)
    change(rows)
    out=io.StringIO();w=csv.DictWriter(out,fields);w.writeheader();w.writerows(rows)
    return out.getvalue()

def bars():return next(iter(parse_csv(demo_csv()).groups.values()))

class ImportTests(unittest.TestCase):
    def test_valid_and_volume_optional(self):
        b=bars();self.assertEqual(len(b),200);self.assertIsNone(b[0].volume)
    def test_timezone_conversion(self):
        self.assertEqual(instant('2025-01-01T09:00:00-03:00'),instant('2025-01-01T12:00:00Z'))
    def test_bad_files(self):
        mutations=[lambda r:r.insert(1,r[0]),lambda r:r.reverse(),lambda r:r.pop(3),
                   lambda r:r[0].update(high='0.1'),lambda r:r[0].update(open='nan'),
                   lambda r:r[0].update(timestamp='2025-01-01T12:00:00'),
                   lambda r:r[0].update(interval_seconds='0'),lambda r:r[0].update(volume='-1'),
                   lambda r:r[0].update(asset='EURUSD-OTC'),lambda r:r[0].update(payout='1.2'),
                   lambda r:r[0].update(payout_known_at='2030-01-01T12:00:00Z'),
                   lambda r:r[0].update(timestamp='2099-01-01T12:00:00Z'),
                   lambda r:r[0].update(open_time='2025-01-06T12:02:00Z')]
        for mutate in mutations:
            with self.subTest(mutation=mutate),self.assertRaises(DataError):parse_csv(changed(mutate))
    def test_header_and_empty(self):
        for raw in ('','timestamp,open\n','timestamp,asset,source,market,interval_seconds,open,high,low,close\n'):
            with self.assertRaises(DataError):parse_csv(raw)
    def test_sources_and_otc_separate(self):
        def mutate(r):
            extra=[dict(x,market='OTC',source='OUTRA',asset='DEMO-EURUSD-OTC') for x in r]
            r.extend(extra)
        self.assertEqual(len(parse_csv(changed(mutate)).groups),2)
    def test_missing_quotes_accepted_not_fabricated(self):
        def mutate(r):
            for row in r:row.update(open_time='',payout='',payout_known_at='')
        b=next(iter(parse_csv(changed(mutate)).groups.values()))
        r=Replay(b,Parameters(),Settings()).run()
        self.assertTrue(r.trades);self.assertTrue(all(t['result']=='INDETERMINADA' for t in r.trades))

class StrategyTests(unittest.TestCase):
    def test_pivot_confirmation_and_symmetric_signals(self):
        b=bars();s=Strategy(Parameters())
        for x in b[:4]:s.step(x)
        self.assertEqual(s.zones,[])
        s.step(b[4]);self.assertTrue(any(z['type']=='resistencia' for z in s.zones))
        for x in b[5:]:s.step(x)
        self.assertEqual({e['direction'] for e in s.events if e['status']=='SINAL'},{'ALTA','BAIXA'})
    def test_every_prefix_identical_no_future_leakage(self):
        b=bars()[:45];full=Strategy(Parameters())
        for x in b:full.step(x)
        for n in range(1,len(b)+1):
            s=Strategy(Parameters())
            for x in b[:n]:s.step(x)
            self.assertEqual(s.events,[e for e in full.events if instant(e['time'])<=b[n-1].end])
    def test_no_duplicate_or_gap_processing(self):
        b=bars();s=Strategy(Parameters());s.step(b[0])
        with self.assertRaises(ValueError):s.step(b[0])
        with self.assertRaises(ValueError):s.step(b[2])
    def test_invalidated_retest(self):
        b=bars()[:12];s=Strategy(Parameters())
        for x in b[:10]:s.step(x)
        self.assertIsNotNone(s.pending)
        bad=replace(b[10],candle=replace(b[10].candle,abertura=.999,fechamento=.999,maxima=1.000,minima=.998))
        s.step(bad);self.assertEqual(s.events[-1]['status'],'INVALIDADO')
    def test_expired_retest(self):
        b=bars()[:14];s=Strategy(Parameters(retest_bars=1))
        for x in b[:10]:s.step(x)
        for x in b[10:12]:s.step(replace(x,candle=replace(x.candle,abertura=1.002,maxima=1.004,minima=1.002,fechamento=1.003)))
        self.assertEqual(s.events[-1]['status'],'INVALIDADO')
    def test_parameter_validation(self):
        for kwargs in ({'left':0},{'width':float('nan')},{'min_touches':1},{'right':1.5}):
            with self.assertRaises(ValueError):Parameters(**kwargs)

class SimulationTests(unittest.TestCase):
    def test_payoffs_and_ties(self):
        self.assertEqual(settle('ALTA',1,2,.8,10,'refund'),('ACERTO',8))
        self.assertEqual(settle('BAIXA',1,2,.8,10,'refund'),('ERRO',-10))
        self.assertEqual(settle('ALTA',1,1,.8,10,'refund'),('EMPATE',0))
        self.assertEqual(settle('BAIXA',1,1,.8,10,'loss'),('EMPATE',-10))
    def test_delayed_entry_and_exact_expiry(self):
        r=Replay(bars(),Parameters(),Settings()).run()
        self.assertTrue(r.trades)
        for t in r.trades:
            if t['entry_time']:
                self.assertGreater(instant(t['entry_time']),instant(t['time']))
                self.assertEqual((instant(t['expiry'])-instant(t['entry_time'])).total_seconds(),120)
        ind=Replay(bars(),Parameters(),Settings(duration=61)).run()
        self.assertTrue(all(t['result']=='INDETERMINADA' for t in ind.trades))
    def test_hypothetical_payout(self):
        b=[replace(x,payout=None,payout_known_at=None) for x in bars()]
        r=Replay(b,Parameters(),Settings(payout=.6)).run()
        self.assertTrue(all(t['payout']==.6 and 'HIPOTÉTICO' in t['payout_type'] for t in r.trades))
    def test_variable_payout_drawdown_streak_wilson(self):
        ts=[]
        for direction,end,payout in [('ALTA',2,.8),('ALTA',0,.7),('ALTA',0,.9),('BAIXA',0,.6)]:
            result,pnl=settle(direction,1,end,payout,10,'refund');ts.append(dict(result=result,pnl=pnl,payout=payout,entry_time='x'))
        m=metrics(ts)
        self.assertEqual(m['net'],-6);self.assertEqual(m['max_drawdown'],20);self.assertEqual(m['max_loss_streak'],2)
        self.assertIsNone(m['break_even']);self.assertAlmostEqual(m['win_rate'],.5)
        self.assertTrue(m['wilson_95'][0]<.5<m['wilson_95'][1]);self.assertIsNone(metrics([])['win_rate'])
    def test_no_reveal_before_settlement(self):
        r=Replay(bars(),Parameters(),Settings())
        while r.step():
            now=r.bars[r.index-1].end
            for t in r.trades:
                if t['pnl'] is not None:self.assertLessEqual(instant(t['expiry']),now)
    def test_one_operation_and_no_repeated_signals(self):
        r=Replay(bars(),Parameters(),Settings(duration=600)).run()
        keys=[(t['time'],t['zone_id'],t['phase']) for t in r.trades]
        self.assertEqual(len(keys),len(set(keys)))
        for a,b in zip(r.trades,r.trades[1:]):
            if a['phase']==b['phase'] and a['expiry']:
                self.assertLessEqual(instant(a['expiry']),instant(b['time']))
    def test_holdout_and_frozen_parameters(self):
        r=Replay(bars(),Parameters(),Settings()).run()
        cutoff=r.bars[r.cut].candle.instante
        for t in r.trades:
            if t['phase']=='TESTE':self.assertGreater(instant(t['time']),cutoff)
            elif t['pnl'] is not None:self.assertLessEqual(instant(t['expiry']),cutoff)
        self.assertEqual(r.report()['parameters'],asdict(Parameters()))
    def test_offline_and_ai_absent(self):
        with patch('socket.socket',side_effect=RuntimeError('Rede indisponível')):
            r=Replay(bars(),Parameters(),Settings()).run()
            self.assertTrue(explain(r.events[0]));self.assertTrue(r.finished)
    def test_stop_and_repeat(self):
        r=Replay(bars(),Parameters(),Settings());r.step();r.finish()
        self.assertFalse(r.step());self.assertEqual(r.index,1)

class StorageTests(unittest.TestCase):
    def test_persistence_backup_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'store.sqlite3';s=Store(db)
            report=Replay(bars(),Parameters(),Settings()).run().report()
            id=s.save(report);s.save_config({'payout':.7});s.close()
            s=Store(db);self.assertEqual(s.get(id),report);self.assertEqual(s.config()['payout'],.7)
            backup=Path(tmp)/'backup.sqlite3';s.backup(backup);s.close()
            s=Store(backup);self.assertEqual(s.get(id),report);s.close()
            out=Path(tmp)/'report.json';export_report(report,out)
            self.assertEqual(json.loads(out.read_text(encoding='utf-8')),report)
            self.assertTrue(out.with_name('report_trades.csv').exists())
    def test_csv_formula_safety(self):
        from ds_trader.storage import safe_cell
        self.assertEqual(safe_cell('=1+1'),"'=1+1")

if __name__=='__main__':unittest.main()
