import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFrame, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
import database
from utils import str_para_float
from validators import validar_campo_preenchido, validar_valor_positivo
from ui_icons import icone


# QSS compartilhado (alinhado ao formulário/tabela de Lançamentos)
_QSS_FORM = """
    QFrame#formCadastro {
        background-color: rgba(15, 23, 42, 175);
        border: 1px solid rgba(148, 163, 184, 55);
        border-radius: 16px;
    }
    QFrame#formCadastro QLineEdit,
    QFrame#formCadastro QComboBox {
        background-color: rgba(15, 23, 42, 210);
        color: #f8fafc;
        border: 1px solid rgba(148, 163, 184, 70);
        border-radius: 10px;
        padding: 9px 12px;
        font-size: 13px;
        min-height: 18px;
    }
    QFrame#formCadastro QLineEdit:focus,
    QFrame#formCadastro QComboBox:focus {
        border: 1px solid rgba(96, 165, 250, 200);
        background-color: rgba(15, 23, 42, 240);
    }
    QFrame#formCadastro QComboBox::drop-down { border: none; width: 24px; }
    QFrame#formCadastro QComboBox QAbstractItemView {
        background-color: #0f172a;
        color: #f8fafc;
        selection-background-color: #6366f1;
        border: 1px solid #334155;
    }
    QFrame#formCadastro QPushButton {
        background-color: #6366f1;
        color: white;
        font-weight: 800;
        border-radius: 10px;
        padding: 10px 16px;
        border: 1px solid rgba(199, 210, 254, 60);
    }
    QFrame#formCadastro QPushButton:hover { background-color: #4f46e5; }
    QFrame#formCadastro QPushButton#btn_limpar {
        background-color: rgba(71, 85, 105, 200);
        border: 1px solid rgba(148, 163, 184, 70);
    }
    QFrame#formCadastro QPushButton#btn_limpar:hover {
        background-color: rgba(100, 116, 139, 220);
    }
"""

_QSS_TABELA = """
    QTableWidget {
        background-color: rgba(15, 23, 42, 145);
        color: #e2e8f0;
        border: 1px solid rgba(148, 163, 184, 45);
        border-radius: 16px;
        gridline-color: transparent;
        selection-background-color: rgba(99, 102, 241, 160);
        selection-color: #ffffff;
        outline: none;
    }
    QTableWidget::item {
        padding: 8px 12px;
        border-bottom: 1px solid rgba(148, 163, 184, 22);
    }
    QTableWidget::item:hover {
        background-color: rgba(51, 65, 85, 120);
        color: #f8fafc;
    }
    QTableWidget::item:selected {
        background-color: rgba(99, 102, 241, 180);
        color: #ffffff;
    }
    QHeaderView::section {
        background-color: rgba(15, 23, 42, 200);
        color: #94a3b8;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.4px;
        padding: 12px 10px;
        border: none;
        border-bottom: 1px solid rgba(148, 163, 184, 50);
    }
"""

_QSS_BUSCA = """
    QLineEdit {
        background-color: rgba(15, 23, 42, 150);
        color: #e2e8f0;
        border: 1px solid rgba(148, 163, 184, 55);
        border-radius: 14px;
        padding: 10px 16px;
        font-size: 12px;
    }
    QLineEdit:focus {
        border: 1px solid rgba(96, 165, 250, 200);
        background-color: rgba(15, 23, 42, 210);
    }
"""


