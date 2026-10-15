"""Contrato único para candles provenientes da tela ou da API."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable


class EstadoFonte(str, Enum):
    ANALISANDO = "Analisando"
    AGUARDAR = "AGUARDAR"
    OTC_IGNORADO = "OTC ignorado"
    SEM_GRAFICO = "Sem gráfico"
    ERRO = "Erro"


@dataclass(frozen=True)
class Candle:
    """OHLC normalizado ou de preço real; sem inventar tempo da vela."""

    instante: datetime | None
    abertura: float
    maxima: float
    minima: float
    fechamento: float
    timeframe: str
    finalizado: bool
    preco_real: bool
    origem: str

    def __post_init__(self) -> None:
        valores = (self.abertura, self.maxima, self.minima, self.fechamento)
        if not all(math.isfinite(v) for v in valores):
            raise ValueError("Candle com valor não finito.")
        if self.maxima < max(self.abertura, self.fechamento, self.minima):
            raise ValueError("Máxima inconsistente.")
        if self.minima > min(self.abertura, self.fechamento, self.maxima):
            raise ValueError("Mínima inconsistente.")
        if not self.preco_real and not all(0 <= valor <= 1 for valor in valores):
            raise ValueError("Preço normalizado deve estar entre 0 e 1.")
        if self.preco_real and self.instante is None:
            raise ValueError("Candles de preço real exigem timestamp.")


@dataclass(frozen=True)
class Amostra:
    """Leitura da fonte com metadados e estado de confiança da captura."""

    ativo: str | None
    timeframe: str | None
    candles: tuple[Candle, ...] = ()
    estado: EstadoFonte = EstadoFonte.AGUARDAR
    mensagem: str = ""
    fps: float = 0.0
    preco_real: bool = False
    instante_coleta: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    identificacao_confiavel: bool = False


AoReceber = Callable[[Amostra], None]


class DataSource(ABC):
    """Uma fonte não tem qualquer permissão para operar na plataforma."""

    @abstractmethod
    def iniciar(self, ao_receber: AoReceber) -> None:
        """Inicia a leitura contínua sem bloquear quem chamou."""

    @abstractmethod
    def parar(self) -> None:
        """Finaliza a leitura e encerra threads auxiliares."""
