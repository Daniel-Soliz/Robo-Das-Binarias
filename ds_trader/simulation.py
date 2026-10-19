"""Reprodução causal. OHLC não substitui uma cotação com horário comprovado."""
import math
from dataclasses import dataclass, asdict
from datetime import timedelta
from decimal import Decimal
from collections import Counter, defaultdict
from ds_trader.data import instant
from ds_trader.strategy import Strategy, VERSION

@dataclass(frozen=True)
class Settings:
    duration: int = 120
    delay: int = 1
    max_wait: int = 60
    stake: float = 10.0
    payout: float = 0.8
    tie: str = 'refund'
    development: float = 0.7
    def __post_init__(self):
        for name in ('duration','delay','max_wait'):
            v = getattr(self,name)
            if type(v) is not int or v < (1 if name != 'delay' else 0):
                raise ValueError(f'{name}: inteiro inválido')
        if not all(math.isfinite(v) for v in (self.stake,self.payout,self.development)) or self.stake<=0 or not 0<=self.payout<=1 or not 0<self.development<1 or self.tie not in ('refund','loss'):
            raise ValueError('Valor/payout/divisão/regra de empate inválidos')

def settle(direction, entry, exit_price, payout, stake, tie):
    if entry == exit_price:
        return 'EMPATE', 0.0 if tie=='refund' else -stake
    win = exit_price > entry if direction=='ALTA' else exit_price < entry
    profit = Decimal(str(stake))*Decimal(str(payout)) if win else -Decimal(str(stake))
    return ('ACERTO' if win else 'ERRO'), float(profit)