class TelaCadastro(QWidget):
    def __init__(self):
        super().__init__()
        self.fornecedor_em_edicao_cnpj = None
        self._anim_formulario = None
        self.init_ui()
        self._registrar_atalhos()
        self.carregar_dados_tabela()

    def init_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)

        # --- BARRA DE AÇÕES ---
        layout_acoes = QHBoxLayout()
        self.btn_novo = QPushButton("Novo Prestador")
        self.btn_novo.setIcon(icone("mais", "#ffffff", 16))
        self.btn_novo.setIconSize(self.btn_novo.iconSize())
        self.btn_novo.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34d399, stop:1 #059669);
                color: #ffffff;
                font-weight: 800;
                font-size: 12px;
                border: 1px solid rgba(167, 243, 208, 80);
                border-radius: 12px;
                padding: 10px 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #047857);
            }
        """)
        self.btn_novo.clicked.connect(self.abrir_formulario_novo)

        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("Buscar por razão social, fantasia, CNPJ/CPF, banco...")
        self.txt_busca.setStyleSheet(_QSS_BUSCA)
        self.txt_busca.textChanged.connect(self.filtrar_tabela)

        layout_acoes.addWidget(self.btn_novo)
        layout_acoes.addStretch()
        layout_acoes.addWidget(self.txt_busca)
        layout_principal.addLayout(layout_acoes)

        # --- FORMULÁRIO (recolhido por padrão, animado) ---
        self.frame_formulario = QFrame()
        self.frame_formulario.setObjectName("formCadastro")
        self.frame_formulario.setVisible(False)
        self.frame_formulario.setMaximumHeight(0)
        self.frame_formulario.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.frame_formulario.setStyleSheet(_QSS_FORM)

        layout_grid = QGridLayout(self.frame_formulario)
        layout_grid.setContentsMargins(18, 16, 18, 16)
        layout_grid.setSpacing(12)

        self.txt_razao = QLineEdit()
        self.txt_razao.setPlaceholderText("Razão Social *")
        self.txt_fantasia = QLineEdit()
        self.txt_fantasia.setPlaceholderText("Razão Fantasia")
        self.txt_cnpj = QLineEdit()
        self.txt_cnpj.setPlaceholderText("CNPJ / CPF *")

        self.txt_banco = QLineEdit()
        self.txt_banco.setPlaceholderText("Banco")
        self.txt_agencia = QLineEdit()
        self.txt_agencia.setPlaceholderText("Agência")
        self.txt_conta = QLineEdit()
        self.txt_conta.setPlaceholderText("Conta")

        self.combo_tipo_pix = QComboBox()
        self.combo_tipo_pix.addItems(["CNPJ", "CPF", "E-MAIL", "Nº TELEFONE", "ALEATÓRIA"])
        self.txt_chave_pix = QLineEdit()
        self.txt_chave_pix.setPlaceholderText("Chave PIX")

        layout_grid.addWidget(self.txt_razao, 0, 0, 1, 2)
        layout_grid.addWidget(self.txt_fantasia, 0, 2)
        layout_grid.addWidget(self.txt_cnpj, 0, 3)

        layout_grid.addWidget(self.txt_banco, 1, 0)
        layout_grid.addWidget(self.txt_agencia, 1, 1)
        layout_grid.addWidget(self.txt_conta, 1, 2)
        layout_grid.addWidget(self.combo_tipo_pix, 1, 3)
        layout_grid.addWidget(self.txt_chave_pix, 1, 4)

        layout_botoes = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar Cadastro")
        self.btn_salvar.clicked.connect(self.salvar_registro)

        self.btn_limpar = QPushButton("Cancelar")
        self.btn_limpar.setObjectName("btn_limpar")
        self.btn_limpar.clicked.connect(self.fechar_formulario)

        layout_botoes.addStretch()
        layout_botoes.addWidget(self.btn_limpar)
        layout_botoes.addWidget(self.btn_salvar)
        layout_grid.addLayout(layout_botoes, 2, 0, 1, 5)

        layout_principal.addWidget(self.frame_formulario)

        # --- TABELA ---
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(8)
        self.tabela.setHorizontalHeaderLabels([
            "Razão Social", "Razão Fantasia", "CNPJ/CPF", "Banco",
            "Agência", "Conta", "Tipo PIX", "Chave PIX",
        ])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setShowGrid(False)
        self.tabela.setAlternatingRowColors(False)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.verticalHeader().setDefaultSectionSize(42)
        self.tabela.doubleClicked.connect(self.ao_clicar_duplo)
        self.tabela.setStyleSheet(_QSS_TABELA)

        layout_principal.addWidget(self.tabela)

    # ---------- animação (mesmo padrão de Lançamentos) ----------
    def _parar_anim_formulario(self):
        if self._anim_formulario is not None:
            self._anim_formulario.stop()
            self._anim_formulario = None

    def _mostrar_formulario_animado(self):
        frame = self.frame_formulario
        if frame.isVisible() and frame.maximumHeight() > 40:
            frame.setMaximumHeight(16777215)
            return
        self._parar_anim_formulario()
        frame.setVisible(True)
        frame.setMaximumHeight(0)
        frame.updateGeometry()
        QApplication.processEvents()
        alvo = max(frame.sizeHint().height(), frame.minimumSizeHint().height(), 160)
        anim = QPropertyAnimation(frame, b"maximumHeight", self)
        anim.setDuration(280)
        anim.setStartValue(0)
        anim.setEndValue(alvo)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _liberar():
            frame.setMaximumHeight(16777215)
            self._anim_formulario = None

        anim.finished.connect(_liberar)
        self._anim_formulario = anim
        anim.start()

    def _ocultar_formulario_animado(self):
        frame = self.frame_formulario
        if not frame.isVisible():
            return
        self._parar_anim_formulario()
        altura = frame.height() if frame.height() > 0 else frame.sizeHint().height()
        frame.setMaximumHeight(altura)
        anim = QPropertyAnimation(frame, b"maximumHeight", self)
        anim.setDuration(220)
        anim.setStartValue(altura)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)

        def _esconder():
            frame.setVisible(False)
            frame.setMaximumHeight(0)
            self._anim_formulario = None

        anim.finished.connect(_esconder)
        self._anim_formulario = anim
        anim.start()

    def abrir_formulario_novo(self):
        self.limpar_campos(fechar=False)
        self.btn_salvar.setText("Salvar Cadastro")
        self._mostrar_formulario_animado()
        self.txt_razao.setFocus()

    def fechar_formulario(self):
        self.limpar_campos(fechar=False)
        self._ocultar_formulario_animado()


    def _registrar_atalhos(self):
        def _at(seq, slot):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(slot)
            return sc
        _at("Esc", self._atalho_esc)
        _at("Ctrl+N", self.abrir_formulario_novo)
        _at("Ctrl+Return", self._atalho_salvar)
        _at("Ctrl+Enter", self._atalho_salvar)

    def _atalho_esc(self):
        if self.frame_formulario.isVisible() and self.frame_formulario.maximumHeight() > 0:
            self.fechar_formulario()

    def _atalho_salvar(self):
        if self.frame_formulario.isVisible() and self.frame_formulario.maximumHeight() > 0:
            self.salvar_registro()

    def exibir_alerta(self, titulo: str, mensagem: str):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(titulo)
        msg.setText(mensagem)
        msg.setStyleSheet("""
            QMessageBox { background-color: #1e293b; color: #f8fafc; }
            QLabel { color: #f8fafc; }
            QPushButton {
                background-color: #6d5dd3; color: white; border-radius: 4px;
                padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #5b4bc4; }
        """)
        msg.exec()

    def carregar_dados_tabela(self):
        fornecedores = database.carregar_fornecedores()
        self.tabela.setRowCount(0)
        for row_idx, f in enumerate(fornecedores):
            self.tabela.insertRow(row_idx)
            valores = list(f.values())[:8]
            for col_idx, valor in enumerate(valores):
                val_str = str(valor) if valor not in [None, "nan"] else ""
                self.tabela.setItem(row_idx, col_idx, QTableWidgetItem(val_str))
        self.filtrar_tabela()

    def filtrar_tabela(self):
        termo = self.txt_busca.text().lower().strip()
        for row in range(self.tabela.rowCount()):
            if not termo:
                self.tabela.setRowHidden(row, False)
                continue
            match = False
            for col in range(self.tabela.columnCount()):
                item = self.tabela.item(row, col)
                if item and termo in item.text().lower():
                    match = True
                    break
            self.tabela.setRowHidden(row, not match)

    def ao_clicar_duplo(self):
        row = self.tabela.currentRow()
        if row < 0:
            return
        self.txt_razao.setText(self.tabela.item(row, 0).text())
        self.txt_fantasia.setText(self.tabela.item(row, 1).text())
        self.txt_cnpj.setText(self.tabela.item(row, 2).text())
        self.txt_banco.setText(self.tabela.item(row, 3).text())
        self.txt_agencia.setText(self.tabela.item(row, 4).text())
        self.txt_conta.setText(self.tabela.item(row, 5).text())
        tipo_pix = self.tabela.item(row, 6).text()
        if tipo_pix:
            self.combo_tipo_pix.setCurrentText(tipo_pix)
        self.txt_chave_pix.setText(self.tabela.item(row, 7).text())
        self.fornecedor_em_edicao_cnpj = self.tabela.item(row, 2).text()
        self.btn_salvar.setText("Atualizar Cadastro")
        self._mostrar_formulario_animado()

    def salvar_registro(self):
        razao = self.txt_razao.text().strip()
        cnpj = self.txt_cnpj.text().strip()

        if not razao:
            self.exibir_alerta("Campo Obrigatório", "O campo 'Razão Social' é obrigatório!")
            self.txt_razao.setFocus()
            return
        if not cnpj:
            self.exibir_alerta("Campo Obrigatório", "O campo 'CNPJ / CPF' é obrigatório!")
            self.txt_cnpj.setFocus()
            return

        dados = [
            razao,
            self.txt_fantasia.text().strip(),
            cnpj,
            self.txt_banco.text().strip(),
            self.txt_agencia.text().strip(),
            self.txt_conta.text().strip(),
            self.combo_tipo_pix.currentText(),
            self.txt_chave_pix.text().strip(),
        ]

        if self.fornecedor_em_edicao_cnpj:
            sucesso, erro = database.atualizar_fornecedor(self.fornecedor_em_edicao_cnpj, dados)
            msg = "Fornecedor atualizado com sucesso!"
        else:
            sucesso, erro = database.adicionar_fornecedor(dados)
            msg = "Novo fornecedor cadastrado!"

        if sucesso:
            QMessageBox.information(self, "Sucesso", msg)
            self.fechar_formulario()
            self.carregar_dados_tabela()
        else:
            QMessageBox.critical(
                self,
                "Erro ao salvar",
                erro or "Houve um problema ao salvar os dados no sistema.",
            )

    def limpar_campos(self, fechar=True):
        self.txt_razao.clear()
        self.txt_fantasia.clear()
        self.txt_cnpj.clear()
        self.txt_banco.clear()
        self.txt_agencia.clear()
        self.txt_conta.clear()
        self.txt_chave_pix.clear()
        self.combo_tipo_pix.setCurrentIndex(0)
        self.fornecedor_em_edicao_cnpj = None
        self.btn_salvar.setText("Salvar Cadastro")
        if fechar:
            self._ocultar_formulario_animado()
