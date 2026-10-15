"""Ponto de entrada do assistente de leitura; nenhuma operação é executada."""

from __future__ import annotations

import argparse
import logging
import time

from config import carregar_configuracao, salvar_configuracao
from data_sources.base import Amostra
from utils.logger import configurar_logs

LOG = logging.getLogger(__name__)


def executar() -> int:
    """Inicializa automaticamente a fonte configurada e exibe diagnóstico."""
    parser = argparse.ArgumentParser(description="Robô das Binárias — leitura sem operações")
    parser.add_argument("--modo", choices=("tela", "api"), default=None)
    parser.add_argument("--recalibrar", action="store_true")
    args = parser.parse_args()
    configurar_logs()
    try:
        configuracao = carregar_configuracao()
        if args.modo is not None:
            configuracao.modo = args.modo
        configuracao.validar()
        if args.recalibrar or (
            configuracao.modo == "tela"
            and (configuracao.regiao_grafico is None or configuracao.regiao_cabecalho is None)
        ):
            from ui.calibration import calibrar_tela

            configuracao = calibrar_tela(configuracao)
            salvar_configuracao(configuracao)
        if configuracao.modo == "tela":
            from data_sources.screen_source import ScreenSource

            fonte = ScreenSource(configuracao)
        else:
            from data_sources.api_source import ApiSource

            fonte = ApiSource(configuracao)
    except (ValueError, RuntimeError, OSError, ImportError) as erro:
        LOG.error("Não foi possível inicializar: %s", erro)
        return 1

    anterior: tuple[str, str, str, str] | None = None
    ultima_exibicao = 0.0

    def mostrar(amostra: Amostra) -> None:
        nonlocal anterior, ultima_exibicao
        atual = (
            amostra.ativo or "—", amostra.timeframe or "—",
            amostra.estado.value, amostra.mensagem
        )
        instante = time.monotonic()
        # Imprime alterações imediatamente e amostras idênticas no máximo a cada 5 s.
        if atual == anterior and instante - ultima_exibicao < 5.0:
            return
        anterior, ultima_exibicao = atual, instante
        LOG.info(
            "%s | %s | %s | %d velas | %.1f FPS | %s",
            atual[0], atual[1], atual[2], len(amostra.candles),
            amostra.fps, amostra.mensagem,
        )

    LOG.info("Modo %s iniciado. Apenas leitura; Ctrl+C para encerrar.", configuracao.modo)
    try:
        fonte.iniciar(mostrar)
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        LOG.info("Encerrando leitor.")
    finally:
        fonte.parar()
    return 0


if __name__ == "__main__":
    raise SystemExit(executar())
