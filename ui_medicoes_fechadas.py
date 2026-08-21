from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QFrame
from ui_historico import TelaHistorico
from ui_estatistica import TelaEstatisticas

class TelaMedicoesFechadas(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        
        # Cria as abas
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #020617;
                border: none;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #334155;
                color: #f8fafc;
            }
        """)
        
        # Aba 1: Histórico
        self.tabs.addTab(TelaHistorico(), "📋 Histórico")
        
        # Aba 2: Estatísticas
        self.tabs.addTab(TelaEstatisticas(), "📊 Estatísticas")
        
        layout_principal.addWidget(self.tabs)