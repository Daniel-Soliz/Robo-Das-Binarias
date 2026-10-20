"""Interface do feed Forex. Nunca roda no thread grafico nem persiste credenciais."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
from queue import Empty
from ds_trader.forex_live import PAIRS, INTERVALS, ForexWatcher
from ds_trader.next_candle import evaluate_next

class ForexMarketTab:
    def __init__(self, parent, root):
        self.root=root
        self.watcher=None
        self.timer=None
        self.running=False
        self.view=None
        self.last_opinion=None
        self.pair=tk.StringVar(value="EUR/USD")
        self.interval=tk.StringVar(value="1min")
        self.refresh=tk.StringVar(value="120")
        self.key=tk.StringVar()
        heading=ttk.Frame(parent,padding=12)
        heading.pack(fill="x")
        ttk.Label(heading,text="FOREX — CANDLES REAIS DO FORNECEDOR",
                  font=("Segoe UI",13,"bold")).pack(anchor="w")
        ttk.Label(heading,text=(
            "Fonte Twelve Data • dados por API de terceiros • fechamento de candles de 1/5/15 minutos. "
            "Nao e IQ Option, nao sao ticks em tempo real. Credencial nao e salva."
        ),wraplength=990).pack(anchor="w",pady=(3,8))
        row=ttk.Frame(heading);row.pack(fill="x")
        ttk.Label(row,text="Par").pack(side="left")
        self.pair_box=ttk.Combobox(row,textvariable=self.pair,values=PAIRS,width=11,state="readonly")
        self.pair_box.pack(side="left",padx=(3,12))
        ttk.Label(row,text="Periodo").pack(side="left")
        self.interval_box=ttk.Combobox(row,textvariable=self.interval,values=list(INTERVALS),width=8,state="readonly")
        self.interval_box.pack(side="left",padx=(3,12))
        ttk.Label(row,text="Atualizar (s)").pack(side="left")
        self.refresh_box=ttk.Combobox(row,textvariable=self.refresh,values=["120","60","300"],width=6,state="readonly")
        self.refresh_box.pack(side="left",padx=(3,12))
        ttk.Label(row,text="Chave API").pack(side="left")
        self.key_entry=ttk.Entry(row,textvariable=self.key,show="●",width=21)
        self.key_entry.pack(side="left",padx=(3,6))
        ttk.Label(heading,text=(
            "A chave e obtida na Twelve Data; pode haver limite/custo conforme o plano. "
            "Uma consulta a cada 120 s equivale a ate 720 por dia. Nunca cole a chave no chat."
        ),wraplength=990).pack(anchor="w",pady=(7,4))
        buttons=ttk.Frame(heading);buttons.pack(fill="x",pady=(5,7))
        self.go=ttk.Button(buttons,text="Conectar ao mercado",command=self.start)
        self.go.pack(side="left")
        self.stop_btn=ttk.Button(buttons,text="Desconectar",command=self.stop,state="disabled")
        self.stop_btn.pack(side="left",padx=8)
        self.status=tk.StringVar(value="DESCONECTADO — insira sua chave de API para receber candles reais.")
        ttk.Label(parent,textvariable=self.status,foreground="#985600",wraplength=1030).pack(anchor="w",padx=15)
        self.next_candle=tk.StringVar(value="PROXIMA VELA: AGUARDAR — sem candles recentes")
        ttk.Label(parent,textvariable=self.next_candle,
                  font=("Segoe UI",14,"bold"),foreground="#146f9f",
                  wraplength=1010).pack(anchor="w",padx=15,pady=(5,4))
        self.pattern_notes=tk.StringVar(value="Padroes / LTA / LTB: aguardando candles.")
        ttk.Label(parent,textvariable=self.pattern_notes,
                  wraplength=1010).pack(anchor="w",padx=15,pady=(0,4))
        self.context=tk.StringVar(value="Aguardando dados do fornecedor. Nenhuma leitura do mercado atual esta disponivel.")
        ttk.Label(parent,textvariable=self.context,wraplength=1040,justify="left").pack(anchor="w",padx=15,pady=(4,6))
        self.prices=tk.StringVar(value="Suporte/resistencia: aguardando cotações verificadas")
        ttk.Label(parent,textvariable=self.prices,wraplength=1040).pack(anchor="w",padx=15,pady=(0,6))
        self.canvas=tk.Canvas(parent,bg="#101b2b",highlightthickness=0)
        self.canvas.pack(fill="both",expand=True,padx=13,pady=(3,6))
        self.canvas.bind("<Configure>",lambda _evt:self.draw())
        ttk.Label(parent,text=(
            "LEITURA EDUCACIONAL • Sem envio de ordens ou CALL/PUT • Cada fonte pode ter preco diferente. "
            "Se o mercado estiver fechado, atrasado ou sem rede, o sistema interrompe a analise."
        ),wraplength=1010,foreground="#985600").pack(anchor="w",padx=15,pady=(0,10))

    def start(self):
        if self.running:return
        key=self.key.get().strip()
        if len(key)<6 or any(c.isspace() for c in key):
            messagebox.showwarning("Twelve Data","Informe uma chave de API valida na propria janela.",parent=self.root)
            return
        try:
            self.watcher=ForexWatcher(key,self.pair.get(),self.interval.get(),int(self.refresh.get()))
        except ValueError as exc:
            messagebox.showerror("DS Trader",str(exc),parent=self.root)
            return
        self.key.set("")   # nao deixar credencial visivel em memoria do widget
        self.running=True
        self.view=None
        self.go.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        for box in (self.pair_box,self.interval_box,self.refresh_box,self.key_entry):
            box.configure(state="disabled")
        self.context.set("Aguardando resposta da Twelve Data...")
        self.prices.set("Aguardando candles fechados...")
        self.canvas.delete("all")
        self.last_opinion=None
        self.next_candle.set("PROXIMA VELA: AGUARDAR — aguardando fonte de mercado")
        self.status.set("CONECTANDO — consultando API de dados, sem executar ordens.")
        self.watcher.start()
        self.poll()

    def poll(self):
        self.timer=None
        if not self.running:return
        try:
            while True:
                kind,value=self.watcher.results.get_nowait()
                if kind=="error":
                    self.view=None
                    self.last_opinion=None
                    self.next_candle.set("PROXIMA VELA: AGUARDAR — fornecedor indisponivel")
                    self.pattern_notes.set("Sem padroes ate nova confirmacao.")
                    self.canvas.delete("all")
                    self.status.set("SEM COTACAO VERIFICADA — "+value)
                    self.context.set("Sem analise enquanto o fornecedor estiver indisponivel.")
                    self.prices.set("Niveis suspensos")
                else:
                    self.view=value
                    self.status.set(
                        f"{value.status} — {value.pair} {value.interval} • origem: {value.source} • "
                        f"ultimo candle fechado: {value.last_closed_at.strftime('%d/%m/%Y %H:%M UTC')} • "
                        f"atraso observado: {value.age_seconds:.0f} s"
                    )
                    if value.status == "ATUALIZADO":
                        self.last_opinion = evaluate_next(value.candles,source="api",closed_confirmed=True)
                        # M1 exige latencia minima. Sem cotacao quase imediata nao há "proxima vela".
                        max_signal_age=min(60,max(20,INTERVALS[value.interval]*.12))
                        can_reference_next=value.age_seconds <= max_signal_age
                        side=self.last_opinion.side if can_reference_next else "AGUARDAR"
                        late="" if can_reference_next else " (ultima vela fechou ha tempo demais)"
                        self.next_candle.set(
                            f"PROXIMA VELA: {side} — hipotese educacional, NAO e entrada IQ Option"+late)
                        self.pattern_notes.set(
                            "Padroes: "+(", ".join(self.last_opinion.patterns) or "nenhum")+
                            " | LTA: "+("sim" if self.last_opinion.lta else "nao")+
                            " | LTB: "+("sim" if self.last_opinion.ltb else "nao")+
                            " | Motivos: "+" ".join(self.last_opinion.reasons[-3:]))
                    else:
                        self.last_opinion=None
                        self.next_candle.set("PROXIMA VELA: AGUARDAR — cotacao atrasada/mercado fechado")
                        self.pattern_notes.set("Nao emitir hipotese com dados sem frescor.")
                    self.context.set(value.summary)
                    support = f"{value.support:.6f}" if value.support is not None else "nao confirmado"
                    resistance = f"{value.resistance:.6f}" if value.resistance is not None else "nao confirmada"
                    self.prices.set(f"Suporte: {support} • Resistencia: {resistance} • {value.zone_note}")
                    self.draw()
        except Empty:
            pass
        if self.view is not None and self.view.status=="ATUALIZADO":
            elapsed=(datetime.now(timezone.utc)-self.view.last_closed_at).total_seconds()
            limit=max(3*INTERVALS[self.view.interval],180)
            if elapsed>limit:
                self.view=None
                self.last_opinion=None
                self.next_candle.set("PROXIMA VELA: AGUARDAR — dados vencidos")
                self.canvas.delete("all")
                self.status.set("ATRASADO — nenhuma cotacao recente confirmada")
                self.context.set("Exibicao suspensa ate receber novos candles fechados do fornecedor.")
                self.prices.set("Suporte/resistencia suspensos por falta de dados recentes.")
        self.timer=self.root.after(200,self.poll)

    def draw(self):
        self.canvas.delete("all")
        if self.view is None:return
        bars=self.view.candles[-75:]
        if not bars:return
        w=self.canvas.winfo_width();h=self.canvas.winfo_height()
        if w<200 or h<110:return
        raw_low=min(c.low for c in bars);raw_high=max(c.high for c in bars)
        span=max(1e-9,raw_high-raw_low);lo=raw_low-span*.07;hi=raw_high+span*.07
        def y(price):return 15+(hi-price)/(hi-lo)*(h-50)
        for i in range(5):
            p=lo+(hi-lo)*i/4;py=y(p)
            self.canvas.create_line(5,py,w-96,py,fill="#273951")
            self.canvas.create_text(w-47,py,text=f"{p:.6f}",fill="#d9e3ee")
        dx=(w-115)/len(bars)
        for index,c in enumerate(bars):
            x=10+(index+.5)*dx
            color="#35d5a6" if c.close>=c.open else "#f5757a"
            self.canvas.create_line(x,y(c.high),x,y(c.low),fill=color)
            top,bottom=sorted((y(c.open),y(c.close)))
            self.canvas.create_rectangle(x-dx*.28,top,x+dx*.28,max(bottom,top+1),outline=color,fill=color)
        if self.view.status=="ATUALIZADO":
            for price,shade in ((self.view.support,"#3686e7"),(self.view.resistance,"#d2a65e")):
                if price is not None and lo<=price<=hi:
                    self.canvas.create_line(3,y(price),w-96,y(price),fill=shade,dash=(6,3),width=2)
        # Linhas de tendencia pelos dois ultimos fundos/topos confirmados,
        # projeção apenas grafica, sem extrapolar rentabilidade.
        if self.last_opinion and self.view.status=="ATUALIZADO":
            for line,color in ((self.last_opinion.lta,"#36b5f4"),
                               (self.last_opinion.ltb,"#f7aa60")):
                if line is None:
                    continue
                slope=line[1]-line[0]
                old=line[1]-slope*min(len(bars)-1,18)
                x_left=10+(max(0,len(bars)-19)+.5)*dx
                x_right=10+(len(bars)-.5)*dx
                if lo<=old<=hi or lo<=line[1]<=hi:
                    self.canvas.create_line(x_left,y(old),x_right,y(line[1]),
                                            fill=color,dash=(5,3),width=2)
        self.canvas.create_text(10,h-15,text=bars[0].opened.strftime("%d/%m %H:%M UTC"),
                                fill="#b0c5d9",anchor="w")
        self.canvas.create_text(w-100,h-15,text=bars[-1].opened.strftime("%H:%M UTC"),
                                fill="#b0c5d9",anchor="e")

    def stop(self):
        self.running=False
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer=None
        if self.watcher:
            self.watcher.stop()
            self.watcher=None
        self.key.set("")
        self.go.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        for box in (self.pair_box,self.interval_box,self.refresh_box):
            box.configure(state="readonly")
        self.key_entry.configure(state="normal")
        self.view=None
        self.last_opinion=None
        self.next_candle.set("PROXIMA VELA: AGUARDAR — desconectado")
        self.pattern_notes.set("Padroes / LTA / LTB: aguardando candles.")
        self.canvas.delete("all")
        self.status.set("DESCONECTADO — consultas interrompidas.")
        self.context.set("Sem leitura atual. Para voltar a consultar, informe a chave novamente.")
        self.prices.set("Suporte/resistencia: aguardando cotações.")

    def shutdown(self):
        self.stop()
