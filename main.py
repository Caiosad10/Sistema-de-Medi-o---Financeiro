import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedWidget, QLabel, QFrame
)
from PySide6.QtCore import Qt
import database  # Importando o arquivo que construímos!
# Importando as telas que já construímos
from ui_cadastro import TelaCadastro
from ui_lancamentos import TelaLancamentos
from ui_medicoes_fechadas import TelaMedicoesFechadas

class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gerenciamento de Medições e Pagamentos - 2026")
        self.resize(1280, 720)

        # ===== CORREÇÃO CRÍTICA: Inicializa o banco de dados =====
        database.inicializar_banco()

        # Container Principal (Layout Horizontal: Sidebar + Conteúdo)
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # --- BARRA LATERAL DE NAVEGAÇÃO (SIDEBAR - BENTO UI) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-right: 1px solid #1e293b;
            }
            QLabel {
                color: #f8fafc;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                text-align: left;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 600;
                border: none;
                border-radius: 8px;
                margin: 4px 10px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #f8fafc;
            }
            QPushButton:checked {
                background-color: #3b82f6;
                color: #ffffff;
            }
        """)

        layout_sidebar = QVBoxLayout(sidebar)
        layout_sidebar.setContentsMargins(10, 20, 10, 20)

        # Título da Sidebar
        lbl_titulo = QLabel("MEDIÇÃO - CITRA")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        layout_sidebar.addWidget(lbl_titulo)

        # Divisor
        divisor = QFrame()
        divisor.setFrameShape(QFrame.HLine)
        divisor.setStyleSheet("background-color: #1e293b; margin-bottom: 15px;")
        layout_sidebar.addWidget(divisor)

        # Botões do Menu (ordem = frequência de uso)
        self.btn_lancamentos = QPushButton("📊 Lançamentos")
        self.btn_lancamentos.setCheckable(True)
        self.btn_lancamentos.setChecked(True)
        self.btn_lancamentos.clicked.connect(lambda: self.mudar_tela(0))

        self.btn_cadastro = QPushButton("📋 Cadastros")
        self.btn_cadastro.setCheckable(True)
        self.btn_cadastro.clicked.connect(lambda: self.mudar_tela(1))

        self.btn_medicoes = QPushButton("📈 Medições Fechadas")
        self.btn_medicoes.setCheckable(True)
        self.btn_medicoes.clicked.connect(lambda: self.mudar_tela(2))

        layout_sidebar.addWidget(self.btn_lancamentos)
        layout_sidebar.addWidget(self.btn_cadastro)
        layout_sidebar.addWidget(self.btn_medicoes)
        layout_sidebar.addStretch()

        # --- ÁREA CENTRAL DE CONTEÚDO (STACKED WIDGET) ---
        self.paginas = QStackedWidget()
        self.paginas.setStyleSheet("background-color: #020617;")

        self.tela_lancamentos = TelaLancamentos()
        self.tela_cadastro = TelaCadastro()
        self.tela_medicoes_fechadas = TelaMedicoesFechadas()

        # Stack alinhado ao menu (Lançamentos = tela inicial)
        self.paginas.addWidget(self.tela_lancamentos)        # Índice 0
        self.paginas.addWidget(self.tela_cadastro)          # Índice 1
        self.paginas.addWidget(self.tela_medicoes_fechadas)   # Índice 2

        self.setStyleSheet("""
            QMessageBox {
                background-color: #0f172a;
            }
            QMessageBox QLabel {
                color: #f8fafc;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2563eb;
            }
        """)

        # Adicionando Sidebar e Conteúdo ao Layout Principal
        layout_principal.addWidget(sidebar)
        layout_principal.addWidget(self.paginas)

    def mudar_tela(self, indice):
        self.paginas.setCurrentIndex(indice)
        self.btn_lancamentos.setChecked(indice == 0)
        self.btn_cadastro.setChecked(indice == 1)
        self.btn_medicoes.setChecked(indice == 2)

        if indice == 0:
            self.tela_lancamentos.carregar_fornecedores_combo()
            self.tela_lancamentos.carregar_dados_tabela()
        elif indice == 1:
            self.tela_cadastro.carregar_dados_tabela()
        elif indice == 2:
            self.tela_medicoes_fechadas.recarregar()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # <-- TRAVA O RENDERIZADOR NATIVO PARA EVITAR BUGS DE TEMA DO WINDOWS
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec())