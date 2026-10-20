"""Conferir a entrega do Windows e preparar somente arquivos aprovados para Releases.

Usado pelo job 'publicar', independentemente da estrutura de pastas gerada pelo
upload/download-artifact. Falha explicitamente se um arquivo estiver ausente,
duplicado, vazio, ou tiver hash divergente.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

FILES = (
    "DS-Trader-Setup.exe",
    "DS-Trader-Setup.sha256.txt",
    "DS-Trader-Windows-x64.zip",
    "DS-Trader-Windows-x64.sha256.txt",
)
HASH_PAIRS = (
    ("DS-Trader-Setup.exe", "DS-Trader-Setup.sha256.txt"),
    ("DS-Trader-Windows-x64.zip", "DS-Trader-Windows-x64.sha256.txt"),
)


def unique(root: Path, filename: str) -> Path:
    found = [p for p in root.rglob(filename) if p.is_file()]
    if len(found) != 1:
        raise RuntimeError(
            f"Esperado exatamente 1 {filename}; encontrados {len(found)} em {root}. "
            f"Arquivos existentes: {[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()]}"
        )
    if found[0].stat().st_size == 0:
        raise RuntimeError(f"Arquivo vazio: {found[0]}")
    return found[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_hash(file: Path, manifest: Path) -> None:
    line = manifest.read_text(encoding="ascii").strip()
    match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?([^\\/\r\n]+)", line)
    if match is None or match.group(2) != file.name:
        raise RuntimeError(f"SHA256 malformado ou nome divergente: {manifest}")
    actual = sha256(file)
    if actual.lower() != match.group(1).lower():
        raise RuntimeError(f"SHA256 divergente para {file.name}: esperado {match.group(1)}, atual {actual}")
    print(f"SHA256 OK: {file.name}")


def prepare(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise RuntimeError(f"Diretorio do artifact ausente: {source}")
    files = {name: unique(source, name) for name in FILES}
    smoke = unique(source, "smoke-result.json")
    status = json.loads(smoke.read_text(encoding="utf-8"))
    for key in ("gui", "persistence", "export"):
        if status.get(key) != "passed":
            raise RuntimeError(f"Smoke test nao aprovado: {key} = {status.get(key)!r}")
    print("Smoke test Windows: GUI, persistencia e exportacao aprovados.")
    for binary, manifest in HASH_PAIRS:
        verify_hash(files[binary], files[manifest])
    target.mkdir(parents=True, exist_ok=True)
    for name, src in files.items():
        dest = target / name
        shutil.copyfile(src, dest)
        if dest.stat().st_size != src.stat().st_size:
            raise RuntimeError(f"Copia incompleta de {name}")
        print(f"PRONTO PARA RELEASE: {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: python scripts/prepare_release.py downloads release-ready")
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
