"""CSV estrito: timestamp é abertura da barra; open_time é cotação observada."""
import csv
import hashlib
import io
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from data_sources.base import Candle
REQUIRED = {'timestamp','asset','source','market','interval_seconds','open','high','low','close'}

def instant(value):
    t = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError('Horário exige fuso ISO 8601, ex.: 2026-01-01T10:00:00-03:00')
    return t.astimezone(timezone.utc)

def number(value):
    n = float(value)
    if not math.isfinite(n):
        raise ValueError('Número não finito')
    return n

@dataclass(frozen=True)
class Bar:
    candle: Candle
    asset: str
    market: str
    interval: int
    volume: float | None = None
    quote_time: datetime | None = None
    payout: float | None = None
    payout_known_at: datetime | None = None
    @property
    def key(self):
        return (self.asset, self.candle.origem, self.market, self.interval)
    @property
    def end(self):
        return self.candle.instante + timedelta(seconds=self.interval)

@dataclass
class Dataset:
    groups: dict
    digest: str
    raw: str
    warnings: list

class DataError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('\n'.join(errors[:30]) + ('\n…' if len(errors)>30 else ''))

def read_csv(path):
    return parse_csv(Path(path).read_text(encoding='utf-8-sig'))

def parse_csv(raw, now=None):
    now = now or datetime.now(timezone.utc)
    reader = csv.DictReader(io.StringIO(raw.lstrip('\ufeff')))
    if not REQUIRED.issubset(reader.fieldnames or []):
        raise DataError(['Colunas obrigatórias: ' + ', '.join(sorted(REQUIRED))])
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise DataError(['Cabeçalho com colunas duplicadas'])
    groups, errors, warnings = {}, [], []
    for line, row in enumerate(reader, 2):
        try:
            if None in row or any(row[k] is None for k in REQUIRED):
                raise ValueError('Quantidade de campos incorreta')
            t = instant(row['timestamp'])
            interval = int(row['interval_seconds'])
            if interval <= 0:
                raise ValueError('Intervalo precisa ser positivo')
            asset, source, market = (row[k].strip() for k in ('asset','source','market'))
            if not asset or not source or market not in ('OTC','REGULAR'):
                raise ValueError('Ativo/origem obrigatórios; market deve ser OTC ou REGULAR')
            if 'OTC' in asset.upper() and market != 'OTC':
                raise ValueError('Ativo OTC rotulado como REGULAR')
            o,h,l,c = [number(row[k]) for k in ('open','high','low','close')]
            if min(o,h,l,c) <= 0:
                raise ValueError('Preços devem ser positivos')
            if t + timedelta(seconds=interval) > now:
                raise ValueError('Candle ainda aberto ou com horário futuro')
            candle = Candle(t,o,h,l,c,f'S{interval}',True,True,source)
            volume = number(row['volume']) if row.get('volume','').strip() else None
            if volume is not None and volume < 0:
                raise ValueError('Volume negativo')
            qt = instant(row['open_time']) if row.get('open_time','').strip() else None
            if qt is not None and not t <= qt < t + timedelta(seconds=interval):
                raise ValueError('open_time deve estar dentro da barra e identificar a cotação de abertura')
            payout = number(row['payout']) if row.get('payout','').strip() else None
            known = instant(row['payout_known_at']) if row.get('payout_known_at','').strip() else None
            if payout is not None and (not 0 <= payout <= 1 or qt is None or known is None or known > qt):
                raise ValueError('Payout entre 0 e 1 exige open_time e payout_known_at <= open_time')
            if known is not None and payout is None:
                raise ValueError('payout_known_at sem payout')
            bar = Bar(candle,asset,market,interval,volume,qt,payout,known)
            group = groups.setdefault(bar.key, [])
            if group:
                delta = (t-group[-1].candle.instante).total_seconds()
                if delta == 0:
                    raise ValueError('Candle duplicado')
                if delta < 0:
                    raise ValueError('Candles fora de ordem')
                if delta != interval:
                    raise ValueError(f'Lacuna/intervalo incorreto: esperado {interval}s, encontrado {delta:g}s')
            group.append(bar)
        except (ValueError, TypeError, KeyError, OverflowError) as e:
            errors.append(f'Linha {line}: {e}')
    if errors:
        raise DataError(errors)
    if not groups:
        raise DataError(['Arquivo sem candles'])
    for key, bars in groups.items():
        age = (now-bars[-1].end).total_seconds()
        if age > key[3]*2:
            warnings.append(f'{key[0]} / {key[1]}: dados históricos/atrasados ({age/3600:.1f} h); somente reprodução histórica')
        if any(b.quote_time is None for b in bars):
            warnings.append(f'{key[0]}: sem open_time, OHLC não é cotação exata de entrada/liquidação')
    return Dataset(groups,hashlib.sha256(raw.encode()).hexdigest(),raw,warnings)
