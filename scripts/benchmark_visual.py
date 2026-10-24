"""Mede a leitura de screenshots locais sem enviar imagens a serviços externos.

Exemplo: python scripts/benchmark_visual.py caminho/do/print.png --crop 90 90 1300 630
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from statistics import median
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ds_trader.live_screen import assess  # noqa: E402


def run(image_path: str, crop=None, runs=50):
    from PIL import Image

    if not 2 <= runs <= 500:
        raise ValueError("Use entre 2 e 500 repetições")
    with Image.open(image_path) as image:
        source = image.convert("RGB")
    if crop:
        left, top, right, bottom = crop
        if not (0 <= left < right <= source.width and
                0 <= top < bottom <= source.height):
            raise ValueError("Recorte fora dos limites da imagem")
        source = source.crop((left, top, right, bottom))
    durations = []
    result = None
    for _ in range(runs):
        start = perf_counter()
        result = assess(source)
        durations.append((perf_counter() - start) * 1000)
    ordered = sorted(durations)
    return {
        "runs": runs,
        "median_ms": round(median(durations), 2),
        "p95_ms": round(ordered[min(runs - 1, int(runs * .95))], 2),
        "candles_detected": result.detected,
        "roi_valid": result.valid_roi,
        "visual_bias": result.next_visual_bias,
        "trading_signal": result.trading_signal,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="Imagem local do gráfico")
    parser.add_argument("--crop", nargs=4, type=int, metavar=("L", "T", "R", "B"))
    parser.add_argument("--runs", type=int, default=50)
    args = parser.parse_args()
    print(json.dumps(run(args.image, args.crop, args.runs), ensure_ascii=False))


if __name__ == "__main__":
    main()
