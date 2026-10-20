"""Aba de leitura visual da tela. Captura iniciada e encerrada pelo usuario."""
import tkinter as tk
from tkinter import messagebox, ttk
from queue import Empty
from ds_trader.live_screen import Region, ScreenMonitor


class RegionPicker:
    """Selecao visual por arraste na area do desktop (sem guardar imagem)."""
    def __init__(self, master, on_select, on_cancel=None):
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.window = tk.Toplevel(master)
        self.window.title("Selecione a area do grafico")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg="#111827")
        self.window.attributes("-alpha", .32)
        # mss usa coordenadas globais, inclusive monitores a esquerda do principal.
        try:
            from mss import mss
            with mss() as capture:
                desktop = capture.monitors[0]
        except Exception:
            self.window.destroy()
            raise RuntimeError("Instale a versao completa do DS Trader com captura de tela")
        self.left, self.top = desktop["left"], desktop["top"]
        self.window.geometry(f'{desktop["width"]}x{desktop["height"]}{self.left:+d}{self.top:+d}')
        self.canvas = tk.Canvas(self.window, bg="#111827", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(30, 38, text="Arraste sobre SOMENTE o grafico de candles  •  Esc cancela",
                                anchor="w", fill="#ffffff", font=("Segoe UI", 17, "bold"))
        self.first = None
        self.rectangle = None
        self.canvas.bind("<ButtonPress-1>", self.begin)
        self.canvas.bind("<B1-Motion>", self.move)
        self.canvas.bind("<ButtonRelease-1>", self.finish)
        self.window.bind("<Escape>", lambda _e: self.cancel())
        self.window.focus_force()
        self.window.grab_set()

    def begin(self, event):
        self.first = (event.x_root, event.y_root)
        if self.rectangle is not None:
            self.canvas.delete(self.rectangle)
            self.rectangle = None

    def move(self, event):
        if self.first is None:
            return
        x0, y0 = self.first
        x1, y1 = event.x_root, event.y_root
        a, b = x0-self.left, y0-self.top
        c, d = x1-self.left, y1-self.top
        if self.rectangle is None:
            self.rectangle = self.canvas.create_rectangle(a, b, c, d, outline="#48ecfc", width=4)
        else:
            self.canvas.coords(self.rectangle, a, b, c, d)

    def finish(self, event):
        if self.first is None:
            return
        x0, y0 = self.first
        left, right = sorted((x0, event.x_root))
        top, bottom = sorted((y0, event.y_root))
        try:
            selection = Region(left, top, right-left, bottom-top)
        except ValueError:
            messagebox.showwarning("DS Trader", "Arraste uma area maior (minimo 180 x 120 pixels).",
                                   parent=self.window)
            self.first = None
            return
        self.cancel(notify=False)
        self.on_select(selection)

    def cancel(self, notify=True):
        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        self.window.destroy()
        if notify and self.on_cancel is not None:
            self.on_cancel()


class LiveScreenTab:
    def __init__(self, parent, root):
        self.root = root
        self.region = None
        self.monitor = None
        self.after_id = None
        self.preview_image = None
        self.active = False
        top = ttk.Frame(parent, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="LEITURA VISUAL AO VIVO — SOMENTE TELA",
                  font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(top, text=(
            "Abra seu grafico no navegador, deixe os candles visiveis e selecione so aquela area. "
            "A leitura roda neste computador; nao envia imagens e nao realiza operacoes."
        ), wraplength=900).pack(anchor="w", pady=(4, 10))
        controls = ttk.Frame(top)
        controls.pack(fill="x")
        self.pick_btn = ttk.Button(controls, text="1. Selecionar area do grafico", command=self.select)
        self.pick_btn.pack(side="left", padx=(0, 8))
        self.start_btn = ttk.Button(controls, text="2. Iniciar monitoramento", command=self.start)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(controls, text="Parar", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left")
        self.status = tk.StringVar(value="Parado — selecione primeiro a area do grafico.")
        ttk.Label(top, textvariable=self.status, wraplength=930,
                  foreground="#336faa").pack(anchor="w", pady=(12, 5))
        self.next_opinion=tk.StringVar(value="PROXIMA VELA: AGUARDAR — captura nao iniciada")
        self.bias_label=ttk.Label(top,textvariable=self.next_opinion,font=("Segoe UI",15,"bold"),
                                  foreground="#1c6388",wraplength=980)
        self.bias_label.pack(anchor="w",pady=(5,6))
        self.structures=tk.StringVar(value="Padroes / LTA / LTB: aguardando reconhecimento.")
        ttk.Label(top,textvariable=self.structures,wraplength=970).pack(anchor="w",pady=(0,4))
        self.observation = tk.StringVar(value="Sem observacoes; aguardando captura.")
        ttk.Label(top, textvariable=self.observation, wraplength=930,
                  justify="left").pack(anchor="w", pady=5)
        view = ttk.Frame(parent, padding=(12, 0, 12, 10))
        view.pack(fill="both", expand=True)
        self.image_label = tk.Label(view, bg="#101b2b", fg="#b4c9d9",
                                    text="A previa do grafico selecionado aparecera aqui.",
                                    anchor="center")
        self.image_label.pack(fill="both", expand=True)
        ttk.Label(parent, text=(
            "Limite: pixels nao sao cotacoes verificadas. A ultima vela pode estar aberta. "
            "CALL/PUT é apenas uma hipótese visual experimental, não previsão confiável; sem horário de fechamento, payout ou vencimento. "
            "Dados historicos permanecem no modo CSV."
        ), wraplength=920, foreground="#985600").pack(anchor="w", padx=15, pady=(0, 12))

    def select(self):
        if self.active:
            self.stop()
        try:
            RegionPicker(self.root, self.selected)
            self.status.set("Arraste o cursor sobre o grafico; pressione Esc para cancelar.")
        except Exception as exc:
            messagebox.showerror("Leitura de tela", str(exc), parent=self.root)

    def selected(self, region):
        self.region = region
        self.status.set(f"Area selecionada: {region.width} x {region.height} pixels. Clique em Iniciar monitoramento.")
        self.observation.set("Nenhuma captura efetuada. Monitoramento desligado.")
        self.next_opinion.set("PROXIMA VELA: AGUARDAR — ainda sem dados")

    def start(self):
        if self.active:
            return
        if self.region is None:
            messagebox.showinfo("DS Trader", "Selecione primeiro a area do grafico.", parent=self.root)
            return
        self.monitor = ScreenMonitor(self.region, interval_seconds=1.2)
        self.active = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.pick_btn.configure(state="disabled")
        self.status.set("Monitoramento em execucao — leitura local a cada 1,2 s.")
        self.monitor.start()
        self.poll()

    def poll(self):
        self.after_id = None
        if not self.active:
            return
        try:
            while True:
                item = self.monitor.results.get_nowait()
                if item[0] == "error":
                    self.stop()
                    self.status.set(item[1])
                    return
                result, frame = item
                from PIL import ImageTk
                self.preview_image = ImageTk.PhotoImage(frame)
                self.image_label.configure(image=self.preview_image, text="")
                self.status.set("Atualizado: " + result.captured_at + " UTC • " + result.movement)
                self.next_opinion.set(
                    "PROXIMA VELA: " + result.bias +
                    " — HIPOTESE VISUAL NAO VALIDADA, NAO E ORDEM"
                )
                self.bias_label.configure(foreground={
                    "CALL":"#147b63",
                    "PUT":"#ae454a",
                    "AGUARDAR":"#8f6c1a"
                }.get(result.bias,"#8f6c1a"))
                self.structures.set(
                    "Padroes: " + (", ".join(result.patterns) or "nao reconhecidos") +
                    " | Estruturas: " + (", ".join(result.structures) or "insuficientes")
                )
                self.observation.set(result.explanation)
        except Empty:
            pass
        self.after_id = self.root.after(170, self.poll)

    def stop(self):
        self.active = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.monitor:
            self.monitor.stop()
            self.monitor = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.pick_btn.configure(state="normal")
        self.status.set("Monitoramento parado. Nenhuma imagem foi salva ou enviada.")
        self.next_opinion.set("PROXIMA VELA: AGUARDAR — captura interrompida")

    def shutdown(self):
        self.stop()
