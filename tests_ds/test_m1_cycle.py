"""Fronteiras temporais do ciclo M1, sem rede, ordens ou dados futuros."""
import math
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from ds_trader.m1_cycle import M1Bar, M1History, M1Price, M1Cycle


UTC = timezone.utc
START = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def bullish_history():
    bars = []
    for i in range(33):
        op = 95 + .02 * i + .16 * math.sin(i * .82)
        cl = op + (.045 if i % 2 else -.045)
        bars.append((op, max(op, cl) + .1, min(op, cl) - .1, cl))
    bars.extend(((95.86, 95.9, 95.49, 95.6),
                 (95.52, 96.24, 95.48, 96.12)))
    return M1History(
        asset="EURUSD", source="TEST_FEED", timeframe="M1",
        observed_at=START + timedelta(minutes=35, seconds=30),
        clock_confirmed=True, identity_confirmed=True,
        bars=tuple(M1Bar(START + timedelta(minutes=i), *prices, True)
                   for i, prices in enumerate(bars)),
    )


def price(event_at, value, *, delay=.25, kind="OPEN", **kwargs):
    original = M1Price("EURUSD", "TEST_FEED", "M1", event_at,
                       event_at + timedelta(seconds=delay), value,
                       True, True, True, kind=kind,
                       closed_confirmed=kind == "CLOSE")
    return replace(original, **kwargs)


