"""Detector HSV vetorizado, opcional, com os MESMOS limiares do detector Python.

Usado no Windows (NumPy e requisito de runtime). Nao importa NumPy no
carregamento do app: modo CSV e plataformas sem NumPy usam fallback legado.
Coordenadas devolvidas sao apenas posicoes relativas em pixels.
"""
from __future__ import annotations


def detect_numpy(hsv, candle_factory):
    import numpy as np

    pixels = np.asarray(hsv)
    height, width = pixels.shape[:2]
    hue, saturation, value = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
    visible = (saturation >= 92) & (value >= 78)
    up_mask = visible & (hue >= 51) & (hue <= 124)
    down_mask = visible & ((hue <= 11) | (hue >= 246))
    # A contagem das colunas usa amostragem a cada 2 linhas, como o
    # detector Python. Nao calcular direcao com dados nao capturados.
    up = np.count_nonzero(up_mask[4:height - 4:2], axis=0)
    down = np.count_nonzero(down_mask[4:height - 4:2], axis=0)
    directions = np.zeros(width, dtype=np.int8)
    directions[(up >= 3) & (up >= 3 * down)] = 1
    directions[(down >= 3) & (down >= 3 * up)] = -1
    # Bordas entre trechos contiguos. A mascaras precomputadas elimina
    # os loops pixel a pixel do caminho antigo.
    padded = np.pad(directions, (1, 1))
    changes = np.flatnonzero(padded[1:] != padded[:-1])
    candles = []
    for begin, end in zip(changes[::2], changes[1::2]):
        direction = int(directions[begin])
        span = int(end - begin)
        if direction == 0 or span < 3 or span > max(18, int(width * .055)):
            continue
        mask = up_mask if direction == 1 else down_mask
        rows = np.count_nonzero(mask[4:height - 4, begin:end], axis=1)
        colored = np.flatnonzero(rows > 0)
        body = np.flatnonzero(rows >= max(2, int(span * .6)))
        if colored.size < 5 or body.size < 2:
            continue
        top = int(body[0]) + 4
        bottom = int(body[-1]) + 4
        high = 1.0 - (int(colored[0]) + 4) / height
        low = 1.0 - (int(colored[-1]) + 4) / height
        if high < low or top >= bottom:
            continue
        up_direction = direction == 1
        open_ = 1.0 - (bottom if up_direction else top) / height
        close = 1.0 - (top if up_direction else bottom) / height
        candles.append(candle_factory(
            int((begin + end) // 2), high, low, open_, close,
            "ALTA" if up_direction else "BAIXA"))
    return tuple(candles)
