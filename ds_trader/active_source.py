"""M5 active-target history routing; no broker connection or hidden fallback."""
from __future__ import annotations

from ds_trader.binance_public import fetch_binance_history
from ds_trader.forex_live import AssetSpec, FeedError, fetch_asset_candles
from ds_trader.public_crypto import fetch_public_crypto_candles


def fetch_active_history(spec: AssetSpec, *, api_key: str,
                         binance_fetcher=fetch_binance_history,
                         kraken_fetcher=fetch_public_crypto_candles,
                         forex_fetcher=fetch_asset_candles):
    if not isinstance(spec, AssetSpec):
        raise FeedError("Ativo nao identificado")
    if spec.category == "FOREX":
        if not api_key or len(api_key.strip()) < 6:
            raise FeedError("Forex exige uma chave de fonte intradiaria Twelve Data")
        return forex_fetcher(api_key, spec, "5min", history_candles=288)
    if spec.category == "CRYPTO" and spec.symbol.endswith("/USDT"):
        return binance_fetcher(spec, "5min", history_candles=288)
    if spec.category == "CRYPTO" and spec.symbol.endswith("/USD"):
        return kraken_fetcher("", spec, "5min", history_candles=288)
    raise FeedError("Ativo sem fonte publica exata configurada")
