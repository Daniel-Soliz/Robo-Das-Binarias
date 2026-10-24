"""Pure UI state: never label offline or stale provider data as live."""
from datetime import datetime, timedelta, timezone

import pytest

from ds_trader.forex_live import AssetSpec, MarketView
from ds_trader.market_radar import RadarCoverage, RadarEvent
from ds_trader.market_radar_ui import (DEFAULT_WATCHLIST, RadarViewModel,
                                       combine_coverages, parse_watchlist,
                                       split_public_sources)


def test_default_watchlist_contains_real_public_usdt_stream_pairs():
    assert AssetSpec("BTC/USDT", "CRYPTO") in DEFAULT_WATCHLIST
    assert AssetSpec("ETH/USDT", "CRYPTO") in DEFAULT_WATCHLIST
    rest, stream = split_public_sources(DEFAULT_WATCHLIST)
    assert stream == (AssetSpec("BTC/USDT", "CRYPTO"), AssetSpec("ETH/USDT", "CRYPTO"))
    assert AssetSpec("BTC/USD", "CRYPTO") in rest  # Kraken USD is not Binance USDT
    assert AssetSpec("EUR/USD", "FOREX") in rest


def test_partition_never_mislabels_usdt_as_kraken_usd_and_limits_streams():
    source, stream = split_public_sources(parse_watchlist("EUR/USD, SOL/USDT, BTC/USD"))
    assert tuple(s.symbol for s in source) == ("EUR/USD", "BTC/USD")
    assert tuple(s.symbol for s in stream) == ("SOL/USDT",)
    eleven = tuple(AssetSpec(f"COIN{i}/USDT", "CRYPTO") for i in range(11))
    with pytest.raises(ValueError, match="10 criptomoedas"):
        split_public_sources(eleven)


def test_coverages_add_without_claiming_unavailable_assets():
    first = RadarCoverage(3, 1, 0, 1, 0, 1)
    second = RadarCoverage(2, 0, 1, 0, 0, 1)
    total = combine_coverages(first, second)
    assert total == RadarCoverage(5, 1, 1, 1, 0, 2)


def test_watchlist_accepts_mixed_symbols_and_rejects_duplicates():
    assert parse_watchlist("EUR/USD, BTC/USD, ETH/USDT") == (
        AssetSpec("EUR/USD", "FOREX"),
        AssetSpec("BTC/USD", "CRYPTO"),
        AssetSpec("ETH/USDT", "CRYPTO"),
    )
    with pytest.raises(ValueError, match="duplicado"):
        parse_watchlist("EUR/USD,EUR/USD")
    with pytest.raises(ValueError, match="invalido"):
        parse_watchlist("FX FANTASY")


def test_ui_model_remains_offline_without_market_data():
    model = RadarViewModel((AssetSpec("EUR/USD", "FOREX"),))
    row = model.rows()[0]
    assert row.symbol == "EUR/USD"
    assert row.status == "SEM FONTE"
    assert row.direction == "—"
    assert row.last_closed == "—"


def test_stale_or_failed_market_data_has_no_directional_claim():
    spec = AssetSpec("BTC/USD", "CRYPTO")
    model = RadarViewModel((spec,))
    model.apply(RadarEvent("BTC/USD", "CRYPTO", "ATRASADO", None,
                           datetime.now(timezone.utc), "Twelve Data", "Feed atrasado"))
    row = model.rows()[0]
    assert row.status == "ATRASADO"
    assert row.direction == "—"
    model.disconnect()
    assert model.rows()[0].status == "SEM FONTE"


def test_ui_expires_a_previously_current_opportunity_without_waiting_for_network():
    spec = AssetSpec("BTC/USD", "CRYPTO")
    at = datetime(2026, 10, 24, 13, 0, tzinfo=timezone.utc)
    snapshot = MarketView(spec.symbol, "1min", (), at, at, 0,
                          "ATUALIZADO", "Dados fechados", "ALTA", None,
                          None, "", category="CRYPTO", source="Twelve Data Crypto")
    model = RadarViewModel((spec,))
    model.apply(RadarEvent(spec.symbol, spec.category, "ATUALIZADO", snapshot,
                           at, snapshot.source, snapshot.summary))
    assert model.rows(now=at + timedelta(minutes=1))[0].direction == "ALTA"
    stale = model.rows(now=at + timedelta(minutes=5))[0]
    assert stale.status == "ATRASADO"
    assert stale.direction == "—"


def test_radar_table_removes_symbols_no_longer_in_watchlist():
    from ds_trader.market_radar_ui import RadarTab

    class SmallTable:
        def __init__(self):
            self.values = {"EUR/USD": ("FOREX", "SEM FONTE", "—", "—", "—")}
        def selection(self): return ()
        def get_children(self): return tuple(self.values)
        def exists(self, key): return key in self.values
        def delete(self, key): self.values.pop(key)
        def insert(self, _parent, _where, *, iid, text, values): self.values[iid] = values
        def item(self, key, *, values): self.values[key] = values

    view = RadarTab.__new__(RadarTab)
    view.table = SmallTable()
    view.model = RadarViewModel((AssetSpec("BTC/USD", "CRYPTO"),))
    view.on_update = None
    view._render()
    assert set(view.table.values) == {"BTC/USD"}
