"""Forex via Twelve Data: REST somente leitura, OHLC UTC, verificacao de frescor.

A coleta em intervalos de 60/120/300 segundos NAO e streaming tick-a-tick.
Chave da API somente em memoria durante a sessao. Nenhuma ordem e enviada.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from queue import Queue, Empty, Full
from threading import Event, Thread
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import math
import re
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

BASE_URL = "https://api.twelvedata.com/time_series"
PAIRS = ("EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "EUR/GBP", "NZD/USD")
INTERVALS = {"1min":60, "5min":300, "15min":900}
SOURCE = "Twelve Data Forex"
MAX_CANDLES = 120

class FeedError(ValueError):
    pass

@dataclass(frozen=True)
class MarketCandle:
    opened: datetime
    open: float
    high: float
    low: float
    close: float

@dataclass(frozen=True)
class MarketView:
    pair: str
    interval: str
    candles: tuple[MarketCandle, ...]
    received_at: datetime
    last_closed_at: datetime
    age_seconds: float
    status: str
    summary: str
    trend: str
    support: float | None
    resistance: float | None
    zone_note: str
    source: str = SOURCE


def _utc_time(value):
    if not isinstance(value, str):
        raise FeedError("Horario de candle ausente")
    try:
        when = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise FeedError("Horario do fornecedor fora do formato UTC esperado") from exc
    return when.replace(tzinfo=timezone.utc)


def _price(value):
    try:
        price = float(value)
    except (ValueError, TypeError) as exc:
        raise FeedError("OHLC do fornecedor nao e numerico") from exc
    if not math.isfinite(price) or price <= 0:
        raise FeedError("Cotacao OHLC fora do intervalo valido")
    return price


def reference_forex_open(now: datetime) -> bool:
    """Sessao Forex indicativa: Nova York domingo 17:05 a sexta 16:59.

    Baseada em referencia de horas de mercado OANDA, NAO em horario da Twelve
    Data e NAO confirma que ativo/conta da corretora esteja negociavel.
    """
    if now.tzinfo is None:
        raise ValueError("Relogio com fuso horario obrigatorio")
    try:
        ny=now.astimezone(ZoneInfo("America/New_York"))
    except ZoneInfoNotFoundError as exc:
        raise FeedError("Base de fusos horaros indisponivel: instalar tzdata") from exc
    weekday=ny.weekday()
    minute=ny.hour*60+ny.minute
    if weekday==5:
        return False
    if weekday==6:
        return minute>=17*60+5
    if weekday==4:
        return minute<16*60+59
    return minute<16*60+59 or minute>=17*60+5


def parse_payload(payload, pair: str, interval: str, *, now=None):
    """Rejeita resposta inconsistente e vela aberta. Nunca fabrica barras em lacunas."""
    if pair not in PAIRS or interval not in INTERVALS:
        raise FeedError("Par de moedas ou periodo invalido")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Relogio precisa ter fuso UTC")
    now = now.astimezone(timezone.utc)
    if not isinstance(payload, dict):
        raise FeedError("Resposta invalida do fornecedor")
    if payload.get("status") == "error" or payload.get("code") in (400, 401, 403, 404, 429):
        code = payload.get("code")
        if str(code) == "429":
            raise FeedError("Limite de creditos/consultas da Twelve Data atingido")
        raise FeedError(f"Fornecedor recusou a consulta ({code or 'erro de API'}). Confira chave, plano e par")
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise FeedError("Metadados do fornecedor ausentes")
    if meta.get("symbol", "").replace("_", "/") != pair:
        raise FeedError("Par devolvido nao corresponde ao solicitado")
    if meta.get("interval") != interval:
        raise FeedError("Intervalo devolvido nao corresponde ao solicitado")
    entries = payload.get("values")
    if not isinstance(entries, list) or not entries or len(entries)>5000:
        raise FeedError("Fornecedor nao devolveu candles validos")
    seconds = INTERVALS[interval]
    by_time = {}
    for item in entries:
        if not isinstance(item, dict):
            raise FeedError("Candle em formato invalido")
        when = _utc_time(item.get("datetime"))
        if when in by_time:
            raise FeedError("Resposta contem candles duplicados")
        op, hi, lo, cl = (_price(item.get(k)) for k in ("open","high","low","close"))
        if lo > min(op, cl) or hi < max(op, cl) or lo > hi:
            raise FeedError("Valores OHLC inconsistentes")
        by_time[when] = MarketCandle(when, op, hi, lo, cl)
    candles = [by_time[t] for t in sorted(by_time)]
    # Nunca trate candle atual como completo: margem para sincronizacao/atraso do fornecedor.
    candles = [c for c in candles if c.opened + timedelta(seconds=seconds+5) <= now]
    if not candles:
        raise FeedError("Aguardando o fechamento de um candle com horario verificavel")
    candles = candles[-MAX_CANDLES:]
    latest = candles[-1]
    closed_at = latest.opened + timedelta(seconds=seconds)
    age = (now - closed_at).total_seconds()
    if age < 0:
        raise FeedError("Cotacao do fornecedor veio com horario futuro")
    # Dados mais antigos que 3 intervalos nunca sao rotulados como atuais.
    status = "ATUALIZADO" if age <= max(3*seconds, 180) else "ATRASADO / MERCADO SEM NOVAS COTACOES"
    if status=="ATUALIZADO" and not reference_forex_open(now):
        status="FORA DO HORARIO REGULAR FOREX (REFERENCIA NOVA YORK)"
    # Descarta qualquer historia anterior a lacuna, inclusive fim de semana.
    start = len(candles)-1
    while start > 0 and (candles[start].opened-candles[start-1].opened).total_seconds()==seconds:
        start-=1
    consecutive = tuple(candles[start:])
    trend, support, resistance, zone_note, summary = analyze(consecutive, status)
    return MarketView(pair, interval, consecutive, now, closed_at, age,
                      status, summary, trend, support, resistance, zone_note)


def _pivots(candles, field, left=2, right=2):
    values = [getattr(c, field) for c in candles]
    output=[]
    for i in range(left,len(candles)-right):
        window = values[i-left:i+right+1]
        v=values[i]
        if field=="high" and v > max(window[:left]+window[left+1:]):
            output.append(v)
        if field=="low" and v < min(window[:left]+window[left+1:]):
            output.append(v)
    return output


def analyze(candles: tuple[MarketCandle, ...], status: str):
    if status != "ATUALIZADO":
        return ("SEM ANALISE", None, None, "Dados indisponiveis no momento",
                "Ultimo candle atrasado; nao emitir leitura de mercado atual.")
    if len(candles) < 25:
        return ("AGUARDANDO", None, None, "Amostra insuficiente",
                f"Apenas {len(candles)} candles consecutivos fechados. Sao necessarios pelo menos 25.")
    closes=[c.close for c in candles]
    sma9=sum(closes[-9:])/9
    sma21=sum(closes[-21:])/21
    spread=(max(c.high for c in candles[-20:])-min(c.low for c in candles[-20:]))
    threshold=max(spread*.04, closes[-1]*.00002)
    if sma9 > sma21+threshold:
        trend="ALTA"
    elif sma9 < sma21-threshold:
        trend="BAIXA"
    else:
        trend="INDEFINIDA"
    highs=_pivots(candles,"high")
    lows=_pivots(candles,"low")
    current=closes[-1]
    resistances=[x for x in highs if x>current]
    supports=[x for x in lows if x<current]
    resistance=min(resistances) if resistances else None
    support=max(supports) if supports else None
    note="Niveis derivados de pivôs com confirmacao de 2 candles; nao sao garantias."
    if support is None or resistance is None:
        note="Pivôs insuficientes em um dos lados do preco; nao inventar suporte/resistencia."
    summary=(f"{len(candles)} candles fechados consecutivos. "
             f"Medias de 9/21 candles: {sma9:.6f} / {sma21:.6f}. "
             f"Tendencia descritiva: {trend}. "
             "Leitura nao determina probabilidade de acerto, CALL/PUT ou vencimento.")
    return trend,support,resistance,note,summary


def fetch_candles(api_key: str, pair: str, interval: str, *, timeout=12, opener=None, now=None):
    """Usa so endpoint de candles. A chave NAO entra em logs, reports nem bancos."""
    if not api_key or len(api_key.strip()) < 6 or any(c.isspace() for c in api_key):
        raise FeedError("Insira uma chave de API Twelve Data valida")
    if pair not in PAIRS or interval not in INTERVALS:
        raise FeedError("Par/intervalo nao permitido")
    params = urlencode({"symbol":pair,"interval":interval,"timezone":"UTC",
                        "outputsize":160,"order":"DESC","apikey":api_key})
    req = Request(BASE_URL + "?" + params, headers={"Accept":"application/json","User-Agent":"DS-Trader/1.1"}, method="GET")
    try:
        response = (opener or urlopen)(req, timeout=timeout)
        with response as conn:
            raw=conn.read(2_000_001)
        if len(raw)>2_000_000:
            raise FeedError("Resposta de mercado excessivamente grande")
        payload=json.loads(raw)
    except HTTPError as exc:
        if exc.code==429: raise FeedError("Limite de consultas da Twelve Data (HTTP 429)") from None
        if exc.code in (401,403): raise FeedError("Chave de API ou permissao de acesso recusada") from None
        raise FeedError(f"Falha HTTP {exc.code} no fornecedor de dados") from None
    except (URLError,TimeoutError,OSError):
        raise FeedError("Conexao com fornecedor de cotacoes indisponivel") from None
    except (json.JSONDecodeError,UnicodeDecodeError):
        raise FeedError("Resposta JSON invalida do fornecedor") from None
    return parse_payload(payload,pair,interval,now=now)


class ForexWatcher:
    """Polling com limite explicito; chave mantida apenas durante a sessao."""
    def __init__(self, api_key, pair, interval, refresh_seconds=120, fetcher=fetch_candles):
        if refresh_seconds not in (60,120,300):
            raise ValueError("Atualizacao deve ser a cada 60, 120 ou 300 segundos")
        self._key=api_key
        self.pair=pair
        self.interval=interval
        self.refresh_seconds=refresh_seconds
        self._fetcher=fetcher
        self.results=Queue(maxsize=1)
        self._stop=Event()
        self._thread=None

    def start(self):
        if self._thread and self._thread.is_alive():return
        self._stop.clear()
        self._thread=Thread(target=self._run,daemon=True,name="ds-forex-readonly")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        self._key=""  # nunca gravar token

    def _emit(self, result):
        try:self.results.put_nowait(result)
        except Full:
            try:self.results.get_nowait()
            except Empty:pass
            self.results.put_nowait(result)

    def _run(self):
        while not self._stop.is_set():
            try:
                view=self._fetcher(self._key,self.pair,self.interval)
                self._emit(("data",view))
            except FeedError as exc:
                self._emit(("error",str(exc)))
            except Exception:
                # Nao publicar excecoes que possam conter chave na URL.
                self._emit(("error","Falha inesperada na consulta; nenhuma cotacao presumida"))
            if self._stop.wait(self.refresh_seconds):break
