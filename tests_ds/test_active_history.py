"""M5 public history may describe scenarios but never authorize IQ Option orders."""
from datetime import datetime, timedelta, timezone

from ds_trader.active_history import assess_history
from ds_trader.forex_live import MarketCandle, MarketView

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)


def view(*, count=288, now=NOW, pair="USD/JPY", gap=False, source="Twelve Data Forex",
         interval="5min", status="ATUALIZADO"):
    step = timedelta(minutes=5)
    start = now - step * count
    bars = []
    for i in range(count):
        opened = start + step * i + (step if gap and i >= count // 2 else timedelta())
        close = 150.0 + i * .001
        bars.append(MarketCandle(opened, close-.001, close+.003,
                                 close-.003, close))
    final = bars[-1].opened + step
    return MarketView(pair, interval, tuple(bars), now, final,
                      (now-final).total_seconds(), status, "Resumo da fonte", "ALTA",
                      None, None, "", source=source, category="FOREX")


def test_24_hours_of_closed_m5_candles_produces_evidence_but_never_iq_option_entry():
    result = assess_history(view(), now=NOW)
    assert result.symbol == "USD/JPY"
    assert result.interval == "5min"
    assert result.closed_count == 288
    assert result.horizon_hours == 24
    assert result.scenario in ("CALL", "PUT", "AGUARDAR")
    assert result.operational_side == "AGUARDAR"
    assert "Twelve Data Forex" in result.reason
    assert "IQ Option" in result.reason


def test_less_than_twelve_hours_never_claims_full_multihour_assessment():
    result = assess_history(view(count=90), now=NOW)
    assert result.scenario == "AGUARDAR"
    assert result.horizon_hours == 7.5
    assert "12h" in result.reason


def test_duplicated_or_missing_history_breaks_chain_and_suppresses_opinion():
    snapshot = view(gap=True)
    result = assess_history(snapshot, now=NOW)
    assert result.scenario == "AGUARDAR"
    assert "lacuna" in result.reason.lower()


def test_late_provider_data_blocks_next_bar_hypothesis_even_when_labeled_current():
    snapshot = view(now=NOW - timedelta(minutes=3))
    result = assess_history(snapshot, now=NOW)
    assert result.scenario == "AGUARDAR"
    assert "atrasado" in result.reason.lower()


def test_open_or_future_bar_is_rejected_when_close_timestamp_does_not_match():
    snapshot = view()
    last = snapshot.candles[-1]
    changed = (*snapshot.candles[:-1], MarketCandle(NOW, last.open, last.high,
                                                    last.low, last.close))
    wrong = MarketView(snapshot.pair, snapshot.interval, changed, snapshot.received_at,
                       snapshot.last_closed_at, snapshot.age_seconds, snapshot.status,
                       snapshot.summary, snapshot.trend, snapshot.support,
                       snapshot.resistance, snapshot.zone_note, snapshot.source,
                       snapshot.category)
    assert assess_history(wrong, now=NOW).scenario == "AGUARDAR"


def test_standalone_active_assessor_rejects_non_m5_timeframe():
    from pytest import raises
    with raises(ValueError, match="M5"):
        assess_history(view(interval="1min"), now=NOW)
