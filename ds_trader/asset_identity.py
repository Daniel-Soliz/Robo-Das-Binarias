"""Conservative on-screen asset identity, independent of any OCR engine.

An identity is confirmed only after repeated matching observations. A changed,
missing or ambiguous header invalidates the previous result immediately.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


FIAT = frozenset({
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "BRL",
    "MXN", "ZAR", "TRY", "SEK", "NOK", "SGD", "HKD", "CNY", "PLN",
})
CRYPTO_QUOTES = frozenset({"USD", "EUR", "BRL", "USDT", "USDC", "BTC", "ETH"})
SYMBOL_RE = re.compile(r"(?<![A-Z0-9])([A-Z0-9]{2,10})\s*[/\-]\s*([A-Z0-9]{3,6})(?![A-Z0-9])")
PERIOD_RE = re.compile(r"(?<![A-Z0-9])M\s*(1|5|15)(?![0-9])")
OTC_RE = re.compile(r"(?<![A-Z])O[\W_]*T[\W_]*C(?![A-Z])")


@dataclass(frozen=True)
class AssetIdentity:
    symbol: str
    timeframe: str
    otc: bool
    category: str


@dataclass(frozen=True)
class IdentityStatus:
    current: AssetIdentity | None
    generation: int
    confirmed: bool
    changed: bool
    reason: str


def parse_asset_header(text: str) -> AssetIdentity | None:
    """Parse a visible chart header; conflicting candidates return None."""
    if not isinstance(text, str) or len(text) > 2000:
        return None
    upper = text.upper()
    periods = {f"M{value}" for value in PERIOD_RE.findall(upper)}
    if len(periods) != 1:
        return None
    symbols = set()
    for base, quote in SYMBOL_RE.findall(upper):
        if base == quote:
            continue
        if base in FIAT and quote in FIAT:
            category = "FOREX"
        elif quote in CRYPTO_QUOTES and base not in FIAT:
            category = "CRYPTO"
        else:
            continue
        symbols.add((f"{base}/{quote}", category))
    if len(symbols) != 1:
        return None
    symbol, category = symbols.pop()
    return AssetIdentity(symbol, periods.pop(), bool(OTC_RE.search(upper)), category)


class IdentityGuard:
    """Frame-ordered fail-closed identity state, no broker/network access."""

    def __init__(self, stable_reads: int = 3):
        if stable_reads < 2:
            raise ValueError("Stable identity requires at least 2 observations")
        self.stable_reads = stable_reads
        self._candidate: AssetIdentity | None = None
        self._count = 0
        self._current: AssetIdentity | None = None
        self._generation = 0
        self._last_frame_id = -1
        self._status = IdentityStatus(None, 0, False, False, "Cabeçalho não confirmado")

    @property
    def status(self) -> IdentityStatus:
        return self._status

    def observe(self, candidate: AssetIdentity | None, *, frame_id: int) -> IdentityStatus:
        if frame_id <= self._last_frame_id:
            return self._status
        self._last_frame_id = frame_id
        changed = False
        if candidate != self._candidate:
            self._candidate = candidate
            self._count = 1 if candidate else 0
            if self._current is not None or (candidate is not None and self._status.current is None):
                self._generation += 1
                changed = True
            self._current = None
        elif candidate is not None:
            self._count += 1

        if candidate is None:
            reason = "Ativo ou período ilegível; aguarde confirmação."
        elif self._count < self.stable_reads:
            reason = f"Confirmando {candidate.symbol} {candidate.timeframe} ({self._count}/{self.stable_reads})"
        else:
            self._current = candidate
            reason = (f"{candidate.symbol} {candidate.timeframe} confirmado"
                      + (" · OTC" if candidate.otc else ""))
        self._status = IdentityStatus(self._current, self._generation,
                                      self._current is not None, changed, reason)
        return self._status
