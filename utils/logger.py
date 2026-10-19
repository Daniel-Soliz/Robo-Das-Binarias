"""Log de diagnóstico sem exportar segredos nem capturas pessoais."""

import logging


def configurar_logs() -> None:
    """Habilita mensagens resumidas no terminal."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

