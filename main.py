import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from ui_icons import icone
import database
import paths
from versao import VERSAO
from ui_cadastro import TelaCadastro
from ui_lancamentos import TelaLancamentos
from ui_medicoes_fechadas import TelaMedicoesFechadas


class FundoAurora(QWidget):
    """Fundo navy/roxo com ondas suaves (paleta Citra - estilo mockup)."""

    def paintEvent(self, _evento):
        from PySide6.QtGui import QPainter, QLinearGradient, QPainterPath, QColor
        p = QPainter(self)
        w, h = self.width(), self.height()

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor("#0b0b2b"))
        grad.setColorAt(0.5, QColor("#151038"))
        grad.setColorAt(1.0, QColor("#0b0b2b"))
        p.fillRect(self.rect(), grad)

        for opac, y_base, ampl in ((36, 0.72, 90), (24, 0.86, 70), (18, 0.60, 110)):
            path = QPainterPath()
            path.moveTo(0, h * y_base)
            path.cubicTo(
                w * 0.3, h * y_base - ampl,
                w * 0.65, h * y_base + ampl * 0.7,
                w, h * y_base - ampl * 0.4,
            )
            path.lineTo(w, h)
            path.lineTo(0, h)
            path.closeSubpath()
            p.fillPath(path, QColor(109, 93, 211, opac))

        grad_topo = QLinearGradient(0, 0, 0, h * 0.35)
        grad_topo.setColorAt(0, QColor(139, 124, 240, 26))
        grad_topo.setColorAt(1, QColor(139, 124, 240, 0))
        p.fillRect(0, 0, w, int(h * 0.35), grad_topo)
        p.end()


class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Sistema de Gerenciamento de Medições e Pagamentos - v{VERSAO}")
        self.setWindowIcon(QIcon(paths.get_resource_path("sismed_icon.png")))
        self.resize(1280, 720)

        database.inicializar_banco()

        widget_central = QWidget()
        self.setCentralWidget(widget_central)

        self._aurora = FundoAurora(widget_central)
        self._aurora.setGeometry(widget_central.rect())
        self._aurora.lower()

        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # --- RAIL LATERAL (só atalhos; sem menu flutuante) ---
        # luz(3) + gap(6) + botão(40) + margens ≈ 68
        LARGURA_RAIL = 72
        rail = QFrame()
        rail.setObjectName("railGlass")
        rail.setFixedWidth(LARGURA_RAIL)
        rail.setStyleSheet("""
            QFrame#railGlass {
                background-color: rgba(12, 18, 40, 165);
                border-right: 1px solid rgba(148, 163, 184, 55);
            }
        """)
        layout_rail = QVBoxLayout(rail)
        layout_rail.setContentsMargins(8, 20, 10, 14)
        layout_rail.setSpacing(12)

        self._rail_mapa = []  # [(botao, chave, luz)]

        def _btn_rail(nome, tooltip, chamada, chave):
            wrap = QWidget()
            wrap.setFixedHeight(44)
            row = QHBoxLayout(wrap)
            row.setContentsMargins(0, 2, 0, 2)
            row.setSpacing(6)

            # Luz fora do quadrado (no próprio rail)
            luz = QFrame()
            luz.setFixedSize(3, 28)
            luz.setStyleSheet("background: transparent; border: none; border-radius: 2px;")
            row.addWidget(luz, 0, Qt.AlignVCenter)

            b = QPushButton()
            b.setFixedSize(40, 40)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(tooltip)
            b.setIcon(icone(nome, "#94a3b8", 22, cor_ativo="#ffffff"))
            b.setIconSize(QSize(22, 22))
            b.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 28);
                }
                QPushButton:checked {
                    background-color: rgba(109, 93, 211, 220);
                }
            """)
            b.clicked.connect(chamada)
            row.addWidget(b, 0, Qt.AlignVCenter)
            layout_rail.addWidget(wrap)
            self._rail_mapa.append((b, chave, luz))
            return b

        _btn_rail("lista", "Lançamentos", lambda: self.mudar_tela(0), (0, None))
        _btn_rail("pessoa", "Cadastros", lambda: self.mudar_tela(1), (1, None))
        _btn_rail("documento", "Medições Fechadas", lambda: self.mudar_tela(2, 0), (2, 0))
        _btn_rail("grafico", "Estatísticas", lambda: self.mudar_tela(2, 1), (2, 1))
        layout_rail.addStretch()

        # --- ÁREA CENTRAL ---
        self.paginas = QStackedWidget()
        self.paginas.setStyleSheet("background-color: transparent;")

        self.tela_lancamentos = TelaLancamentos()
        self.tela_cadastro = TelaCadastro()
        self.tela_medicoes_fechadas = TelaMedicoesFechadas()

        self.paginas.addWidget(self.tela_lancamentos)         # 0
        self.paginas.addWidget(self.tela_cadastro)           # 1
        self.paginas.addWidget(self.tela_medicoes_fechadas)  # 2

        self.tela_medicoes_fechadas.tabs.currentChanged.connect(self._aba_medicoes_trocou)

        self.setStyleSheet("""
            QMessageBox {
                background-color: #0f172a;
            }
            QMessageBox QLabel {
                color: #f8fafc;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background-color: #6d5dd3;
                color: white;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #5b4bc4;
            }
        """)

        layout_principal.addWidget(rail)
        layout_principal.addWidget(self.paginas)

        self._atualizar_rail()

    def _atualizar_rail(self):
        """Destaca no rail o botão ativo e acende a luz fora do quadrado."""
        idx = self.paginas.currentIndex()
        if idx == 2:
            chave = (2, self.tela_medicoes_fechadas.tabs.currentIndex())
        else:
            chave = (idx, None)
        for b, c, luz in self._rail_mapa:
            ativo = c == chave
            b.setChecked(ativo)
            if ativo:
                luz.setStyleSheet(
                    "background-color: #c4b5fd; border: none; border-radius: 2px;"
                )
            else:
                luz.setStyleSheet(
                    "background: transparent; border: none; border-radius: 2px;"
                )

    def _aba_medicoes_trocou(self, _idx):
        if self.paginas.currentIndex() == 2:
            self._atualizar_rail()

    def mudar_tela(self, indice, aba_medicoes=None):
        self.paginas.setCurrentIndex(indice)
        if indice == 2 and aba_medicoes is not None:
            self.tela_medicoes_fechadas.tabs.setCurrentIndex(aba_medicoes)
        self._atualizar_rail()

        if indice == 0:
            self.tela_lancamentos.carregar_fornecedores_combo()
            self.tela_lancamentos.carregar_dados_tabela()
        elif indice == 1:
            self.tela_cadastro.carregar_dados_tabela()
        elif indice == 2:
            self.tela_medicoes_fechadas.recarregar()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if getattr(self, "_aurora", None) is not None:
            self._aurora.setGeometry(self.centralWidget().rect())
            self._aurora.lower()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec())
