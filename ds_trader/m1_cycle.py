"""Ciclo M1 conservador para TESTE, sem ordens ou previsoes de rentabilidade.

Uma vela que termina em T so fica disponivel em/apos T. Para preparar uma
hipotese ANTES da abertura, o alvo e T+60s (e nao a vela que abre em T).
Um adaptador confiavel deve fornecer horario, identidade, OHLC fechado e
cotacoes de abertura/fechamento com carimbo da fonte. Pixels nao fornecem isso.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite

from ds_trader.next_candle import evaluate_next


MINUTE = timedelta(minutes=1)
OPEN_TOLERANCE = timedelta(seconds=1)
CLOSE_TOLERANCE = timedelta(seconds=2)
MIN_PREPARATION_LEAD = timedelta(seconds=1)
VERIFIED_KIND = "TIMESTAMPED_QUOTES"  # somente adaptador auditavel; nunca pixels/OHLC agregado


@dataclass(frozen=True)
class M1Bar:
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    closed_confirmed: bool
    confirmed_at: datetime | None = None  # momento do fechamento comprovado pela fonte


@dataclass(frozen=True)
class M1History:
    asset: str
    source: str
    timeframe: str
    observed_at: datetime
    clock_confirmed: bool
    identity_confirmed: bool
    bars: tuple[M1Bar, ...]
    source_kind: str = "UNVERIFIED"


@dataclass(frozen=True)
class M1Price:
    asset: str
    source: str
    timeframe: str
    event_at: datetime  # instante do preco na FONTE, nunca hora de recepcao
    observed_at: datetime
    price: float
    clock_confirmed: bool
    identity_confirmed: bool
    price_confirmed: bool
    kind: str = "OPEN"  # OPEN na ativacao, CLOSE na avaliacao
    closed_confirmed: bool = False
    source_kind: str = "UNVERIFIED"


@dataclass(frozen=True)
class M1Result:
    asset: str
    source: str
    side: str
    opened_at: datetime
    expired_at: datetime
    opening_price: float
    closing_price: float
    outcome: str  # ACERTO, ERRO, EMPATE; sem inferir retorno financeiro


@dataclass(frozen=True)
class M1Status:
    phase: str  # AGUARDAR, PENDENTE, ATIVA, CONCLUIDA
    side: str   # AGUARDAR, CALL, PUT; pendente nao e entrada
    reason: str
    target_open: datetime | None = None
    target_close: datetime | None = None
    result: M1Result | None = None


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Horario sem fuso verificavel")
    return value.astimezone(timezone.utc)


def _minute_boundary(value: datetime) -> bool:
    return value.second == 0 and value.microsecond == 0


def _valid_price(value: float) -> bool:
    try:
        return isfinite(float(value)) and float(value) > 0
    except (ValueError, TypeError, OverflowError):
        return False


class M1Cycle:
    """Maquina de estados para evidencias M1. Sem chamadas a corretoras.

    Nao inferir confirmacao de um booleano local: ele deve ser afirmado por um
    adaptador com metadados comprovaveis. Na captura visual, deixar False.
    """

    def __init__(self):
        self.phase = "AGUARDAR"
        self.side = "AGUARDAR"
        self.reason = "Aguardando fonte com tempos e precos confirmados."
        self.target_open: datetime | None = None
        self.asset = ""
        self.source = ""
        self.opening_price: float | None = None
        self.results: list[M1Result] = []
        self._used_targets: set[tuple[str, str, datetime]] = set()

    def status(self, now: datetime | None = None) -> M1Status:
        visible_side = self.side
        if self.phase == "PENDENTE" and now is not None:
            try:
                if _utc(now) >= self.target_open:
                    visible_side = "AGUARDAR"  # ate confirmar a abertura
            except ValueError:
                visible_side = "AGUARDAR"
        if self.phase == "CONCLUIDA":
            visible_side = "AGUARDAR"  # resultado passado não é sinal para outra vela
        return M1Status(self.phase, visible_side, self.reason, self.target_open,
                        self.target_open + MINUTE if self.target_open else None,
                        self.results[-1] if self.phase == "CONCLUIDA" else None)

    def _wait(self, reason: str) -> M1Status:
        self.phase = "AGUARDAR"
        self.side = "AGUARDAR"
        self.reason = reason
        self.target_open = None
        self.opening_price = None
        self.asset = self.source = ""
        return self.status()

    def prepare(self, history: M1History) -> M1Status:
        """Prepara a candidata com historico fechado, antes do minuto-alvo."""
        if self.phase in ("PENDENTE", "ATIVA"):
            if (history.asset != self.asset or history.source != self.source or
                    history.timeframe != "M1" or not history.clock_confirmed or
                    not history.identity_confirmed or
                    history.source_kind != VERIFIED_KIND):
                return self._wait("AGUARDAR: perda de sincronizacao da fonte, ativo ou M1.")
            try:
                return self.advance(history.observed_at)
            except (TypeError, ValueError):
                return self._wait("AGUARDAR: observacao temporal invalida.")
        if not (history.asset and history.source and history.timeframe == "M1"
                and history.clock_confirmed and history.identity_confirmed and
                history.source_kind == VERIFIED_KIND):
            return self._wait("AGUARDAR: ativo, M1, fonte ou relogio nao confirmados.")
        try:
            now = _utc(history.observed_at)
            times = [_utc(bar.opened_at) for bar in history.bars]
        except ValueError:
            return self._wait("AGUARDAR: horario ausente ou sem fuso.")
        if len(times) < 25:
            return self._wait("AGUARDAR: menos de 25 candles fechados.")
        if any(not _minute_boundary(t) for t in times) or any(
            b - a != MINUTE for a, b in zip(times, times[1:])
        ):
            return self._wait("AGUARDAR: intervalo M1 desalinhado ou historico com lacunas.")
        for bar, started in zip(history.bars, times):
            try:
                confirmed_at = _utc(bar.confirmed_at)
            except ValueError:
                return self._wait("AGUARDAR: falta horario de confirmacao do fechamento.")
            if (not bar.closed_confirmed or started + MINUTE > now or
                    confirmed_at < started + MINUTE or confirmed_at > now or
                    not all(_valid_price(x) for x in (bar.open, bar.high, bar.low, bar.close)) or
                    not (bar.low <= min(bar.open, bar.close) <=
                         max(bar.open, bar.close) <= bar.high)):
                return self._wait("AGUARDAR: vela aberta, OHLC invalido ou fechamento nao comprovado.")
        # Nao ha tempo de analisar a barra que fecha no mesmo instante da
        # proxima abertura. Usa-se a abertura UM minuto depois do ultimo close.
        target = times[-1] + 2 * MINUTE
        if not (times[-1] + MINUTE <= now <= target - MIN_PREPARATION_LEAD):
            return self._wait("AGUARDAR: preparacao tardia ou fora da janela anterior ao alvo.")
        key = (history.source, history.asset, target)
        if key in self._used_targets:
            return self._wait("AGUARDAR: ciclo deste minuto ja processado; sem duplicar entrada.")
        opinion = evaluate_next(history.bars, source="api", closed_confirmed=True)
        if opinion.side not in ("CALL", "PUT"):
            return self._wait("AGUARDAR: sem confluencia tecnica suficiente.")
        self._used_targets.add(key)
        self.phase = "PENDENTE"
        self.side = opinion.side
        self.reason = "Hipotese pendente; aguarda preco confirmado da abertura, sem ordem."
        self.target_open = target
        self.asset = history.asset
        self.source = history.source
        return self.status(now)

    def _price_ok(self, sample: M1Price, expected_at: datetime,
                  allowance: timedelta, kind: str) -> bool:
        if not (sample.source == self.source and sample.asset == self.asset and
                sample.timeframe == "M1" and sample.clock_confirmed and
                sample.identity_confirmed and sample.price_confirmed and
                sample.kind == kind and sample.source_kind == VERIFIED_KIND and
                (kind != "CLOSE" or sample.closed_confirmed) and
                _valid_price(sample.price)):
            return False
        try:
            at, received = _utc(sample.event_at), _utc(sample.observed_at)
        except ValueError:
            return False
        return at == expected_at and expected_at <= received <= expected_at + allowance

    def activate(self, opening: M1Price) -> M1Status:
        """So registra referencia apos preco de abertura observado em T exato."""
        if self.phase != "PENDENTE":
            return self.status()
        if not self._price_ok(opening, self.target_open, OPEN_TOLERANCE, "OPEN"):
            return self._wait("AGUARDAR: abertura ausente, atrasada ou nao verificada.")
        self.opening_price = float(opening.price)
        self.phase = "ATIVA"
        self.reason = "Abertura comprovada; esperando fechamento exato em T+60s."
        return self.status()

    def settle(self, closing: M1Price) -> M1Status:
        """Compara precos de T e T+60s apenas depois do fechamento confirmado."""
        if self.phase != "ATIVA":
            return self.status()
        expires = self.target_open + MINUTE
        if not self._price_ok(closing, expires, CLOSE_TOLERANCE, "CLOSE"):
            return self._wait("AGUARDAR: fechamento/vencimento ausente, atrasado ou nao verificado.")
        price = float(closing.price)
        movement = (price > self.opening_price) - (price < self.opening_price)
        outcome = ("EMPATE" if movement == 0 else "ACERTO" if
                   (movement > 0) == (self.side == "CALL") else "ERRO")
        result = M1Result(self.asset, self.source, self.side, self.target_open,
                          expires, self.opening_price, price, outcome)
        self.results.append(result)
        self.phase = "CONCLUIDA"
        self.reason = f"Ciclo simulado concluido: {outcome}; sem ordem real."
        return self.status()

    def advance(self, now: datetime) -> M1Status:
        """Cancela ciclos quando a prova exigida nao chegou a tempo."""
        try:
            current = _utc(now)
        except ValueError:
            return self._wait("AGUARDAR: relogio sem fuso verificavel.")
        if self.phase == "PENDENTE" and current > self.target_open + OPEN_TOLERANCE:
            return self._wait("AGUARDAR: abertura M1 perdida; sem entrada valida.")
        if self.phase == "ATIVA" and current > self.target_open + MINUTE + CLOSE_TOLERANCE:
            return self._wait("AGUARDAR: fechamento M1 perdido; resultado indeterminado.")
        return self.status(current)
