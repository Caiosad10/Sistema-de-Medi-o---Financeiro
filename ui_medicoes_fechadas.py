from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from ui_historico import TelaHistorico
from ui_estatistica import TelaEstatisticas


class TelaMedicoesFechadas(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(16, 16, 16, 16)
        layout_principal.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background: transparent;
                border: none;
                margin-top: 10px;
            }
            QTabBar {
                background: transparent;
                qproperty-drawBase: 0;
            }
            QTabBar::tab {
                background-color: rgba(30, 41, 59, 160);
                color: #94a3b8;
                padding: 10px 22px;
                margin-right: 8px;
                border-radius: 12px;
                font-weight: 700;
                font-size: 12px;
                border: 1px solid rgba(148, 163, 184, 55);
                min-height: 22px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #6366f1);
                color: #ffffff;
                border: 1px solid rgba(147, 197, 253, 180);
            }
            QTabBar::tab:hover:!selected {
                background-color: rgba(51, 65, 85, 200);
                color: #e2e8f0;
                border: 1px solid rgba(148, 163, 184, 90);
            }
        """)

        self.tela_historico = TelaHistorico()
        self.tabs.addTab(self.tela_historico, "Histórico")

        self.tela_estatisticas = TelaEstatisticas()
        self.tabs.addTab(self.tela_estatisticas, "Estatísticas")

        layout_principal.addWidget(self.tabs)

    def recarregar(self):
        """Atualiza histórico e estatísticas ao entrar na tela."""
        try:
            self.tela_historico.carregar_historico()
        except Exception:
            pass
        try:
            self.tela_estatisticas.carregar_dados()
        except Exception:
            pass
