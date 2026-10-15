"""Carregamento e validação da configuração local do assistente."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ARQUIVO_CONFIG = Path(__file__).resolve().parent / "config.json"


@dataclass(frozen=True)
class Regiao:
    """Retângulo absoluto em pixels do desktop virtual."""

    left: int
    top: int
    width: int
    height: int

    def validar(self) -> None:
        if self.width < 20 or self.height < 12:
            raise ValueError("Região muito pequena para leitura.")
        if self.width > 16000 or self.height > 16000:
            raise ValueError("Dimensões da região inválidas.")

    @classmethod
    def de_dict(cls, valor: dict[str, Any]) -> "Regiao":
        regiao = cls(*(int(valor[campo]) for campo in ("left", "top", "width", "height")))
        regiao.validar()
        return regiao


@dataclass
class Configuracao:
    """Parâmetros verificáveis, sem credenciais armazenadas."""

    modo: str = "tela"
    captura_fps: float = 3.0
    ocr_intervalo_segundos: float = 1.5
    timeframes_permitidos: tuple[str, ...] = ("M5", "M15")
    minimo_candles: int = 60
    pontuacao_minima: int = 75
    api_ativo: str = "EURUSD"
    api_intervalo_segundos: float = 10.0
    regiao_grafico: Regiao | None = None
    regiao_cabecalho: Regiao | None = None
    regiao_escala: Regiao | None = None

    def validar(self) -> None:
        if self.modo not in ("tela", "api"):
            raise ValueError("Modo deve ser 'tela' ou 'api'.")
        if not 0.5 <= self.captura_fps <= 10:
            raise ValueError("FPS fora do limite seguro (0,5 a 10).")
        if not 0.5 <= self.ocr_intervalo_segundos <= 30:
            raise ValueError("Intervalo de OCR inválido.")
        if not 3 <= self.minimo_candles <= 500:
            raise ValueError("Quantidade mínima de candles inválida.")
        if not 50 <= self.pontuacao_minima <= 100:
            raise ValueError("Pontuação mínima fora de 50 a 100.")
        if not 3 <= self.api_intervalo_segundos <= 3600:
            raise ValueError("Intervalo da API inválido.")
        if any(valor not in ("M5", "M15") for valor in self.timeframes_permitidos):
            raise ValueError("Timeframe não permitido.")
        for regiao in (self.regiao_grafico, self.regiao_cabecalho, self.regiao_escala):
            if regiao is not None:
                regiao.validar()

    def para_dict(self) -> dict[str, Any]:
        dados = asdict(self)
        dados["timeframes_permitidos"] = list(self.timeframes_permitidos)
        return dados


def carregar_configuracao(caminho: Path = ARQUIVO_CONFIG) -> Configuracao:
    """Cria configuração pessoal na primeira execução e aplica validações."""
    if not caminho.exists():
        configuracao = Configuracao()
        salvar_configuracao(configuracao, caminho)
        return configuracao
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError("Configuração deve ser um objeto JSON.")
    permitidos = set(Configuracao.__dataclass_fields__)
    desconhecidos = set(dados) - permitidos
    if desconhecidos:
        raise ValueError(f"Chaves de configuração desconhecidas: {sorted(desconhecidos)}")
    for campo in ("regiao_grafico", "regiao_cabecalho", "regiao_escala"):
        if dados.get(campo) is not None:
            dados[campo] = Regiao.de_dict(dados[campo])
    if "timeframes_permitidos" in dados:
        dados["timeframes_permitidos"] = tuple(dados["timeframes_permitidos"])
    configuracao = Configuracao(**dados)
    configuracao.validar()
    return configuracao


def salvar_configuracao(
    configuracao: Configuracao, caminho: Path = ARQUIVO_CONFIG
) -> None:
    """Grava somente parâmetros locais, sem credenciais."""
    configuracao.validar()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(
        json.dumps(configuracao.para_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporario.replace(caminho)
