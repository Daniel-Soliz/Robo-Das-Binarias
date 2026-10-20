"""Testes offline de cotacoes Forex, horarios, frescor e seguranca do feed."""
import io
import json
import unittest
from datetime import datetime,timedelta,timezone
from urllib.error import HTTPError, URLError
from ds_trader.forex_live import (
    FeedError, MarketCandle, parse_payload, analyze, fetch_candles,
    ForexWatcher, PAIRS, reference_forex_open
)

START=datetime(2026,10,20,12,0,tzinfo=timezone.utc)
NOW=START+timedelta(minutes=37,seconds=15)

def make_payload(n=36, pair="EUR/USD", interval="1min", down=False):
    rows=[]
    for i in range(n):
        t=START+timedelta(minutes=i)
        v=1.1200+i*(-.00012 if down else .00012)
        rows.append({"datetime":t.strftime("%Y-%m-%d %H:%M:%S"),
                     "open":f"{v:.6f}","high":f"{v+.00015:.6f}",
                     "low":f"{v-.00005:.6f}","close":f"{v+.00010:.6f}"})
    return {"status":"ok","meta":{"symbol":pair,"interval":interval},
            "values":list(reversed(rows))}


class ParseTests(unittest.TestCase):
    def test_current_closed_ohlc_real_and_trend(self):
        view=parse_payload(make_payload(), "EUR/USD", "1min", now=NOW)
        self.assertEqual(view.pair,"EUR/USD")
        self.assertEqual(view.status,"ATUALIZADO")
        self.assertEqual(len(view.candles),36)
        self.assertEqual(view.trend,"ALTA")
        self.assertEqual(view.last_closed_at,START+timedelta(minutes=36))
        self.assertIn("Medias de 9/21",view.summary)
        self.assertIsNone(view.support)  # nenhum pivo demonstrado; nao inventar

    def test_downtrend(self):
        view=parse_payload(make_payload(down=True),"EUR/USD","1min",now=NOW)
        self.assertEqual(view.trend,"BAIXA")

    def test_discard_open_candle(self):
        data=make_payload(38)
        # Bar das 12:37 existe na API, mas nao pode ser tratado como fechado as 12:37:15.
        view=parse_payload(data,"EUR/USD","1min",now=NOW)
        self.assertEqual(len(view.candles),37)
        self.assertEqual(view.candles[-1].opened,START+timedelta(minutes=36))

    def test_stale_market_never_has_analysis(self):
        view=parse_payload(make_payload(),"EUR/USD","1min",
                           now=NOW+timedelta(days=2))
        self.assertIn("ATRASADO",view.status)
        self.assertEqual(view.trend,"SEM ANALISE")
        self.assertIsNone(view.support)

    def test_gap_clears_previous_context(self):
        data=make_payload()
        data["values"]=[r for r in data["values"] if r["datetime"]!="2026-10-20 12:15:00"]
        view=parse_payload(data,"EUR/USD","1min",now=NOW)
        self.assertEqual(len(view.candles),20)
        self.assertEqual(view.trend,"AGUARDANDO")

    def test_reject_duplicates_wrong_pair_and_bad_ohlc(self):
        data=make_payload()
        data["values"].append(dict(data["values"][0]))
        with self.assertRaisesRegex(FeedError,"duplicados"):
            parse_payload(data,"EUR/USD","1min",now=NOW)
        with self.assertRaisesRegex(FeedError,"Par devolvido"):
            parse_payload(make_payload(pair="GBP/USD"),"EUR/USD","1min",now=NOW)
        data=make_payload()
        data["values"][0]["high"]="0.2"
        with self.assertRaisesRegex(FeedError,"OHLC inconsistentes"):
            parse_payload(data,"EUR/USD","1min",now=NOW)

    def test_reject_api_error_and_insufficient(self):
        with self.assertRaisesRegex(FeedError,"Limite"):
            parse_payload({"status":"error","code":429},"EUR/USD","1min",now=NOW)
        view=parse_payload(make_payload(n=6),"EUR/USD","1min",now=START+timedelta(minutes=7))
        self.assertEqual(view.trend,"AGUARDANDO")
        self.assertFalse(view.support)

    def test_reference_market_hours_sunday_friday_and_break(self):
        # Outubro: NY em UTC-4. Inicio semanal domingo 17h05 em NY.
        def utc(hour, minute, day):
            return datetime(2026,10,day,hour,minute,tzinfo=timezone.utc)
        self.assertFalse(reference_forex_open(utc(20, 30, 18))) # domingo 16:30 NY
        self.assertTrue(reference_forex_open(utc(21, 10, 18)))  # domingo 17:10 NY
        self.assertTrue(reference_forex_open(utc(20, 58, 20)))  # terca 16:58 NY
        self.assertFalse(reference_forex_open(utc(21, 2, 20)))  # terca 17:02 pausa
        self.assertFalse(reference_forex_open(utc(21, 20, 23))) # sexta 17:20 NY
        self.assertFalse(reference_forex_open(utc(15, 0, 24)))  # sabado
        # Com dados ficticios novos durante pausa, nao liberar analise como mercado ativo.
        pause=utc(21,2,20)
        fresh=make_payload(36)
        dt=pause-timedelta(minutes=2)
        for row in fresh["values"]:
            offset=(datetime.strptime(row["datetime"],"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)-START)
            row["datetime"]=(dt-timedelta(minutes=34)+offset).strftime("%Y-%m-%d %H:%M:%S")
        result=parse_payload(fresh,"EUR/USD","1min",now=pause)
        self.assertIn("FORA DO HORARIO",result.status)
        self.assertEqual(result.trend,"SEM ANALISE")

    def test_reject_invalid_future_price(self):
        data=make_payload()
        data["values"][0]["close"]="NaN"
        with self.assertRaisesRegex(FeedError,"OHLC"):
            parse_payload(data,"EUR/USD","1min",now=NOW)
        data=make_payload()
        data["values"][0]["datetime"]="2026-10-20T13:30:00Z"
        with self.assertRaises(FeedError):
            parse_payload(data,"EUR/USD","1min",now=NOW)


class ReadOnlyHttpTests(unittest.TestCase):
    def test_api_request_only_timeseries_no_trades(self):
        requests=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return json.dumps(make_payload()).encode()
        def open_fake(request,timeout):
            requests.append(request)
            self.assertEqual(timeout,12)
            return Response()
        key="TEST-KEY-SO-NOT-SEND"
        result=fetch_candles(key,"EUR/USD","1min",opener=open_fake,now=NOW)
        self.assertEqual(result.trend,"ALTA")
        self.assertEqual(len(requests),1)
        self.assertEqual(requests[0].get_method(),"GET")
        self.assertIn("/time_series?",requests[0].full_url)
        self.assertNotIn("orders",requests[0].full_url)
        self.assertNotIn(key,repr(result))

    def test_http_errors_never_expose_key(self):
        key="SHHH-SUPER-SECRET-TOKEN"
        def bad(req,timeout):
            raise HTTPError(req.full_url,429,"Too Many Requests",{},None)
        with self.assertRaises(FeedError) as caught:
            fetch_candles(key,"EUR/USD","1min",opener=bad)
        self.assertNotIn(key,str(caught.exception))

    def test_invalid_params_and_polling_quota(self):
        with self.assertRaises(FeedError):
            fetch_candles("secret123","INVALID","1min")
        with self.assertRaises(ValueError):
            ForexWatcher("secret123","EUR/USD","1min",refresh_seconds=2)


if __name__=="__main__":
    unittest.main()
