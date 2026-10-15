"""Leitura de cabeçalho com validação conservadora de ativo e período."""

from __future__ import annotations

import re

import cv2
import numpy as np


def eh_otc(texto: str | None) -> bool:
    """Detecta OTC mesmo com espaços/pontuação entre as letras."""
    if not texto:
        return False
    return bool(re.search(r"(?<![A-Z])O[\W_]*T[\W_]*C(?![A-Z])", texto.upper()))


def identificar_cabecalho(texto: str) -> tuple[str | None, str | None, bool]:
    """Retorna (par Forex, timeframe, otc); entradas ambíguas não são aceitas."""
    limpo = texto.upper().replace("\n", " ")
    otc = eh_otc(limpo)
    pares = re.findall(r"(?<![A-Z])([A-Z]{3})\s*[/\-]\s*([A-Z]{3})(?![A-Z])", limpo)
    if not pares:
        pares = [
            (p[:3], p[3:]) for p in
            re.findall(r"(?<![A-Z])([A-Z]{6})(?![A-Z])", limpo)
        ]
    moedas = {
        "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD",
        "BRL", "MXN", "ZAR", "TRY", "SEK", "NOK", "SGD",
    }
    pares_validos = {a + b for a, b in pares if a in moedas and b in moedas and a != b}
    ativo = next(iter(pares_validos)) if len(pares_validos) == 1 else None
    encontrados = re.findall(r"(?<!\w)M\s*(5|15)(?!\d)", limpo)
    encontrados += re.findall(r"(?<!\d)(5|15)\s*(?:M|MIN)(?!\w)", limpo)
    timeframes = {"M" + valor for valor in encontrados}
    timeframe = next(iter(timeframes)) if len(timeframes) == 1 else None
    return ativo, timeframe, otc


def extrair_texto(imagem_bgr: np.ndarray) -> str:
    """Executa OCR local; lança erro se Tesseract não estiver configurado."""
    import pytesseract

    cinza = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY)
    ampliada = cv2.resize(cinza, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    contraste = cv2.equalizeHist(ampliada)
    # PSM 6 preserva linhas e rótulos adjacentes do cabeçalho.
    return pytesseract.image_to_string(contraste, config="--psm 6")
