"""Read-only cryptocurrency OHLC via Kraken's unauthenticated public API.

This is Kraken's spot market, NOT an IQ Option quote or a synthetic OTC pair.
No authenticated endpoints, trading operations, or user accounts are used.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from ds_trader.forex_live import (
    AssetSpec, FeedError, RateLimitError, MarketCandle, MarketView,
    INTERVALS, MAX_CANDLES, _price, analyze, fetch_asset_candles,
)


KRAKEN_PUBLIC_OHLC = "https://api.kraken.com/0/public/OHLC"
KRAKEN_SOURCE = "Kraken Spot público"
# Names deliberately mapped only for pairs with an identical USD quote asset.
# Never silently substitute a stablecoin pair (USDT, USDC) for USD.
KRAKEN_PAIRS = {
    "BTC/USD": "XBTUSD", "ETH/USD": "ETHUSD", "SOL/USD": "SOLUSD",
    "XRP/USD": "XRPUSD", "ADA/USD": "ADAUSD", "DOGE/USD": "DOGEUSD",
    "LTC/USD": "LTCUSD",
}
# Kraken may return its internal pair key (XXBTZUSD) instead of the
# requested public altname (XBTUSD). Never accept an unrelated sole key:
# otherwise ETH candles could be silently displayed as BTC/USD.
KRAKEN_RESULT_KEYS = {
    "BTC/USD": frozenset(("XXBTZUSD", "XBTUSD")),
    "ETH/USD": frozenset(("XETHZUSD", "ETHUSD")),
    "SOL/USD": frozenset(("SOLUSD",)),
    "XRP/USD": frozenset(("XXRPZUSD", "XRPUSD")),
    "ADA/USD": frozenset(("ADAUSD",)),
    "DOGE/USD": frozenset(("XXDGZUSD", "XDGUSD", "DOGEUSD")),
    "LTC/USD": frozenset(("XLTCZUSD", "LTCUSD")),
}


def parse_kraken_ohlc(payload, spec: AssetSpec, interval: str, *, now=None,
                     history_candles=MAX_CANDLES):
    if spec.category != "CRYPTO" or spec.symbol not in KRAKEN_PAIRS or interval not in INTERVALS:
        raise FeedError("Par de criptomoeda nao suportado pela fonte publica configurada")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Relogio requer fuso UTC")
    now = now.astimezone(timezone.utc)
    if not isinstance(payload, dict) or not isinstance(payload.get("error"), list):
        raise FeedError("Resposta Kraken incompleta")
    if payload["error"]:
        message = " ".join(str(v) for v in payload["error"])
        if "rate limit" in message.lower():
            raise RateLimitError("Fonte publica atingiu o limite de consultas")
        raise FeedError("Par Kraken nao suportado ou consulta indisponivel")
    result = payload.get("result")
    if not isinstance(result, dict) or len([k for k in result if k != "last"]) != 1:
        raise FeedError("Resposta Kraken sem um unico ativo identificado")
    response_key, entries = next((key, value) for key, value in result.items()
                                 if key != "last")
    if response_key not in KRAKEN_RESULT_KEYS[spec.symbol]:
        raise FeedError("Ativo Kraken divergente do par solicitado")
    if not isinstance(entries, list) or not (2 <= len(entries) <= 721):
        raise FeedError("Candles Kraken indisponiveis ou formato invalido")
    # Kraken explicitly documents that the final OHLC is the open candle.
    # Exclude it unconditionally, even if the clock appears to have advanced.
    seen = set()
    closed = []
    seconds = INTERVALS[interval]
    for raw in entries[:-1]:
        if not isinstance(raw, (list, tuple)) or len(raw) < 5:
            raise FeedError("Candle Kraken incompleto")
        timestamp = raw[0]
        if type(timestamp) not in (int, float) or timestamp <= 0:
            raise FeedError("Horario Kraken invalido")
        opened = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        if opened in seen:
            raise FeedError("Candles Kraken duplicados")
        seen.add(opened)
        op, hi, lo, cl = (_price(item) for item in raw[1:5])
        if lo > min(op, cl) or hi < max(op, cl) or hi < lo:
            raise FeedError("OHLC Kraken inconsistente")
        if opened + timedelta(seconds=seconds) <= now:
            closed.append(MarketCandle(opened, op, hi, lo, cl))
    if not closed:
        raise FeedError("Sem candle Kraken comprovadamente fechado")
    if any(a.opened >= b.opened for a, b in zip(closed, closed[1:])):
        raise FeedError("Candles Kraken fora de ordem")
    if not 25 <= history_candles <= 288:
        raise FeedError("Historico Kraken fora do limite")
    closed = closed[-history_candles:]
    age = (now - (closed[-1].opened + timedelta(seconds=seconds))).total_seconds()
    status = ("ATUALIZADO" if 0 <= age <= max(180, 3 * seconds)
              else "ATRASADO / MERCADO SEM NOVAS COTACOES")
    beginning = len(closed) - 1
    while (beginning > 0 and
           (closed[beginning].opened - closed[beginning - 1].opened).total_seconds() == seconds):
        beginning -= 1
    consecutive = tuple(closed[beginning:])
    trend, support, resistance, zone, summary = analyze(consecutive, status)
    return MarketView(spec.symbol, interval, consecutive, now,
                      closed[-1].opened + timedelta(seconds=seconds), age,
                      status, summary, trend, support, resistance, zone,
                      source=KRAKEN_SOURCE, category="CRYPTO")


def fetch_public_crypto_candles(_api_key: str, spec: AssetSpec, interval: str, *,
                                opener=None, timeout=8, now=None,
                                history_candles=MAX_CANDLES):
    if spec.category != "CRYPTO":
        raise FeedError("Forex intradiario nao possui fonte publica gratuita neste modo")
    if spec.symbol not in KRAKEN_PAIRS or interval not in INTERVALS:
        raise FeedError("Par nao suportado pela fonte Kraken publica")
    params = urlencode({"pair": KRAKEN_PAIRS[spec.symbol],
                        "interval": INTERVALS[interval] // 60})
    request = Request(KRAKEN_PUBLIC_OHLC + "?" + params,
                      headers={"Accept": "application/json", "User-Agent": "DS-Trader/1.1"},
                      method="GET")
    try:
        with (opener or urlopen)(request, timeout=timeout) as conn:
            raw = conn.read(1_000_001)
        if len(raw) > 1_000_000:
            raise FeedError("Resposta Kraken excessivamente grande")
        payload = json.loads(raw)
    except HTTPError as exc:
        if exc.code == 429:
            raise RateLimitError("Fonte publica atingiu limite de consultas") from None
        if exc.code in (400, 404):
            raise FeedError("Par nao suportado pela fonte Kraken publica") from None
        raise FeedError(f"Falha HTTP {exc.code} no fornecedor Kraken") from None
    except (URLError, TimeoutError, OSError):
        raise FeedError("Sem conexao com a fonte publica Kraken") from None
    except (ValueError, UnicodeDecodeError):
        raise FeedError("Resposta JSON Kraken invalida") from None
    return parse_kraken_ohlc(payload, spec, interval, now=now,
                             history_candles=history_candles)


def fetch_hybrid_market(api_key: str, spec: AssetSpec, interval: str):
    """Use authenticated provider only when a key was explicitly entered."""
    if api_key.strip():
        return fetch_asset_candles(api_key, spec, interval)
    return fetch_public_crypto_candles("", spec, interval)
