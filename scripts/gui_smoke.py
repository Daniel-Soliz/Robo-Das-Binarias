"""Smoke test real do Tk e persistência; requer sessão gráfica (Windows CI)."""
import json
import tempfile
from pathlib import Path
from ds_trader.ui import App
from ds_trader.storage import Store, export_report
import tkinter as tk

def run():
    with tempfile.TemporaryDirectory() as tmp:
        root=tk.Tk();store=Store(Path(tmp)/'state.sqlite3');app=App(root,store)
        root.update()
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
        app.demo();app.new_replay()
        for _ in range(15):app.advance();root.update()
        assert app.canvas.find_all(), 'Gráfico não desenhado'
        app.pause();assert not app.running
        while not app.replay.finished:app.advance()
        root.update();assert app.replay.trades
        app.refresh_saved();app.load_saved()
        report=app.report_view
        export_report(report,Path(tmp)/'report.json')
        assert (Path(tmp)/'report_trades.csv').exists()
        app.close()
        reopened=Store(Path(tmp)/'state.sqlite3');assert reopened.runs();reopened.close()
        return {'gui':'passed','candles':report['processed'],'operations':len(report['trades']),'persistence':'passed','export':'passed','forex_tab':'passed'}

if __name__=='__main__':print(json.dumps(run()))