class Replay:
    def __init__(self,bars,parameters,settings):
        if len(bars)<2:
            raise ValueError('Selecione pelo menos dois candles')
        self.bars,self.parameters,self.settings = bars,parameters,settings
        self.strategy = Strategy(parameters)
        self.index = 0
        self.cut = max(1,min(len(bars)-1,int(len(bars)*settings.development)))
        self.events,self.trades = [],[]
        self.active = None
        self.finished = False
    @property
    def phase(self):
        return 'DESENVOLVIMENTO' if self.index < self.cut else 'TESTE'
    def unknown(self,reason):
        if self.active:
            self.active.update(result='INDETERMINADA',reason_result=reason,pnl=None)
            self.active=None
    def clock(self,t):
        if not self.active:
            return
        a=self.active
        if a['entry_time'] is None:
            if t > instant(a['deadline']):
                self.unknown('Nenhuma cotação verificável dentro do prazo de entrada')
        elif t > instant(a['expiry']):
            self.unknown('Sem cotação no horário exato de expiração; sem interpolação')
    def quote(self,bar):
        t=bar.quote_time
        if t is None:
            return
        self.clock(t)
        if not self.active:
            return
        a=self.active
        if a['entry_time'] is None:
            signal=instant(a['time'])
            if t > signal and t >= signal+timedelta(seconds=self.settings.delay) and t<=instant(a['deadline']):
                payout = bar.payout if bar.payout is not None else self.settings.payout
                a.update(entry_time=t.isoformat(),entry_price=bar.candle.abertura,
                         expiry=(t+timedelta(seconds=self.settings.duration)).isoformat(),payout=payout,
                         payout_type='HISTÓRICO INFORMADO NO CSV' if bar.payout is not None else 'CENÁRIO HIPOTÉTICO',
                         result='ABERTA')
        elif t == instant(a['expiry']):
            result,pnl=settle(a['direction'],a['entry_price'],bar.candle.abertura,a['payout'],self.settings.stake,self.settings.tie)
            a.update(result=result,pnl=pnl,exit_price=bar.candle.abertura,
                     reason_result='Liquidação na cotação exata informada; execução real não garantida')
            self.active=None
    def step(self):
        if self.finished:
            return False
        if self.index==self.cut:
            self.unknown('Fim do desenvolvimento: operação não atravessa período reservado de teste')
            if self.strategy.pending:
                zone,_=self.strategy.pending
                e=self.strategy.event(self.bars[self.index-1],zone,'INVALIDADO','Fim do desenvolvimento antes do reteste')
                self.events.append(dict(e,phase='DESENVOLVIMENTO'))
            self.strategy=Strategy(self.parameters)
        bar=self.bars[self.index]
        self.quote(bar)
        self.clock(bar.end)
        before=len(self.strategy.events)
        signal=self.strategy.step(bar)
        for e in self.strategy.events[before:]:
            self.events.append(dict(e,phase=self.phase))
        if signal:
            if self.active:
                self.events.append(dict(signal,status='IGNORADO',reason='Já existe operação/entrada pendente',phase=self.phase))
            else:
                s=instant(signal['time'])
                trade=dict(signal,phase=self.phase,entry_time=None,entry_price=None,expiry=None,
                           deadline=(s+timedelta(seconds=self.settings.delay+self.settings.max_wait)).isoformat(),
                           payout=self.settings.payout,payout_type='CENÁRIO HIPOTÉTICO (até entrada)',
                           duration=self.settings.duration,delay=self.settings.delay,stake=self.settings.stake,
                           tie=self.settings.tie,result='AGUARDANDO',pnl=None,exit_price=None,reason_result='')
                self.trades.append(trade)
                self.active=trade
        self.index+=1
        if self.index==len(self.bars):
            self.finish()
        return True
    def finish(self,reason='Fim dos dados antes de obter entrada/liquidação verificável'):
        self.unknown(reason)
        if self.strategy.pending and self.index:
            zone,_ = self.strategy.pending
            e=self.strategy.event(self.bars[self.index-1],zone,'INVALIDADO','Reprodução encerrada antes de confirmar reteste')
            self.events.append(dict(e,phase='DESENVOLVIMENTO' if self.index<=self.cut else 'TESTE'))
            self.strategy.pending=None
        self.finished=True
    def run(self):
        while self.step():
            pass
        return self
    def report(self):
        groups=defaultdict(list)
        for t in self.trades:
            groups[' | '.join((t['asset'],t['source'],t['market'],t['phase']))].append(t)
        return dict(strategy_version=VERSION,parameters=asdict(self.parameters),settings=asdict(self.settings),
                    processed=self.index,total_bars=len(self.bars),split_index=self.cut,
                    start=self.bars[0].candle.instante.isoformat(),end=self.bars[-1].end.isoformat(),
                    finished=self.finished,summary=metrics(self.trades),
                    by_asset_period={k:metrics(v) for k,v in groups.items()},events=self.events,trades=self.trades,
                    caveats='Resultado apenas das operações determináveis. Indeterminadas não equivalem a zero. Teste reservado perde independência se usado para ajustar parâmetros. Amostra pequena, seleção de parâmetros, dependência entre operações e diferenças de execução impedem alegar validação/lucratividade.')

def metrics(trades):
    counts=Counter(t['result'] for t in trades)
    balance=Decimal('0'); peak=Decimal('0'); dd=Decimal('0')
    streak=max_streak=0
    for t in trades:
        if t['pnl'] is not None:
            balance+=Decimal(str(t['pnl'])); peak=max(peak,balance); dd=max(dd,peak-balance)
        if t['result']=='ERRO' or (t['result']=='EMPATE' and t['pnl'] is not None and t['pnl']<0):
            streak+=1;max_streak=max(max_streak,streak)
        else:
            streak=0
    n=counts['ACERTO']+counts['ERRO']
    rate=counts['ACERTO']/n if n else None
    wilson=None
    if n:
        z=1.959963984540054; d=1+z*z/n
        center=(rate+z*z/(2*n))/d
        half=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/d
        wilson=[max(0,center-half),min(1,center+half)]
    payouts=sorted(set(t['payout'] for t in trades if t['entry_time'] is not None))
    return dict(operations=len(trades),counts=dict(counts),net=float(balance),max_drawdown=float(dd),
                max_loss_streak=max_streak,win_rate=rate,wilson_95=wilson,payouts=payouts,
                break_even=1/(1+payouts[0]) if len(payouts)==1 else None,
                uncertainty='Wilson 95% entre acertos/erros; exclui empates e indeterminadas. Pressupõe ensaios independentes; correlação e seleção de parâmetros podem tornar o intervalo otimista. Equilíbrio 1/(1+p) pressupõe acerto +p, erro -1; empate-perda altera o equilíbrio global.')
