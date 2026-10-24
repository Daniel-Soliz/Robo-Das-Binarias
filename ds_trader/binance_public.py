"""Unauthenticated Binance Spot candles; NEVER the IQ Option broker feed.

Only the public data-api and data-stream hosts are used. A USDT quote is
always labelled USDT, not USD. No order/account endpoints exist here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from ds_trader.forex_live import (AssetSpec, FeedError, RateLimitError,
                                  INTERVALS, MarketCandle, MarketView,
                                  _price, analyze)

REST = "https://data-api.binance.vision/api/v3/klines"
STREAM = "wss://data-stream.binance.vision:443/stream?streams="
REST_SOURCE = "Binance Spot REST público"
WS_SOURCE = "Binance Spot WebSocket público"
MAX_STREAM_SYMBOLS = 10


def _pair_code(spec: AssetSpec) -> str:
    if not isinstance(spec, AssetSpec) or spec.category != "CRYPTO":
        raise FeedError("Binance Spot somente para cripto")
    base, quote = spec.symbol.split("/")
    if quote != "USDT":
        raise FeedError("Fonte Binance configurada somente para pares /USDT")
    return base + quote


def make_binance_stream_url(specs, interval: str) -> str:
    specs = tuple(specs)
    if (interval not in INTERVALS or not specs or
            len(specs) > MAX_STREAM_SYMBOLS or len(set(specs)) != len(specs)):
        raise ValueError("Lista Binance deve conter 1 a 10 pares unicos e periodo valido")
    code = {"1min": "1m", "5min": "5m", "15min": "15m"}[interval]
    return STREAM + "/".join(f"{_pair_code(spec).lower()}@kline_{code}" for spec in specs)


def _time_ms(value):
    if type(value) not in (int, float) or value <= 0:
        raise FeedError("Horario da Binance ausente ou invalido")
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    except (OSError, OverflowError, ValueError) as exc:
        raise FeedError("Horario da Binance fora do intervalo") from exc


def _bar(open_ms, opening, high, low, close):
    at = _time_ms(open_ms)
    op, hi, lo, cl = (_price(v) for v in (opening, high, low, close))
    if lo > min(op, cl) or hi < max(op, cl) or lo > hi:
        raise FeedError("OHLC da Binance inconsistente")
    return MarketCandle(at, op, hi, lo, cl)


class BinanceCandleBook:
    """Source-specific closed candles; no predicted probabilities or trade signals."""

    def __init__(self, spec: AssetSpec, interval: str, *, capacity=120):
        self.code = _pair_code(spec)
        if interval not in INTERVALS:
            raise FeedError("Periodo de Binance invalido")
        if not 25 <= capacity <= 288:
            raise FeedError("Limite de historico Binance invalido")
        self.spec = spec
        self.interval = interval
        self.seconds = INTERVALS[interval]
        self.capacity = capacity
        self.closed: list[MarketCandle] = []

    def _view(self, now, source):
        if not self.closed:
            raise FeedError("Nenhum candle Binance comprovadamente fechado")
        last_close = self.closed[-1].opened + timedelta(seconds=self.seconds)
        age = (now - last_close).total_seconds()
        status = ("ATUALIZADO" if 0 <= age <= max(180, self.seconds * 3)
                  else "ATRASADO / MERCADO SEM NOVAS COTACOES")
        trend, support, resistance, zone, summary = analyze(tuple(self.closed), status)
        return MarketView(self.spec.symbol, self.interval, tuple(self.closed), now,
                          last_close, age, status, summary, trend,
                          support, resistance, zone, source=source, category="CRYPTO")

    def seed(self, view: MarketView):
        if (view.pair != self.spec.symbol or view.interval != self.interval or
                view.category != "CRYPTO"):
            raise FeedError("Historico Binance de outro ativo/periodo")
        self.closed = list(view.candles[-self.capacity:])

    def bootstrap(self, payload, *, now=None):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("Relogio sem fuso horario")
        now = now.astimezone(timezone.utc)
        if not isinstance(payload, list) or not 2 <= len(payload) <= 1000:
            raise FeedError("Historico Binance incompleto")
        clean = []
        seen = set()
        for row in payload:
            if not isinstance(row, (list, tuple)) or len(row) < 7:
                raise FeedError("Barra Binance malformada")
            opened = _time_ms(row[0])
            # Close time is inclusive on Binance; closed one ms after T.
            closed_at = _time_ms(row[6] + 1) if type(row[6]) is int else None
            if closed_at is None or (closed_at - opened).total_seconds() != self.seconds:
                raise FeedError("Duracao de candle Binance inconsistente")
            if closed_at > now:
                continue  # never parse a mutable, unclosed OHLC
            candle = _bar(*row[:5])
            if opened in seen:
                raise FeedError("Candles Binance duplicados")
            seen.add(opened)
            if clean and opened <= clean[-1].opened:
                raise FeedError("Candles Binance fora de ordem")
            clean.append(candle)
        if not clean:
            raise FeedError("Historico Binance sem candles fechados")
        start = len(clean)-1
        while (start > 0 and
               (clean[start].opened - clean[start-1].opened).total_seconds() == self.seconds):
            start -= 1
        self.closed = clean[start:][-self.capacity:]
        return self._view(now, REST_SOURCE)

    def accept(self, event, *, now=None):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("Relogio sem fuso horario")
        now = now.astimezone(timezone.utc)
        if not isinstance(event, dict):
            raise FeedError("Mensagem Binance invalida")
        payload = event.get("data", event)
        if not isinstance(payload, dict) or payload.get("e") != "kline":
            return None
        kline = payload.get("k")
        if not isinstance(kline, dict):
            raise FeedError("Mensagem de candle Binance incompleta")
        expected_interval = {"1min":"1m", "5min":"5m", "15min":"15m"}[self.interval]
        if (payload.get("s") != self.code or kline.get("s") != self.code or
                kline.get("i") != expected_interval):
            return None
        if kline.get("x") is not True:
            return None
        candle = _bar(kline.get("t"), kline.get("o"), kline.get("h"),
                      kline.get("l"), kline.get("c"))
        close_time = _time_ms(kline.get("T") + 1) if type(kline.get("T")) is int else None
        if close_time is None or close_time != candle.opened + timedelta(seconds=self.seconds):
            raise FeedError("Fechamento Binance inconsistente")
        if close_time > now + timedelta(seconds=1):
            raise FeedError("Candle Binance no futuro")
        if self.closed and candle.opened <= self.closed[-1].opened:
            return None
        if (self.closed and
                (candle.opened - self.closed[-1].opened).total_seconds() != self.seconds):
            self.closed = []  # do not bridge a missing candle
        self.closed.append(candle)
        self.closed = self.closed[-self.capacity:]
        return self._view(now, WS_SOURCE)


def fetch_binance_history(spec: AssetSpec, interval: str, *, opener=None,
                          timeout=8, now=None, history_candles=120):
    code = _pair_code(spec)
    if interval not in INTERVALS:
        raise FeedError("Intervalo Binance invalido")
    if not 25 <= history_candles <= 288:
        raise FeedError("Limite de historico Binance invalido")
    params = urlencode({"symbol": code,
                        "interval": {"1min":"1m", "5min":"5m", "15min":"15m"}[interval],
                        "limit": history_candles + 1})
    request = Request(REST + "?" + params,
                      headers={"Accept":"application/json", "User-Agent":"DS-Trader/2.0"},
                      method="GET")
    try:
        with (opener or urlopen)(request, timeout=timeout) as conn:
            raw = conn.read(300_001)
        if len(raw) > 300_000:
            raise FeedError("Historico Binance excessivamente grande")
        payload = json.loads(raw)
    except HTTPError as exc:
        if exc.code in (418, 429):
            raise RateLimitError("Limite da fonte publica Binance; aguarde reconexao") from None
        if exc.code in (400, 404):
            raise FeedError("Par Binance nao suportado pela fonte") from None
        raise FeedError(f"Fonte publica Binance HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise FeedError("Conexao a Binance indisponivel") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise FeedError("JSON Binance invalido") from None
    return BinanceCandleBook(spec, interval, capacity=history_candles).bootstrap(payload, now=now)