class M1CycleTests(unittest.TestCase):
    def test_correct_sequence_prepares_activates_then_scores_only_after_expiry(self):
        engine = M1Cycle()
        status = engine.prepare(bullish_history())
        self.assertEqual((status.phase, status.side), ("PENDENTE", "CALL"))
        self.assertEqual(status.target_open, START + timedelta(minutes=36))
        self.assertEqual(status.target_close, START + timedelta(minutes=37))
        self.assertEqual(engine.results, [])

        # No instante de abertura, sem cotacao verificavel, nao existe entrada.
        self.assertEqual(engine.advance(status.target_open).side, "AGUARDAR")
        active = engine.activate(price(status.target_open, 96.0))
        self.assertEqual((active.phase, active.side), ("ATIVA", "CALL"))
        self.assertEqual(engine.results, [])
        self.assertIsNone(active.result)
        result = engine.settle(price(status.target_close, 96.2, kind="CLOSE"))
        self.assertEqual((result.phase, result.result.outcome), ("CONCLUIDA", "ACERTO"))
        self.assertEqual(result.result.opened_at, status.target_open)
        self.assertEqual(result.result.expired_at, status.target_close)
        self.assertEqual(len(engine.results), 1)
        self.assertEqual(engine.settle(price(status.target_close, 80, kind="CLOSE")).result, result.result)
        self.assertEqual(len(engine.results), 1)

    def test_cannot_use_same_boundary_for_last_closed_and_target_open(self):
        entry = M1Cycle().prepare(bullish_history())
        self.assertEqual(entry.target_open, START + timedelta(minutes=36))
        self.assertNotEqual(entry.target_open, bullish_history().bars[-1].opened_at + timedelta(minutes=1))

    def test_last_candle_open_or_future_disqualifies_preparation(self):
        raw = bullish_history()
        scenarios = (
            replace(raw, bars=raw.bars[:-1] + (replace(raw.bars[-1], closed_confirmed=False),)),
            replace(raw, observed_at=START + timedelta(minutes=34, seconds=59)),
            replace(raw, bars=raw.bars[:-1] + (replace(raw.bars[-1], opened_at=START + timedelta(minutes=35)),)),
            replace(raw, bars=raw.bars[:-1] + (replace(raw.bars[-1], close=raw.bars[-1].high + 1),)),
        )
        for history in scenarios:
            with self.subTest(history=history):
                self.assertEqual(M1Cycle().prepare(history).phase, "AGUARDAR")

    def test_asset_period_clock_and_gaps_must_be_confirmed(self):
        raw = bullish_history()
        scenarios = (
            replace(raw, timeframe="M5"),
            replace(raw, asset=""),
            replace(raw, clock_confirmed=False),
            replace(raw, identity_confirmed=False),
            replace(raw, observed_at=raw.observed_at.replace(tzinfo=None)),
            replace(raw, bars=raw.bars[:9] + (replace(raw.bars[9], opened_at=raw.bars[9].opened_at + timedelta(seconds=1)),) + raw.bars[10:]),
        )
        for history in scenarios:
            with self.subTest(history=history):
                self.assertEqual(M1Cycle().prepare(history).side, "AGUARDAR")

    def test_too_late_preparation_and_duplicate_target_are_rejected(self):
        base = bullish_history()
        for seconds in (59.5, 60, 63):
            self.assertEqual(M1Cycle().prepare(replace(base, observed_at=START + timedelta(minutes=35, seconds=seconds))).phase, "AGUARDAR")
        engine = M1Cycle()
        self.assertEqual(engine.prepare(base).phase, "PENDENTE")
        self.assertEqual(engine.advance(START + timedelta(minutes=36, seconds=2)).phase, "AGUARDAR")
        self.assertEqual(engine.prepare(base).phase, "AGUARDAR")

    def test_delayed_unverified_or_mismatched_open_never_activates(self):
        cases = (
            lambda at: price(at, 96, delay=1.1),
            lambda at: replace(price(at, 96), event_at=at + timedelta(seconds=1)),
            lambda at: price(at, 96, price_confirmed=False),
            lambda at: price(at, 96, clock_confirmed=False),
            lambda at: price(at, 96, timeframe="M5"),
            lambda at: price(at, 96, asset="GBPUSD"),
            lambda at: price(at, 96, observed_at=at - timedelta(milliseconds=1)),
            lambda at: price(at, float("nan")),
        )
        for make in cases:
            engine = M1Cycle()
            target = engine.prepare(bullish_history()).target_open
            with self.subTest(make=make):
                self.assertEqual(engine.activate(make(target)).phase, "AGUARDAR")
                self.assertEqual(engine.results, [])

    def test_delayed_or_missing_close_is_indeterminate(self):
        for closing in (None, "late", "unchecked", "unclosed", "wrong_kind", "wrong_boundary"):
            engine = M1Cycle()
            target = engine.prepare(bullish_history()).target_open
            self.assertEqual(engine.activate(price(target, 96)).phase, "ATIVA")
            expiry = target + timedelta(minutes=1)
            if closing is None:
                status = engine.advance(expiry + timedelta(seconds=3))
            elif closing == "late":
                status = engine.settle(price(expiry, 96.5, delay=3, kind="CLOSE"))
            elif closing == "unchecked":
                status = engine.settle(price(expiry, 96.5, kind="CLOSE", price_confirmed=False))
            elif closing == "unclosed":
                status = engine.settle(price(expiry, 96.5, kind="CLOSE", closed_confirmed=False))
            elif closing == "wrong_kind":
                status = engine.settle(price(expiry, 96.5, kind="OPEN"))
            else:
                status = engine.settle(price(expiry + timedelta(minutes=1), 96.5, kind="CLOSE"))
            with self.subTest(closing=closing):
                self.assertEqual(status.phase, "AGUARDAR")
                self.assertIsNone(status.result)
                self.assertEqual(engine.results, [])

    def test_loss_and_equal_close_do_not_fabricate_payout(self):
        for end_price, expected in ((95.0, "ERRO"), (96.0, "EMPATE")):
            engine = M1Cycle()
            target = engine.prepare(bullish_history()).target_open
            engine.activate(price(target, 96.0))
            result = engine.settle(price(target + timedelta(minutes=1), end_price, kind="CLOSE")).result
            self.assertEqual(result.outcome, expected)
            self.assertFalse(hasattr(result, "profit"))

    def test_lost_identity_during_pending_or_active_cancels_cycle(self):
        for phase in ("PENDENTE", "ATIVA"):
            engine = M1Cycle()
            target = engine.prepare(bullish_history()).target_open
            if phase == "ATIVA":
                engine.activate(price(target, 96.0))
            status = engine.prepare(replace(bullish_history(), asset="USDJPY"))
            self.assertEqual(status.phase, "AGUARDAR")
            self.assertEqual(engine.results, [])


if __name__ == "__main__":
    unittest.main()
