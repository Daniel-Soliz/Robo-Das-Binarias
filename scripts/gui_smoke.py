"""Smoke test real do Tk e persistência; requer sessão gráfica (Windows CI)."""
import json
import tempfile
from pathlib import Path
from ds_trader.ui import App
from ds_trader.storage import Store, export_report
import tkinter as tk
import faulthandler
import time


def _checkpoint(stage):
    with open('smoke-progress.txt','a',encoding='utf-8') as output:
        output.write(f'{time.strftime("%H:%M:%S")} | {stage}\n')
        output.flush()

def run():
    Path('smoke-progress.txt').write_text('',encoding='utf-8')
    diag = open('smoke-trace.txt','w',encoding='utf-8')
    faulthandler.dump_traceback_later(55,repeat=True,file=diag)
    _checkpoint('smoke iniciado')
    with tempfile.TemporaryDirectory() as tmp:
        _checkpoint('antes Tk()')
        root=tk.Tk();store=Store(Path(tmp)/'state.sqlite3')
        _checkpoint('antes App()')
        app=App(root,store)
        _checkpoint('apos App()')
        _checkpoint('antes root.update()')
        root.update()
        _checkpoint('apos root.update()')
        # A nova shell deve substituir a barra de abas antiga por navegacao real.
        assert app.shell.current == 'forex', 'Pagina inicial do dashboard nao e Forex'
        assert len(app.shell.nav_buttons) == 8, 'Navegacao lateral incompleta'
        assert app.forex_view.view is None, 'Nao inventar candles antes da conexao'
        assert app.forex_view.next_candle.get().startswith('PROXIMA VELA: AGUARDAR')
        assert not app.forex_view.running, 'Nao conectar a API automaticamente'
        assert 'AGUARDAR' in app.forex_view.side_label.cget('text'), 'Card inicial inseguro'
        app.forex_view.set_chart_type('line')
        assert app.forex_view.chart_type == 'line', 'Controle linha inoperante'
        app.forex_view.set_chart_type('candles')
        app.forex_view.toggle_expand()
        assert app.forex_view.expanded, 'Expandir grafico inoperante'
        app.forex_view.toggle_expand()
        assert not app.forex_view.expanded, 'Restaurar painéis inoperante'
        app.shell.go('overview')
        assert app.book.select() == str(app.overview_tab), 'Visao geral inacessivel'
        app.shell.go('live')
        assert app.book.select() == str(app.live_tab), 'Tela ao vivo inacessivel'
        app.shell.go('forex')
        assert app.book.select() == str(app.forex_tab), 'Forex inacessivel'
        assert app.screen_view is not None, 'Aba de monitoramento visual ausente'
        assert app.screen_view.container.cget('bg') == '#08111f', 'Tema escuro ausente'
        assert app.screen_view.next_opinion.get() == 'AGUARDAR', 'Sinal inicial inseguro'
        assert app.screen_view.m1_cycle.results == [], 'Captura nao pode criar entradas M1'
        assert 'captura visual' in app.screen_view.cycle_message.get(), 'Motivo do bloqueio M1 ausente'
        app.screen_view.timeframe.set('M5')
        assert 'não é M1' in app.screen_view.cycle_message.get(), 'Troca de periodo nao bloqueada'
        app.screen_view.timeframe.set('M1')
        assert app.screen_view.m1_cycle.status().side == 'AGUARDAR', 'Ciclo visual inseguro'
        assert app.screen_view.start_btn.cget('state') == 'disabled', 'Iniciar sem selecionar grafico'
        from ds_trader.live_screen import Region
        from ds_trader.window_capture import WindowTarget
        sample_target=WindowTarget(123, 456, "Navegador de teste", (0,0,800,500),
                                   (0,0,700,400))
        app.screen_view.selected(Region(0, 0, 700, 400),window_target=sample_target)
        assert app.screen_view.start_btn.cget('state') == 'normal', 'Selecionar nao habilitou iniciar'
        assert app.screen_view.window_target == sample_target, 'Janela nao foi fixada'
        app.screen_view.stop()
        assert app.screen_view.next_opinion.get() == 'AGUARDAR', 'Parar nao limpou sinal'
        assert app.forex_view is not None, 'Aba Forex ausente'
        assert not app.forex_view.running, 'Forex nao pode conectar automaticamente'
        assert not app.screen_view.active, 'Captura nao pode iniciar sem consentimento'
        # O dashboard abre no Forex. O canvas do replay só recebe tamanho
        # real quando sua página fica visível; jamais validar canvas oculto.
        _checkpoint('selecionando aba grafico e reproducao')
        app.shell.go('chart')
        root.update()
        _checkpoint('antes app.demo()')
        app.demo();app.new_replay()
        _checkpoint('apos app.demo()')
        _checkpoint('antes 15 updates')
        for _ in range(15):app.advance();root.update()
        _checkpoint('apos 15 updates')
        app.draw()
        assert app.canvas.winfo_width() > 100, 'Canvas grafico nao recebeu geometria'
        assert app.canvas.find_all(), 'Gráfico nao desenhado após abrir aba de reproducao'
        app.pause();assert not app.running
        _checkpoint('antes replay ate fim')
        while not app.replay.finished:app.advance()
        _checkpoint('apos replay ate fim')
        _checkpoint('antes root.update() final')
        root.update();assert app.replay.trades
        _checkpoint('apos root.update() final')
        app.refresh_saved();app.load_saved()
        report=app.report_view
        export_report(report,Path(tmp)/'report.json')
        assert (Path(tmp)/'report_trades.csv').exists()
        _checkpoint('antes app.close()')
        app.close()
        _checkpoint('apos app.close()')
        reopened=Store(Path(tmp)/'state.sqlite3');assert reopened.runs();reopened.close()
        faulthandler.cancel_dump_traceback_later()
        diag.close()
        _checkpoint('smoke concluido')
        return {'gui':'passed','candles':report['processed'],'operations':len(report['trades']),'persistence':'passed','export':'passed','forex_tab':'passed'}

if __name__=='__main__':print(json.dumps(run()))
