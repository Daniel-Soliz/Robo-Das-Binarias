"""LTA/LTB usando pivôs confirmados, validação de contatos e eventos."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from data_sources.base import Candle
from analysis.indicators import amplitude_tipica
from analysis.levels import Pivo, detectar_pivos


@dataclass(frozen=True)
class LinhaTendencia:
    tipo: str
    primeiro_indice: int
    ultimo_indice: int
    inclinacao: float
    intercepto: float
    toques: int
    evento: str

    def preco_no_indice(self, indice: int) -> float:
        return self.intercepto + indice * self.inclinacao


def detectar_linhas(
    candles: Sequence[Candle], minimo_toques: int = 2
) -> tuple[LinhaTendencia, ...]:
    """Exige pivôs crescentes em LTA e decrescentes em LTB."""
    if minimo_toques not in (2, 3):
        raise ValueError("Configuração aceita dois ou três toques.")
    serie = [c for c in candles if c.finalizado]
    if len(serie) < 10:
        return ()
    tolerancia = max(amplitude_tipica(serie) * 0.35, 1e-10)
    pivos = detectar_pivos(serie)
    linhas: list[LinhaTendencia] = []
    for tipo, especie in (("LTA", "suporte"), ("LTB", "resistencia")):
        candidatos = [p for p in pivos if p.tipo == especie]
        if len(candidatos) < minimo_toques:
            continue
        # Janela local recente: rejeitar linhas de tendência muito antigas.
        candidatos = [p for p in candidatos if p.indice >= len(serie) - 50]
        if len(candidatos) < minimo_toques:
            continue
        ultima = candidatos[-1]
        possiveis: list[LinhaTendencia] = []
        for anterior in reversed(candidatos[:-1]):
            delta_indice = ultima.indice - anterior.indice
            if delta_indice <= 0:
                continue
            inclinacao = (ultima.preco - anterior.preco) / delta_indice
            if (tipo == "LTA" and inclinacao <= 0) or (tipo == "LTB" and inclinacao >= 0):
                continue
            intercepto = anterior.preco - inclinacao * anterior.indice
            contatos = tuple(
                p for p in candidatos
                if anterior.indice <= p.indice <= ultima.indice
                and abs(p.preco - (intercepto + inclinacao * p.indice)) <= tolerancia
            )
            # Uma linha com pivôs cruzando muito a projeção é rejeitada.
            intermediarios = [
                p for p in candidatos if anterior.indice < p.indice < ultima.indice
            ]
            if any(
                (p.preco < intercepto + inclinacao * p.indice - tolerancia)
                if tipo == "LTA"
                else (p.preco > intercepto + inclinacao * p.indice + tolerancia)
                for p in intermediarios
            ):
                continue
            if len(contatos) < minimo_toques:
                continue
            indice_atual = len(serie) - 1
            projecao = intercepto + inclinacao * indice_atual
            atual = serie[-1]
            anterior_candle = serie[-2]
            previa = intercepto + inclinacao * (indice_atual - 1)
            evento = "sem evento"
            if tipo == "LTA":
                if anterior_candle.fechamento >= previa - tolerancia and atual.fechamento < projecao - tolerancia:
                    evento = "rompimento"
                elif (anterior_candle.fechamento < previa - tolerancia
                      and atual.maxima >= projecao - tolerancia
                      and atual.fechamento < projecao - tolerancia):
                    # Reteste da linha ROMPIDA, por baixo; não é gatilho de compra.
                    evento = "reteste"
                elif abs(atual.minima - projecao) <= tolerancia and atual.fechamento >= projecao:
                    evento = "toque"
            else:
                if anterior_candle.fechamento <= previa + tolerancia and atual.fechamento > projecao + tolerancia:
                    evento = "rompimento"
                elif (anterior_candle.fechamento > previa + tolerancia
                      and atual.minima <= projecao + tolerancia
                      and atual.fechamento > projecao + tolerancia):
                    # Reteste da linha ROMPIDA, por cima; não é gatilho de venda.
                    evento = "reteste"
                elif abs(atual.maxima - projecao) <= tolerancia and atual.fechamento <= projecao:
                    evento = "toque"
            possiveis.append(
                LinhaTendencia(
                    tipo=tipo, primeiro_indice=anterior.indice,
                    ultimo_indice=ultima.indice, inclinacao=inclinacao,
                    intercepto=intercepto, toques=len(contatos), evento=evento,
                )
            )
        if possiveis:
            # Preferir maior número de toques e pivô mais recente.
            linhas.append(max(possiveis, key=lambda l: (l.toques, l.primeiro_indice)))
    return tuple(linhas)
