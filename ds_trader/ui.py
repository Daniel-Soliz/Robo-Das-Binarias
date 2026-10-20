"""Interface desktop Tk nativa; runtime somente biblioteca padrão do Python."""
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from dataclasses import asdict
from ds_trader.data import read_csv, parse_csv, instant
from ds_trader.demo import demo_csv
from ds_trader.strategy import Parameters
from ds_trader.simulation import Settings, Replay
from ds_trader.storage import Store, export_report
from ds_trader.explain import explain
from ds_trader.live_ui import LiveScreenTab
from ds_trader.forex_ui import ForexMarketTab

LABELS={
'left':'Candles à esquerda do pivô','right':'Candles à direita (confirmação)',
'min_touches':'Mínimo de toques','separation':'Distância mínima entre toques (barras)',
'width':'Meia largura da região (preço)','breakout':'Tolerância de rompimento (preço)',
'retest_bars':'Prazo de reteste (barras)','zone_age':'Idade máxima desde último toque (barras)',
'duration':'Duração da operação (segundos)','delay':'Atraso mínimo após sinal (segundos)',
'max_wait':'Espera máxima adicional de cotação (s)','stake':'Valor fixo por operação',
'payout':'Payout hipotético (0.8 = 80%)','tie':'Empate: refund = devolve; loss = perde',
'development':'Fração para desenvolvimento (0.7 = 70%)'}
HELP='''DS TRADER — ANÁLISE E SIMULAÇÃO\n\n1. Clique em “Exemplo sintético” para conhecer o programa, ou importe seu CSV.\n2. Escolha ativo/origem/mercado/tempo gráfico. As datas opcionais exigem ISO 8601 com fuso.\n3. Confira as Configurações: valores iniciais são hipóteses, não parâmetros lucrativos.\n4. Inicie a reprodução. Pause, avance uma barra ou encerre. Clique em um evento para entender.\n5. Exporte JSON + dois CSVs. O JSON inclui parâmetros, versão, hash e dados de entrada para auditoria.\n\nCSV obrigatório (separador vírgula; decimal ponto; UTF-8):\ntimestamp,asset,source,market,interval_seconds,open,high,low,close\nTimestamp é abertura da barra com fuso. market: REGULAR ou OTC.\nOpcionais: volume,open_time,payout,payout_known_at.\nopen_time deve registrar o horário REAL da cotação open; não invente esse horário a partir do candle.\nPayout histórico é fração do lucro e exige payout_known_at <= open_time. Ausente: cenário hipotético.\n\nEntrada: primeira cotação open com open_time estritamente posterior ao sinal, respeitando atraso/prazo.\nExpiração: entrada + duração configurada (independente do candle). Liquidação exige cotação no instante exato.\nSem informação suficiente: INDETERMINADA. Não interpolamos. Apenas uma operação/entrada pendente.\n\nPivôs estritos com confirmação à direita; regiões ancoradas no primeiro pivô; toques separados.\nRompimento: fechamento cruza borda + tolerância; reteste em barra posterior toca região e fecha além da borda, na direção do rompimento.\nFechamento no lado oposto invalida; prazo expirado também. Uma região gera no máximo um padrão.\nAs regras são simétricas para ALTA e BAIXA.\n\nO teste é a parte final cronológica. Motor reinicia na divisão, sem transportar operações/regiões.\nNão ajuste parâmetros usando o teste. Reutilizá-lo para ajuste deixa de ser avaliação independente.\nIntervalo Wilson é descritivo: supõe independência e exclui empates/indeterminadas.\nLucro histórico, sobretudo sintético, não valida estratégia. Não há martingale nem ordens reais.\n\nFontes ao vivo e IA externa não estão ativadas nesta versão. Não há login, custo de IA ou envio de dados.\nExplicações são determinísticas, baseadas no motor. IQ Option: API oficial adequada não confirmada; adaptador legado não oficial fica fora deste aplicativo.\n\nHistórico e configurações ficam em dados locais do usuário. Use Backup para copiar o banco SQLite.\nRestaurar backup: feche o aplicativo e substitua history.sqlite3 na pasta exibida abaixo.\n'''

