"""Rompimento + reteste. step recebe somente UMA barra fechada."""
from dataclasses import dataclass
from analysis.levels import detectar_pivos
VERSION = 'rompimento-reteste/1.0.0'

@dataclass(frozen=True)
class Parameters:
    left: int = 2
    right: int = 2
    min_touches: int = 2
    separation: int = 3
    width: float = 0.0002
    breakout: float = 0.00005
    retest_bars: int = 5
    zone_age: int = 200
    def __post_init__(self):
        import math
        for name in ('left','right','min_touches','separation','retest_bars','zone_age'):
            v = getattr(self,name)
            if type(v) is not int or v < 1:
                raise ValueError(f'{name} deve ser inteiro positivo')
        if self.min_touches < 2 or not math.isfinite(self.width) or self.width <= 0 or not math.isfinite(self.breakout) or self.breakout < 0:
            raise ValueError('Mínimo 2 toques; largura positiva; tolerância não negativa')

class Strategy:
    def __init__(self, parameters):
        self.p = parameters
        self.bars, self.zones, self.events = [], [], []
        self.pending = None
        self.next_id = 1
    def event(self, bar, zone, status, reason):
        e = dict(time=bar.end.isoformat(),asset=bar.asset,source=bar.candle.origem,market=bar.market,
                 direction='ALTA' if zone['type']=='resistencia' else 'BAIXA',
                 lower=zone['lower'],upper=zone['upper'],touches=len(zone['touches']),
                 zone_id=zone['id'],status=status,reason=reason,version=VERSION)
        self.events.append(e)
        return e
    def step(self, bar):
        if self.bars and bar.candle.instante <= self.bars[-1].candle.instante:
            raise ValueError('Reprocessamento/ordem inválida')
        if not bar.candle.finalizado:
            raise ValueError('Somente candles fechados')
        if self.bars and (bar.key != self.bars[-1].key or bar.candle.instante != self.bars[-1].end):
            raise ValueError('Fonte diferente ou lacuna: análise interrompida')
        self.bars.append(bar)
        i = len(self.bars)-1
        c = bar.candle
        emitted = None
        if self.pending:
            z, b = self.pending
            up = z['type']=='resistencia'
            invalid = c.fechamento < z['lower']-self.p.breakout if up else c.fechamento > z['upper']+self.p.breakout
            if invalid or i-b > self.p.retest_bars:
                self.event(bar,z,'INVALIDADO','Fechamento no lado oposto' if invalid else 'Prazo de reteste esgotado')
                self.pending = None
            elif i > b:
                touch = c.minima <= z['upper'] and c.maxima >= z['lower']
                confirm = (c.fechamento > z['upper']+self.p.breakout and c.fechamento > c.abertura) if up else (c.fechamento < z['lower']-self.p.breakout and c.fechamento < c.abertura)
                if touch and confirm:
                    emitted = self.event(bar,z,'SINAL','Pivôs confirmados; toques separados; rompimento fechado; reteste posterior na região; candle direcional fechou além da tolerância')
                    self.pending = None
        elif i:
            prev = self.bars[-2].candle.fechamento
            for z in self.zones:
                if z['used'] or len(z['touches']) < self.p.min_touches or i-z['touches'][-1] > self.p.zone_age:
                    continue
                crossed = (prev <= z['upper']+self.p.breakout < c.fechamento) if z['type']=='resistencia' else (prev >= z['lower']-self.p.breakout > c.fechamento)
                if crossed:
                    z['used'] = True
                    self.pending = (dict(z),i)
                    self.event(bar,z,'ROMPIMENTO','Fechamento ultrapassou borda e tolerância; aguardando reteste')
                    break
        size = self.p.left+self.p.right+1
        if len(self.bars) >= size:
            window = [x.candle for x in self.bars[-size:]]
            for pivot in detectar_pivos(window,self.p.left,self.p.right):
                index = i-self.p.right
                matched = next((z for z in self.zones if not z['used'] and z['type']==pivot.tipo and z['lower']<=pivot.preco<=z['upper'] and i-z['touches'][-1]<=self.p.zone_age),None)
                if matched:
                    if index-matched['touches'][-1] >= self.p.separation:
                        matched['touches'].append(index)
                else:
                    self.zones.append(dict(id=self.next_id,type=pivot.tipo,lower=pivot.preco-self.p.width,
                                           upper=pivot.preco+self.p.width,touches=[index],used=False))
                    self.next_id += 1
        return emitted
