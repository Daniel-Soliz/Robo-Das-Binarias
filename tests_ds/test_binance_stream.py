"""Live Binance stream thread uses bounded queues and fail-closed status."""
from datetime import datetime, timedelta, timezone
from threading import Event
import json
import time

from ds_trader.binance_public import BinanceCandleBook
from ds_trader.binance_stream import BinanceStreamRadar
from ds_trader.forex_live import AssetSpec

NOW = datetime(2026, 10, 24, 12, 40, tzinfo=timezone.utc)
SPEC = AssetSpec("BTC/USDT", "CRYPTO")


def snapshot():
    start = NOW - timedelta(minutes=36)
    history = []
    for i in range(37):
        millis = int((start+timedelta(minutes=i)).timestamp()*1000)
        history.append([millis, "100", "110", "90", "105", "3",
                        millis+59999, "2", 2, "1", "1", "1"])
    return BinanceCandleBook(SPEC, "1min").bootstrap(history, now=NOW)


def stream_event(*, closed=True):
    millis = int(NOW.timestamp()*1000)
    return json.dumps({"stream":"btcusdt@kline_1m", "data": {
        "e":"kline", "s":"BTCUSDT", "E":millis+60000,
        "k":{"t":millis,"T":millis+59999,"s":"BTCUSDT", "i":"1m",
             "x":closed,"o":"100","h":"110","l":"90","c":"104"}}})


def eventually(predicate, timeout=1):
    end = time.monotonic()+timeout
    while time.monotonic()<end:
        if predicate(): return
        time.sleep(.01)
    assert predicate()


def test_live_closed_kline_after_rest_bootstrap_emits_verified_websocket_event():
    calls=[]
    class Socket:
        def __init__(self): self.first=True
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def recv(self, timeout):
            assert timeout <= 1.5
            if self.first:
                self.first=False
                return stream_event()
            raise TimeoutError
    def connect(url, **kwargs):
        calls.append(url)
        return Socket()
    feed = BinanceStreamRadar([SPEC], interval="1min", fetcher=lambda spec, interval: snapshot(),
                              connector=connect, utcnow=lambda: NOW+timedelta(minutes=1))
    try:
        feed.start()
        eventually(lambda: feed.coverage().current == 1 and not feed.events.empty())
        events=[]
        eventually(lambda: len(events) >= 2 or (events.extend(list(feed.drain())) or len(events) >= 2))
        assert any(e.source == "Binance Spot WebSocket público" and e.status == "ATUALIZADO" for e in events)
        assert calls == ["wss://data-stream.binance.vision:443/stream?streams=btcusdt@kline_1m"]
    finally:
        feed.stop()


def test_open_ws_kline_never_becomes_a_new_closed_candle():
    class Socket:
        def __init__(self): self.first=True
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def recv(self, timeout):
            if self.first:
                self.first=False
                return stream_event(closed=False)
            raise TimeoutError
    feed=BinanceStreamRadar([SPEC], interval="1min", fetcher=lambda *_: snapshot(),
                             connector=lambda *args, **kwargs: Socket(),
                             utcnow=lambda: NOW+timedelta(minutes=1))
    try:
        feed.start()
        eventually(lambda: not feed.events.empty())
        time.sleep(.05)
        emitted = list(feed.drain())
        assert len(emitted) == 1
        assert emitted[0].source == "Binance Spot REST público"
    finally:
        feed.stop()


def test_disconnected_stream_marks_source_inactive_before_retry():
    connected = Event()
    def fail(url, **kwargs):
        connected.set()
        raise ConnectionError("internet offline")
    feed = BinanceStreamRadar([SPEC], fetcher=lambda *_: snapshot(), connector=fail,
                              reconnect_seconds=.2, utcnow=lambda:NOW)
    try:
        feed.start()
        assert connected.wait(1)
        eventually(lambda: feed.coverage().failed == 1)
        events=list(feed.drain())
        assert events[-1].snapshot is None
        assert events[-1].status == "ERRO"
        assert "offline" not in events[-1].reason
    finally:
        feed.stop()


def test_stop_during_bootstrap_does_not_publish_late_result():
    entered, release = Event(), Event()
    def slow_fetch(*_):
        entered.set()
        release.wait(2)
        return snapshot()
    feed=BinanceStreamRadar([SPEC], fetcher=slow_fetch,
                             connector=lambda *_args, **_kw: None)
    feed.start()
    assert entered.wait(1)
    start = time.monotonic()
    feed.stop(wait=False)
    assert time.monotonic()-start < .1
    release.set()
    eventually(lambda: not feed.running)
    assert feed.events.empty()


def test_websocket_recovers_after_network_failure_and_rebootstrap():
    attempts = []
    class Socket:
        def __init__(self): self.first = True
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def recv(self, timeout):
            if self.first:
                self.first = False
                return stream_event()
            raise TimeoutError
    def connector(*_args, **_kwargs):
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            raise ConnectionError("temporarily offline")
        return Socket()
    feed = BinanceStreamRadar([SPEC], fetcher=lambda *_: snapshot(),
                              connector=connector,
                              reconnect_seconds=.1,
                              utcnow=lambda: NOW+timedelta(minutes=1))
    seen = []
    try:
        feed.start()
        def recovered():
            seen.extend(feed.drain())
            return any(e.source == "Binance Spot WebSocket público" and
                       e.status == "ATUALIZADO" for e in seen)
        eventually(recovered, timeout=1.4)
        assert len(attempts) >= 2
        assert any(e.status == "ERRO" and e.snapshot is None for e in seen)
    finally:
        feed.stop()


def test_output_queue_is_bounded_under_consumer_backpressure():
    feed = BinanceStreamRadar([SPEC], fetcher=lambda *_: snapshot(), connector=lambda *_a, **_k: None)
    now = NOW
    from ds_trader.market_radar import RadarEvent
    for i in range(300):
        feed._emit(RadarEvent(SPEC.symbol, SPEC.category, "ERRO", None, now,
                              "Binance Spot WebSocket público", str(i)))
    assert feed.events.qsize() <= 4
    assert feed.drain()[-1].reason == "299"
