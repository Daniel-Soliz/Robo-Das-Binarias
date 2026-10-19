"""Testes determinísticos com frames artificiais, sem utilizar IQ Option."""

from datetime import datetime

import cv2
import numpy as np

from data_sources.screen_source import extrair_velas
from utils.ocr import eh_otc, identificar_cabecalho


def test_filtro_otc_e_periodos():
    assert eh_otc("EUR/USD OTC M5")
    assert eh_otc("EURUSD (O T C)")
    assert not eh_otc("EUR/USD M5")
    assert identificar_cabecalho("EUR/USD M5") == ("EURUSD", "M5", False)
    assert identificar_cabecalho("GBP/JPY OTC M15") == ("GBPJPY", "M15", True)
    assert identificar_cabecalho("EUR/USD 1M")[1] is None
    assert identificar_cabecalho("texto ilegível") == (None, None, False)


def test_velas_normalizadas_com_corpo_e_pavio():
    imagem = np.zeros((120, 160, 3), dtype=np.uint8)
    # Alta verde: corpo de y 42 a 68; máxima visual em y=28 e mínima y=80.
    cv2.line(imagem, (30, 28), (30, 80), (0, 255, 0), 1)
    cv2.rectangle(imagem, (26, 42), (34, 68), (0, 255, 0), -1)
    # Baixa vermelha: corpo de y 30 a 61; máxima visual y=18 e mínima y=78.
    cv2.line(imagem, (90, 18), (90, 78), (0, 0, 255), 1)
    cv2.rectangle(imagem, (86, 30), (94, 61), (0, 0, 255), -1)
    velas = extrair_velas(imagem, "M5")
    assert len(velas) == 2
    assert velas[0].fechamento > velas[0].abertura
    assert velas[1].fechamento < velas[1].abertura
    assert velas[0].preco_real is False
    assert velas[0].instante is None
    assert velas[0].finalizado and not velas[1].finalizado
    assert all(0 <= vela.minima <= vela.maxima <= 1 for vela in velas)


def test_frame_sem_velas():
    imagem = np.zeros((120, 160, 3), dtype=np.uint8)
    assert extrair_velas(imagem, "M5") == ()