class App:
    def __init__(self,root,store=None):
        self.root=root;self.store=store or Store()
        self.data=None;self.replay=None;self.running=False;self.run_id=None;self.report_view=None;self.timer=None;self.event_view=[]
        self.root.title('DS Trader — Análise e Simulação')
        self.root.geometry('1240x850');self.root.minsize(950,680)
        style=ttk.Style();style.theme_use('clam')
        style.configure('TButton',padding=7);style.configure('TLabel',padding=3)
        style.configure('Title.TLabel',font=('Segoe UI',19,'bold'))
        head=ttk.Frame(root,padding=(16,12));head.pack(fill='x')
        ttk.Label(head,text='DS Trader',style='Title.TLabel').pack(side='left')
        ttk.Label(head,text='ANÁLISE E SIMULAÇÃO  •  LOCAL  •  SEM ORDENS REAIS').pack(side='left',padx=20)
        bar=ttk.Frame(root,padding=(12,0));bar.pack(fill='x')
        for text,cmd in [('Importar CSV',self.import_file),('Exemplo sintético',self.demo),('Exportar relatório',self.export),('Backup',self.backup)]:
            ttk.Button(bar,text=text,command=lambda f=cmd:self.guard(f)).pack(side='left',padx=3)
        self.mode=tk.StringVar(value='SEM DADOS — importe um CSV ou abra o exemplo')
        ttk.Label(root,textvariable=self.mode,foreground='#985600').pack(fill='x',padx=15)
        choose=ttk.Frame(root,padding=(15,3));choose.pack(fill='x')
        self.asset=ttk.Combobox(choose,state='readonly',width=52);self.asset.pack(side='left')
        ttk.Label(choose,text='De').pack(side='left');self.start=ttk.Entry(choose,width=24);self.start.pack(side='left')
        ttk.Label(choose,text='Até').pack(side='left');self.end=ttk.Entry(choose,width=24);self.end.pack(side='left')
        self.book=ttk.Notebook(root);self.book.pack(fill='both',expand=True,padx=15,pady=8)
        self.chart_tab=ttk.Frame(self.book);self.forex_tab=ttk.Frame(self.book);self.live_tab=ttk.Frame(self.book);self.events_tab=ttk.Frame(self.book);self.report_tab=ttk.Frame(self.book);self.config_tab=ttk.Frame(self.book);self.help_tab=ttk.Frame(self.book)
        for frame,label in [(self.chart_tab,'Gráfico e reprodução'),(self.forex_tab,'Forex em tempo real'),(self.live_tab,'Tela ao vivo'),(self.events_tab,'Sinais e histórico'),(self.report_tab,'Resultados'),(self.config_tab,'Configurações'),(self.help_tab,'Ajuda')]:self.book.add(frame,text=label)
        controls=ttk.Frame(self.chart_tab);controls.pack(fill='x')
        for text,cmd in [('Iniciar / continuar',self.play),('Pausar',self.pause),('Avançar uma barra',self.step_once),('Encerrar',self.stop)]:
            ttk.Button(controls,text=text,command=lambda f=cmd:self.guard(f)).pack(side='left',padx=3,pady=5)
        self.progress=ttk.Progressbar(self.chart_tab);self.progress.pack(fill='x',padx=5)
        self.status=tk.StringVar(value='Sem sinal')
        ttk.Label(self.chart_tab,textvariable=self.status).pack(fill='x')
        self.canvas=tk.Canvas(self.chart_tab,bg='#101b2b',highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self.forex_view=ForexMarketTab(self.forex_tab,self.root)
        self.screen_view=LiveScreenTab(self.live_tab,self.root)
        ttk.Label(self.chart_tab,text='Últimos 90 candles já revelados • horários UTC • regiões azuis • preços sem interpolação').pack()
        self.tree=ttk.Treeview(self.events_tab,columns=('time','asset','phase','status','direction'),show='headings',height=12)
        for key,label in [('time','Horário UTC'),('asset','Ativo'),('phase','Período'),('status','Evento'),('direction','Direção')]:self.tree.heading(key,text=label)
        self.tree.pack(fill='both',expand=True);self.tree.bind('<<TreeviewSelect>>',self.show_event)
        self.detail=tk.Text(self.events_tab,height=8,wrap='word');self.detail.pack(fill='x')
        hist=ttk.Frame(self.report_tab);hist.pack(fill='x')
        self.saved=ttk.Combobox(hist,state='readonly',width=55);self.saved.pack(side='left')
        ttk.Button(hist,text='Abrir histórico salvo',command=lambda:self.guard(self.load_saved)).pack(side='left')
        self.result=tk.Text(self.report_tab,wrap='word',font=('Consolas',11));self.result.pack(fill='both',expand=True)
        self.vars={};config=self.store.config()
        for i,(name,default) in enumerate({**asdict(Parameters()),**asdict(Settings())}.items()):
            ttk.Label(self.config_tab,text=LABELS[name]).grid(row=i,column=0,sticky='w',padx=12)
            var=tk.StringVar(value=str(config.get(name,default)));self.vars[name]=var
            if name=='tie': widget=ttk.Combobox(self.config_tab,textvariable=var,values=['refund','loss'],state='readonly',width=22)
            else: widget=ttk.Entry(self.config_tab,textvariable=var,width=25)
            widget.grid(row=i,column=1,padx=15,pady=2)
        ttk.Label(self.config_tab,text='Hipóteses de teste. Ajuste a largura à escala do ativo.\nMudanças valem somente para a próxima reprodução.\nO período de teste deve ficar reservado; não há otimização automática.',foreground='#985600').grid(row=0,column=2,rowspan=6,padx=10,sticky='nw')
        ttk.Button(self.config_tab,text='Salvar configurações',command=lambda:self.guard(self.save_config)).grid(row=16,column=1,pady=8)
        helptext=tk.Text(self.help_tab,wrap='word');helptext.pack(fill='both',expand=True);helptext.insert('1.0',HELP+'\nBanco: '+str(self.store.path));helptext.configure(state='disabled')
        self.refresh_saved();root.protocol('WM_DELETE_WINDOW',self.close)
    def guard(self,func):
        try:func()
        except Exception as e:messagebox.showerror('DS Trader',str(e),parent=self.root)
    def settings(self):
        vals={}
        defaults={**asdict(Parameters()),**asdict(Settings())}
        for k,d in defaults.items():vals[k]=type(d)(self.vars[k].get())
        return Parameters(**{k:vals[k] for k in asdict(Parameters())}),Settings(**{k:vals[k] for k in asdict(Settings())})
    def save_config(self):
        p,s=self.settings();self.store.save_config({**asdict(p),**asdict(s)})
    def accept(self,data):
        self.stop();self.data=data;self.replay=None;self.report_view=None;self.run_id=None
        self.keys=list(data.groups)
        self.asset['values']=[' | '.join(map(str,k))+'s' for k in self.keys];self.asset.current(0)
        synthetic=all('SINTETICO' in k[1].upper() for k in self.keys)
        self.mode.set('DEMONSTRAÇÃO — DADOS SINTÉTICOS' if synthetic else 'REPRODUÇÃO HISTÓRICA — NÃO É AO VIVO')
        self.status.set('Sem sinal — '+ ('; '.join(data.warnings) or 'CSV validado'))
        self.start.delete(0,'end');self.end.delete(0,'end');self.tree.delete(*self.tree.get_children());self.canvas.delete('all')
    def import_file(self):
        path=filedialog.askopenfilename(filetypes=[('Candles CSV','*.csv')])
        if path:self.accept(read_csv(path))
    def demo(self):self.accept(parse_csv(demo_csv()))
    def new_replay(self):
        if not self.data:raise ValueError('Importe dados primeiro')
        p,s=self.settings();self.save_config()
        bars=self.data.groups[self.keys[self.asset.current()]]
        lo=instant(self.start.get()) if self.start.get().strip() else None
        hi=instant(self.end.get()) if self.end.get().strip() else None
        bars=[b for b in bars if (lo is None or b.candle.instante>=lo) and (hi is None or b.end<=hi)]
        self.replay=Replay(bars,p,s);self.run_id=None;self.report_view=None
        self.tree.delete(*self.tree.get_children())
    def play(self):
        if self.running:return
        if self.timer is not None:
            self.root.after_cancel(self.timer);self.timer=None
        if self.replay is None or self.replay.finished:self.new_replay()
        self.running=True;self.tick()
    def pause(self):
        self.running=False
        if self.timer is not None:self.root.after_cancel(self.timer);self.timer=None
        self.persist()
    def step_once(self):
        self.pause()
        if self.replay is None or self.replay.finished:self.new_replay()
        self.advance()
    def tick(self):
        self.timer=None
        if not self.running:return
        try:
            self.advance()
            if self.replay.finished:self.running=False
            else:self.timer=self.root.after(70,self.tick)
        except Exception as e:
            self.running=False;messagebox.showerror('Reprodução interrompida',str(e))
    def advance(self):
        self.replay.step();self.progress['value']=100*self.replay.index/len(self.replay.bars)
        events=self.replay.events;self.event_view=events
        for i in range(len(self.tree.get_children()),len(events)):
            e=events[i];self.tree.insert('', 'end',iid=str(i),values=[e[k] for k in ('time','asset','phase','status','direction')])
        last=events[-1] if events else None
        current=self.replay.bars[self.replay.index-1].end.isoformat()
        state=last['status'] if last and last['time']==current else 'SEM SINAL'
        self.status.set(f'{self.replay.index}/{len(self.replay.bars)} • {current} UTC • {state}'+(' • ENCERRADO' if self.replay.finished else ''))
        self.draw();self.persist();self.render_report(self.report_view)
    def stop(self):
        self.running=False
        if self.timer is not None:self.root.after_cancel(self.timer);self.timer=None
        if self.replay and not self.replay.finished:
            self.replay.finish('Usuário encerrou antes da liquidação');self.persist();self.render_report(self.report_view)
    def persist(self):
        if self.replay:
            report=self.replay.report();report.update(data_sha256=self.data.digest,input_csv=self.data.raw,warnings=self.data.warnings)
            self.report_view=report;self.run_id=self.store.save(report,self.run_id)
            if self.replay.finished:self.refresh_saved()
    def refresh_saved(self):
        self.saved_rows=self.store.runs();self.saved['values']=[f'{i} — {t}' for i,t in self.saved_rows]
        if self.saved_rows:self.saved.current(0)
    def load_saved(self):
        if self.saved.current()<0:return
        selected=self.saved_rows[self.saved.current()][0]
        self.stop();self.report_view=self.store.get(selected);self.render_report(self.report_view)
        self.event_view=self.report_view['events'];self.tree.delete(*self.tree.get_children())
        for i,e in enumerate(self.event_view):self.tree.insert('', 'end',iid=str(i),values=[e[k] for k in ('time','asset','phase','status','direction')])
    def render_report(self,r):
        if not r:return
        lines=['DS TRADER — RESULTADO SIMULADO',f"Estratégia {r['strategy_version']}",f"Candles: {r['processed']}/{r['total_bars']} | divisão: {r['split_index']}",r['caveats'],'']
        for name,m in [('TOTAL',r['summary']),*r['by_asset_period'].items()]:
            lines += [name,f"Operações: {m['operations']} | {m['counts']}",f"Líquido determinável: {m['net']:.2f} | maior queda: {m['max_drawdown']:.2f} | sequência de perdas: {m['max_loss_streak']}",f"Taxa entre acertos/erros: {m['win_rate']} | Wilson 95%: {m['wilson_95']}",f"Payouts na entrada: {m['payouts']} | equilíbrio fixo 1/(1+p): {m['break_even']}",'']
        lines += [r['summary']['uncertainty'],'','OPERAÇÕES (detalhes completos no JSON/CSV)']
        for t in r['trades']:lines.append(f"{t['asset']} {t['phase']} {t['direction']} | sinal {t['time']} | entrada {t['entry_time']} @ {t['entry_price']} | expira {t['expiry']} | payout {t['payout']} ({t['payout_type']}) | {t['result']} | {t['pnl']} | {t['reason_result']}")
        self.result.delete('1.0','end');self.result.insert('1.0','\n'.join(lines))
    def show_event(self,event=None):
        if not self.tree.selection():return
        e=self.event_view[int(self.tree.selection()[0])]
        text=explain(e)
        for t in (self.report_view or {}).get('trades',[]):
            if t['time']==e['time'] and t['zone_id']==e['zone_id']:
                text+=f"\nEntrada {t['entry_time']} | expiração {t['expiry']} | payout {t['payout']} ({t['payout_type']})\nResultado: {t['result']} — {t['reason_result']}"
        self.detail.delete('1.0','end');self.detail.insert('1.0',text)
    def draw(self):
        self.canvas.delete('all')
        if not self.replay or not self.replay.index:return
        bars=self.replay.bars[max(0,self.replay.index-90):self.replay.index]
        w,h=self.canvas.winfo_width(),self.canvas.winfo_height()
        if w<100 or h<80:return
        low=min(b.candle.minima for b in bars);high=max(b.candle.maxima for b in bars)
        span=max(high-low,1e-9);low-=span*.1;high+=span*.1
        def y(p):return 18+(high-p)/(high-low)*(h-55)
        dx=(w-110)/len(bars)
        for j in range(5):
            price=low+(high-low)*j/4;yy=y(price)
            self.canvas.create_line(5,yy,w-95,yy,fill='#263448');self.canvas.create_text(w-48,yy,text=f'{price:.6g}',fill='#bdcadb')
        for z in self.replay.strategy.zones:
            if len(z['touches'])>=self.replay.parameters.min_touches and low<=z['lower']<=high:
                self.canvas.create_rectangle(5,y(z['upper']),w-95,y(z['lower']),outline='#418cdd',dash=(4,3))
        for i,b in enumerate(bars):
            c=b.candle;x=8+(i+.5)*dx;color='#36d6a0' if c.fechamento>=c.abertura else '#f5757a'
            self.canvas.create_line(x,y(c.maxima),x,y(c.minima),fill=color)
            top,bottom=sorted([y(c.abertura),y(c.fechamento)])
            self.canvas.create_rectangle(x-dx*.3,top,x+dx*.3,max(top+1,bottom),fill=color,outline=color)
        self.canvas.create_text(10,h-12,text=bars[0].candle.instante.strftime('%Y-%m-%d %H:%M:%S UTC'),fill='#bdcadb',anchor='w')
        self.canvas.create_text(w-100,h-12,text=bars[-1].end.strftime('%H:%M:%S UTC'),fill='#bdcadb',anchor='e')
    def export(self):
        if not self.report_view:raise ValueError('Execute uma simulação ou abra um histórico')
        path=filedialog.asksaveasfilename(defaultextension='.json',initialfile='ds-trader-relatorio.json')
        if path:export_report(self.report_view,path);messagebox.showinfo('Exportado','JSON e CSVs de operações e eventos salvos.')
    def backup(self):
        path=filedialog.asksaveasfilename(defaultextension='.sqlite3',initialfile='ds-trader-backup.sqlite3')
        if path:self.store.backup(path)
    def close(self):
        self.forex_view.shutdown()
        self.screen_view.shutdown()
        self.stop();self.store.close();self.root.destroy()

def main():
    # Capturas mss usam pixels fisicos; alinhar as coordenadas do Tk em Windows HiDPI.
    import sys
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
    root=tk.Tk();App(root);root.mainloop()
