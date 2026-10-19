"""Seleção guiada de regiões por arraste do mouse (somente leitura)."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QDialog

from config import Configuracao, Regiao


class SeletorRegiao(QDialog):
    """Janela temporária sobre o desktop virtual para selecionar um retângulo."""

    def __init__(self, titulo: str, largura_minima: int, altura_minima: int):
        super().__init__()
        self.titulo = titulo
        self.largura_minima = largura_minima
        self.altura_minima = altura_minima
        self.inicio: QPoint | None = None
        self.fim: QPoint | None = None
        self.regiao: Regiao | None = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        tela = QApplication.primaryScreen()
        if tela is None:
            raise RuntimeError("Nenhum monitor disponível para calibração.")
        self.setGeometry(tela.virtualGeometry())
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, _evento) -> None:
        pintor = QPainter(self)
        pintor.fillRect(self.rect(), QColor(8, 12, 20, 110))
        if self.inicio is not None and self.fim is not None:
            retangulo = QRect(self.inicio, self.fim).normalized()
            pintor.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pintor.fillRect(retangulo, Qt.GlobalColor.transparent)
            pintor.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pintor.setPen(QPen(QColor("#47DBB4"), 2))
            pintor.drawRect(retangulo)
        pintor.setFont(QFont("Segoe UI", 15))
        pintor.setPen(QPen(QColor("white")))
        pintor.drawText(24, 44, self.titulo + " — arraste o mouse; Esc cancela")

    def mousePressEvent(self, evento: QMouseEvent) -> None:
        if evento.button() == Qt.MouseButton.LeftButton:
            self.inicio = evento.position().toPoint()
            self.fim = self.inicio
            self.update()

    def mouseMoveEvent(self, evento: QMouseEvent) -> None:
        if self.inicio is not None:
            self.fim = evento.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, evento: QMouseEvent) -> None:
        if evento.button() != Qt.MouseButton.LeftButton or self.inicio is None:
            return
        self.fim = evento.position().toPoint()
        area = QRect(self.inicio, self.fim).normalized()
        if area.width() < self.largura_minima or area.height() < self.altura_minima:
            self.inicio = None
            self.fim = None
            self.update()
            return
        global_inicio = self.mapToGlobal(area.topLeft())
        self.regiao = Regiao(
            left=global_inicio.x(),
            top=global_inicio.y(),
            width=area.width(),
            height=area.height(),
        )
        self.accept()

    def keyPressEvent(self, evento: QKeyEvent) -> None:
        if evento.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(evento)


def calibrar_tela(configuracao: Configuracao) -> Configuracao:
    """Solicita duas áreas; não altera a configuração se houver cancelamento."""
    if QApplication.instance() is None:
        QApplication([])
    grafico = SeletorRegiao("Selecione apenas o gráfico com as velas", 100, 80)
    if grafico.exec() != QDialog.DialogCode.Accepted or grafico.regiao is None:
        raise RuntimeError("Calibração do gráfico cancelada.")
    cabecalho = SeletorRegiao("Selecione o nome do ativo E o período M5/M15", 80, 20)
    if cabecalho.exec() != QDialog.DialogCode.Accepted or cabecalho.regiao is None:
        raise RuntimeError("Calibração do cabeçalho cancelada.")
    configuracao.regiao_grafico = grafico.regiao
    configuracao.regiao_cabecalho = cabecalho.regiao
    configuracao.validar()
    return configuracao

