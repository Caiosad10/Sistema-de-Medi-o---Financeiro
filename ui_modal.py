"""
ui_modal.py — Modais "glass" no tema Bento UI do SisMed.

Substitui o QMessageBox do sistema por diálogos modernos:
- A janela principal fica escurecida e desfocada (print da tela + blur)
- Painel central arredondado, semi-transparente, cores do sistema
- Janelas de escolher/salvar ARQUIVO (QFileDialog) continuam nativas do Windows

Uso:
    from ui_modal import confirmar, informar, alerta, erro, planilha_pronta

    if confirmar(self, "Fechar Medição", "Deseja continuar?"):
        ...
    informar(self, "Sucesso", "Lançamento salvo!")
"""
import os

from PySide6.QtCore import Qt, QEvent, QEventLoop
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect,
)

import utils

_ICONES = {
    "pergunta": "❓",
    "info": "ℹ️",
    "sucesso": "✅",
    "alerta": "⚠️",
    "erro": "❌",
}

_LARGURA_MIN = 420
_LARGURA_MAX = 600


def _capturar_desfocado(janela, raio=16):
    """Tira um 'print' da janela e devolve desfocado (simula o blur do fundo)."""
    if janela is None:
        return QPixmap()
    pix = janela.grab()
    cena = QGraphicsScene()
    item = QGraphicsPixmapItem(pix)
    efeito = QGraphicsBlurEffect()
    efeito.setBlurRadius(raio)
    efeito.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(efeito)
    cena.addItem(item)
    img = QImage(pix.size(), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    cena.render(painter)
    painter.end()
    return QPixmap.fromImage(img)


class _ModalGlass(QWidget):
    """Modal glass: child widget da janela principal, cobre toda a area como overlay."""

    def __init__(self, janela, titulo, mensagem, tipo, botoes):
        super().__init__(janela)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._janela = janela
        self._botoes = botoes
        self.resultado = None
        self._fundo = None
        self._fundo_label = None
        self._overlay = None
        self._loop = None

        # Define a geometria ANTES de montar o painel, para que
        # self.width()/self.height() tenham o tamanho correto.
        if janela is not None:
            self.setGeometry(janela.rect())
        else:
            self.resize(600, 400)

        # Captura o fundo DESFOCADO DEPOIS de ter geometria
        self._fundo = _capturar_desfocado(janela)

        self._montar_painel(titulo, mensagem, tipo, botoes)

        if janela is not None:
            janela.installEventFilter(self)

    def _montar_painel(self, titulo, mensagem, tipo, botoes):
        # Camada 1: fundo desfocado da janela principal
        if self._fundo and not self._fundo.isNull():
            self._fundo_label = QLabel(self)
            self._fundo_label.setPixmap(self._fundo)
            self._fundo_label.setScaledContents(True)
            self._fundo_label.setGeometry(0, 0, self.width(), self.height())
            self._fundo_label.lower()

        # Camada 2: overlay escurecido
        self._overlay = QWidget(self)
        self._overlay.setStyleSheet("background-color: rgba(0, 0, 0, 160);")
        self._overlay.setGeometry(0, 0, self.width(), self.height())
        self._overlay.lower()

        # Camada 3: painel glass central
        self.painel = QFrame(self)
        self.painel.setObjectName("painelGlass")
        self.painel.setStyleSheet("""
            QFrame#painelGlass {
                background-color: rgba(15, 23, 42, 235);
                border: 1px solid rgba(59, 130, 246, 130);
                border-radius: 16px;
            }
            QLabel {
                color: #f8fafc;
                background: transparent;
                border: none;
            }
            QLabel#iconeModal { font-size: 30px; }
            QLabel#tituloModal { font-size: 15px; font-weight: 800; }
            QLabel#textoModal { color: #cbd5e1; font-size: 13px; }
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                min-width: 90px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton#btnSecundario {
                background-color: transparent;
                color: #94a3b8;
                border: 1px solid #334155;
            }
            QPushButton#btnSecundario:hover {
                background-color: #1e293b;
                color: #f8fafc;
            }
        """)

        layout = QVBoxLayout(self.painel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        cabecalho = QHBoxLayout()
        cabecalho.setSpacing(12)
        lbl_icone = QLabel(_ICONES.get(tipo, "ℹ️"))
        lbl_icone.setObjectName("iconeModal")
        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("tituloModal")
        cabecalho.addWidget(lbl_icone)
        cabecalho.addWidget(lbl_titulo, 1)
        layout.addLayout(cabecalho)

        lbl_texto = QLabel(mensagem)
        lbl_texto.setObjectName("textoModal")
        lbl_texto.setWordWrap(True)
        lbl_texto.setMinimumWidth(_LARGURA_MIN)
        lbl_texto.setMaximumWidth(_LARGURA_MAX)
        layout.addWidget(lbl_texto)

        linha_botoes = QHBoxLayout()
        linha_botoes.addStretch()
        for i, (texto, papel) in enumerate(botoes):
            btn = QPushButton(texto)
            if papel == "cancelar" or i > 0:
                btn.setObjectName("btnSecundario")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, p=papel: self._fechar(p))
            linha_botoes.addWidget(btn)
        layout.addLayout(linha_botoes)

        self.painel.adjustSize()
        self._centralizar_painel()
        self.raise_()
        self.painel.raise_()

    def eventFilter(self, origem, evento):
        if origem is self._janela and evento.type() == QEvent.Type.Resize:
            self.setGeometry(self._janela.rect())
            self._centralizar_painel()
        return super().eventFilter(origem, evento)

    def _centralizar_painel(self):
        pw = self.painel.sizeHint().width()
        ph = self.painel.sizeHint().height()
        self.painel.resize(max(pw, _LARGURA_MIN), ph)
        x = (self.width() - self.painel.width()) // 2
        y = (self.height() - self.painel.height()) // 2
        self.painel.move(x, y)

    def showEvent(self, evento):
        super().showEvent(evento)
        self._centralizar_painel()
        self.raise_()
        self.painel.raise_()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if hasattr(self, '_fundo_label') and self._fundo_label is not None:
            self._fundo_label.setGeometry(0, 0, self.width(), self.height())
        if hasattr(self, '_overlay') and self._overlay is not None:
            self._overlay.setGeometry(0, 0, self.width(), self.height())
        if hasattr(self, 'painel') and self.painel is not None:
            self._centralizar_painel()

    def _fechar(self, papel):
        self.resultado = papel
        if self._loop is not None:
            self._loop.quit()

    def exec(self):
        self.show()
        self.raise_()
        self.painel.raise_()
        self._loop = QEventLoop()
        self._loop.exec()
        resultado = self.resultado
        self.deleteLater()
        return resultado


def confirmar(janela, titulo, mensagem):
    """Pergunta Sim/Não. Retorna True se clicar em 'Sim'."""
    d = _ModalGlass(janela, titulo, mensagem, "pergunta", [("Sim", "sim"), ("Não", "cancelar")])
    return d.exec() == "sim"


def informar(janela, titulo, mensagem):
    """Modal de informação. Só 'Ok'."""
    d = _ModalGlass(janela, titulo, mensagem, "info", [("Ok", "ok")])
    d.exec()


def alerta(janela, titulo, mensagem):
    """Modal de aviso. Só 'Ok'."""
    d = _ModalGlass(janela, titulo, mensagem, "alerta", [("Ok", "ok")])
    d.exec()


def erro(janela, titulo, mensagem):
    """Modal de erro. Só 'Ok'."""
    d = _ModalGlass(janela, titulo, mensagem, "erro", [("Ok", "ok")])
    d.exec()


def importacao_pc(janela, mensagem, tipo_icone="info", com_botao_cadastro=True):
    """
    Resultado da importação de PDF de PC.
    Botões: ['Ir para Cadastros', 'Continuar no lançamento'] (se prestador não cadastrado)
    ou ['Ok'] (caso contrário).
    Retorna True se clicou em 'Ir para Cadastros', False caso contrário.
    """
    if com_botao_cadastro:
        d = _ModalGlass(
            janela,
            "Importação de PC",
            mensagem,
            tipo_icone,
            [("Ir para Cadastros", "cadastro"), ("Continuar no lançamento", "ok")],
        )
        return d.exec() == "cadastro"
    informar(janela, "Importação de PC", mensagem)
    return False


def planilha_pronta(janela, caminho_arquivo, total_medicao, proj):
    """
    Sucesso de exportação: mostra Total da medição + botão 'Abrir Pasta'.
    Retorna True se clicou em 'Abrir Pasta', False se clicou em 'Ok'.
    """
    pasta = os.path.dirname(caminho_arquivo)
    d = _ModalGlass(
        janela,
        "Exportação Concluída",
        f"Planilha do projeto '{proj}' salva com sucesso.\n"
        f"Total da medição: R$ {utils.float_para_moeda(total_medicao)}\n"
        f"Arquivo: {os.path.basename(caminho_arquivo)}",
        "sucesso",
        [("📂 Abrir Pasta", "abrir"), ("Ok", "ok")],
    )
    resultado = d.exec()
    if resultado == "abrir":
        try:
            os.startfile(pasta)
        except Exception as e:
            print(f"Não foi possível abrir a pasta: {e}")
    return resultado == "abrir"

