"""Offline MT5 adapter tests. These do NOT prove live quotes or IQ Option parity."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from ds_trader.mt5_readonly import MT5DataError, MT5ReadOnlyFeed

NOW = datetime(2026, 10, 29, 20, 10, 10, tzinfo=timezone.utc)


def bars(count=60, now=NOW):
    start = now.replace(second=0, microsecond=0) - timedelta(minutes=count)
    return [dict(time=int((start + timedelta(minutes=i)).timestamp()),
                 open=1.1, high=1.11, low=1.09, close=1.105)
            for i in range(count)]


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    TIMEFRAME_M1 = 1

    def __init__(self, *, mode=0, connected=True, rows=None):
        self.mode = mode
        self.connected = connected
        self.rows = bars() if rows is None else rows
        self.calls = []

    def initialize(self, *args, **kwargs):
        self.calls.append(("initialize", args, kwargs))
        return True

    def terminal_info(self):
        return SimpleNamespace(connected=self.connected)

    def account_info(self):
        return SimpleNamespace(trade_mode=self.mode)

    def shutdown(self):
        self.calls.append(("shutdown",))

    def symbol_info(self, symbol):
        return SimpleNamespace(name=symbol)

    def symbol_select(self, symbol, select):
        self.calls.append(("symbol_select", symbol, select))
        return True

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        self.calls.append(("copy_rates_from_pos", symbol, timeframe, start, count))
        return self.rows[-count:]


class MT5ReadOnlyTests(unittest.TestCase):
    def feed(self, fake=None, **kwargs):
        fake = fake or FakeMT5()
        return MT5ReadOnlyFeed(mt5=fake, clock=lambda: NOW, **kwargs), fake

    def test_demo_connect_and_closed_candles(self):
        feed, fake = self.feed(terminal_path="C:/MT5/terminal64.exe")
        feed.connect()
        snapshot = feed.read_closed_m1("EUR/USD")
        self.assertEqual(snapshot.pair, "EUR/USD")
        self.assertEqual(len(snapshot.candles), 60)
        self.assertEqual(snapshot.last_closed_at, NOW.replace(second=0))
        self.assertIn(("copy_rates_from_pos", "EURUSD", 1, 1, 60), fake.calls)
        self.assertEqual(fake.calls[0][1], ("C:/MT5/terminal64.exe",))
        feed.close()
        self.assertIn(("shutdown",), fake.calls)

    def test_real_account_rejected(self):
        feed, fake = self.feed(FakeMT5(mode=2))
        with self.assertRaisesRegex(MT5DataError, "DEMO"):
            feed.connect()
        self.assertIn(("shutdown",), fake.calls)

    def test_disconnected_terminal_rejected(self):
        feed, _ = self.feed(FakeMT5(connected=False))
        with self.assertRaisesRegex(MT5DataError, "sem conexao"):
            feed.connect()

    def test_unconfigured_pair_rejected(self):
        feed, _ = self.feed()
        feed.connect()
        with self.assertRaisesRegex(MT5DataError, "nao configurado"):
            feed.read_closed_m1("EUR/JPY")

    def test_stale_candle_rejected(self):
        old = bars(now=NOW - timedelta(minutes=5))
        feed, _ = self.feed(FakeMT5(rows=old))
        feed.connect()
        with self.assertRaisesRegex(MT5DataError, "atrasado"):
            feed.read_closed_m1("EUR/USD")

    def test_future_candle_rejected(self):
        future = bars(now=NOW + timedelta(minutes=1))
        feed, _ = self.feed(FakeMT5(rows=future))
        feed.connect()
        with self.assertRaisesRegex(MT5DataError, "nao confirmado"):
            feed.read_closed_m1("EUR/USD")

    def test_bad_ohlc_rejected(self):
        wrong = bars()
        wrong[-1]["low"] = 1.12
        feed, _ = self.feed(FakeMT5(rows=wrong))
        feed.connect()
        with self.assertRaisesRegex(MT5DataError, "OHLC"):
            feed.read_closed_m1("EUR/USD")

    def test_duplicates_rejected(self):
        duplicate = bars()
        duplicate[-1]["time"] = duplicate[-2]["time"]
        feed, _ = self.feed(FakeMT5(rows=duplicate))
        feed.connect()
        with self.assertRaisesRegex(MT5DataError, "duplicados"):
            feed.read_closed_m1("EUR/USD")

    def test_insufficient_history_rejected(self):
        feed, _ = self.feed(FakeMT5(rows=bars(count=20)))
        feed.connect()
        with self.assertRaisesRegex(MT5DataError, "25 candles"):
            feed.read_closed_m1("EUR/USD")

    def test_maximum_six_pairs(self):
        with self.assertRaisesRegex(ValueError, "seis pares"):
            MT5ReadOnlyFeed(symbols={str(i): str(i) for i in range(7)})

    def test_no_trade_calls(self):
        feed, fake = self.feed()
        feed.connect()
        feed.read_closed_m1("GBP/USD")
        self.assertFalse(any("order" in c[0] for c in fake.calls))


if __name__ == "__main__":
    unittest.main()
