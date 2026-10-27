import sys
from PySide6.QtWidgets import (
    QRadioButton, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QFrame, QFileDialog, QApplication, QCompleter,
    QTabBar, QDialog, QDialogButtonBox, QSizePolicy, QMenu, QInputDialog,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QIcon, QKeySequence, QShortcut
import database
import utils
from utils import str_para_float
from ui_modal import confirmar, informar, alerta, erro, planilha_pronta, importacao_pc
from pc_pdf_reader import importar_pc_medicao, match_prestador_cadastrado
from ui_icons import pixmap_icone, icone

class TelaLancamentos(QWidget):
    def __init__(self):
        super().__init__()
        self.pc_em_edicao = None
        self.dados_carregados = []
        self.ciclo_id_ativo = None
        self._ciclos_cache = []
        self._bloqueando_abas = False
        self._filtro_status = None  # None = sem filtro; "MOBILIZA"/"ADIANT"/"CONCLU"
        self._card_frames = {}  # {"MOBILIZA": wrapper, "ADIANT": wrapper, "CONCLU": wrapper}
        self._card_original_style = {}  # {"MOBILIZA": stylesheet, ...}
        self._animacao_glow = None
        self._glow_frame_idx = 0
        self.init_ui()
        self._registrar_atalhos()
        self.carregar_projetos_combo()
        self.carregar_fornecedores_combo()
        self.carregar_dados_tabela()

    def init_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)

        # --- 0. SELETOR DE PROJETO E BARRA DE STATUS (BENTO UI ELEGANTE) ---
        layout_topo_projeto = QHBoxLayout()
        
        lbl_icone = QLabel("📂 Projeto Ativo:")
        lbl_icone.setStyleSheet("color: #f8fafc; font-weight: bold; font-size: 14px;")
        
        self.combo_projeto = QComboBox()
        self.combo_projeto.setStyleSheet("""
            QComboBox {
                background-color: rgba(30, 64, 175, 190);
                color: #ffffff;
                font-weight: 800;
                font-size: 13px;
                letter-spacing: 0.3px;
                border: 1px solid rgba(96, 165, 250, 220);
                border-radius: 14px;
                padding: 8px 18px;
                min-width: 200px;
                min-height: 22px;
            }
            QComboBox:hover {
                background-color: rgba(37, 99, 235, 220);
                border: 1px solid rgba(147, 197, 253, 255);
            }
            QComboBox::drop-down { border: none; width: 28px; }
            QComboBox::down-arrow { image: none; border: none; width: 0; height: 0; }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #f8fafc;
                selection-background-color: #3b82f6;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        glow_combo = QGraphicsDropShadowEffect(self.combo_projeto)
        glow_combo.setBlurRadius(22)
        glow_combo.setOffset(0, 0)
        glow_combo.setColor(QColor(59, 130, 246, 160))
        self.combo_projeto.setGraphicsEffect(glow_combo)
        self.combo_projeto.currentIndexChanged.connect(self.mudar_projeto_ativo)

        layout_topo_projeto.addWidget(lbl_icone)
        layout_topo_projeto.addWidget(self.combo_projeto)

        # Contador de lançamentos do ciclo (texto sutil; sempre o ciclo inteiro, ignora a busca)
        self.lbl_contador = QLabel("")
        self.lbl_contador.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 12px; padding-left: 12px;")
        layout_topo_projeto.addWidget(self.lbl_contador)

        layout_topo_projeto.addStretch()

        # Total da medição (caixa no canto direito, mesmo estilo visual do dropdown)
        self.lbl_total_medicao = QLabel()
        self.lbl_total_medicao.setTextFormat(Qt.RichText)
        self.lbl_total_medicao.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 58, 138, 175);
                border: 1px solid rgba(96, 165, 250, 160);
                border-radius: 14px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
                min-height: 22px;
            }
        """)
        glow_total = QGraphicsDropShadowEffect(self.lbl_total_medicao)
        glow_total.setBlurRadius(18)
        glow_total.setOffset(0, 0)
        glow_total.setColor(QColor(59, 130, 246, 120))
        self.lbl_total_medicao.setGraphicsEffect(glow_total)
        layout_topo_projeto.addWidget(self.lbl_total_medicao)

        layout_principal.addLayout(layout_topo_projeto)

        # --- 0.1 BARRA DE ABAS (ciclos de medição) ---
        layout_abas = QHBoxLayout()
        layout_abas.setContentsMargins(0, 2, 0, 4)
        layout_abas.setSpacing(8)

        self.tab_ciclos = QTabBar()
        self.tab_ciclos.setExpanding(False)
        self.tab_ciclos.setDrawBase(False)
        self.tab_ciclos.setMovable(False)
        self.tab_ciclos.setTabsClosable(False)
        self.tab_ciclos.setStyleSheet("""
            QTabBar {
                background: transparent;
            }
            QTabBar::tab {
                background-color: rgba(30, 41, 59, 160);
                color: #94a3b8;
                padding: 8px 20px;
                margin-right: 8px;
                margin-top: 2px;
                margin-bottom: 2px;
                border-radius: 12px;
                font-weight: 700;
                font-size: 12px;
                border: 1px solid rgba(148, 163, 184, 55);
                min-height: 20px;
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
        self.tab_ciclos.currentChanged.connect(self.on_aba_alterada)
        self.tab_ciclos.tabBarDoubleClicked.connect(self.on_aba_duplo_clique)
        self.tab_ciclos.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_ciclos.customContextMenuRequested.connect(self.on_aba_menu_contexto)

        self.btn_nova_aba = QPushButton("+")
        self.btn_nova_aba.setFixedSize(36, 36)
        self.btn_nova_aba.setToolTip("Nova aba de medição")
        self.btn_nova_aba.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 170);
                color: #93c5fd;
                font-weight: 800;
                font-size: 18px;
                border: 1px solid rgba(96, 165, 250, 120);
                border-radius: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #6366f1);
                color: #ffffff;
                border: 1px solid rgba(147, 197, 253, 200);
            }
        """)
        self.btn_nova_aba.clicked.connect(self.criar_nova_aba)

        layout_abas.addWidget(self.tab_ciclos)
        layout_abas.addWidget(self.btn_nova_aba)
        layout_abas.addStretch()
        layout_principal.addLayout(layout_abas)

        # --- 1. DASHBOARD DE STATUS (GRADIENTES BENTO UI) ---
        layout_cards = QHBoxLayout()
        # Cores alinhadas às pílulas da tabela (mesma leitura visual / daltonismo)
        # MOBILIZ. = teal | ADIANT. = âmbar | CONCL. = roxo
        self.lbl_card_mobilizacao = self.criar_card(
            "Status: Mobilização", "R$ 0,00",
            "rgba(20, 184, 166, 185)", "rgba(15, 118, 110, 155)",
            "rgba(45, 212, 191, 140)", "capacete",
        )
        self.lbl_card_adiantamento = self.criar_card(
            "Status: Adiantamento", "R$ 0,00",
            "rgba(245, 158, 11, 185)", "rgba(180, 83, 9, 155)",
            "rgba(251, 191, 36, 140)", "moeda",
        )
        self.lbl_card_conclusao = self.criar_card(
            "Status: Conclusão", "R$ 0,00",
            "rgba(139, 92, 246, 185)", "rgba(91, 33, 182, 155)",
            "rgba(196, 181, 253, 140)", "check",
        )

        # Guarda os frames e torna clicáveis
        frame_mob = self.lbl_card_mobilizacao.parentWidget()
        frame_adi = self.lbl_card_adiantamento.parentWidget()
        frame_con = self.lbl_card_conclusao.parentWidget()

        self._card_original_style = {
            "MOBILIZA": frame_mob.styleSheet(),
            "ADIANT": frame_adi.styleSheet(),
            "CONCLU": frame_con.styleSheet(),
        }

        wrapper_mob = self._criar_glow_wrapper(frame_mob)
        wrapper_adi = self._criar_glow_wrapper(frame_adi)
        wrapper_con = self._criar_glow_wrapper(frame_con)

        self._card_frames = {"MOBILIZA": wrapper_mob, "ADIANT": wrapper_adi, "CONCLU": wrapper_con}

        for chave, wrapper in self._card_frames.items():
            wrapper.setCursor(Qt.CursorShape.PointingHandCursor)
            wrapper.setToolTip("Clique para filtrar por este status")
            wrapper.mousePressEvent = lambda e, c=chave: self.toggle_filtro_card(c)

        layout_cards.addWidget(wrapper_mob)
        layout_cards.addWidget(wrapper_adi)
        layout_cards.addWidget(wrapper_con)

        layout_principal.addLayout(layout_cards)

        # --- 2. BARRA DE AÇÕES (Botões e Campo de Busca) ---
        layout_acoes = QHBoxLayout()
        
        self.btn_novo = QPushButton("Novo Lançamento")
        self.btn_novo.setIcon(icone("mais", "#ffffff", 16))
        self.btn_novo.setIconSize(QSize(16, 16))
        self.btn_novo.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34d399, stop:1 #10b981);
                color: #ffffff;
                font-weight: 800;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 12px;
                padding: 10px 18px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669); }
            QPushButton:pressed { background-color: #047857; }
        """)
        self.btn_novo.clicked.connect(self.abrir_formulario_novo)
        
        self.btn_exportar = QPushButton("Exportar Financeiro")
        self.btn_exportar.setIcon(icone("download", "#ffffff", 16))
        self.btn_exportar.setIconSize(QSize(16, 16))
        self.btn_exportar.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a78bfa, stop:1 #6d5dd3);
                color: #ffffff;
                font-weight: 800;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 12px;
                padding: 10px 18px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6d5dd3, stop:1 #4f3fb0); }
            QPushButton:pressed { background-color: #3f3196; }
        """)
        self.btn_exportar.clicked.connect(self.exportar_excel)

        self.btn_fechar_medicao = QPushButton("Fechar Medição")
        self.btn_fechar_medicao.setIcon(icone("cadeado", "#ffffff", 16))
        self.btn_fechar_medicao.setIconSize(QSize(16, 16))
        self.btn_fechar_medicao.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a78bfa, stop:1 #8b5cf6);
                color: #ffffff;
                font-weight: 800;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 12px;
                padding: 10px 18px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8b5cf6, stop:1 #7c3aed); }
            QPushButton:pressed { background-color: #6d28d9; }
        """)
        self.btn_fechar_medicao.clicked.connect(self.fechar_medicao)

        self.btn_limpar_projeto = QPushButton("Recomeçar Medição")
        self.btn_limpar_projeto.setIcon(icone("reiniciar", "#ffffff", 16))
        self.btn_limpar_projeto.setIconSize(QSize(16, 16))
        self.btn_limpar_projeto.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0626e, stop:1 #e53946);
                color: #ffffff;
                font-weight: 800;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 45);
                border-radius: 12px;
                padding: 10px 18px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e53946, stop:1 #c7303b); }
            QPushButton:pressed { background-color: #b02834; }
        """)
        self.btn_limpar_projeto.clicked.connect(self.limpar_medicao_projeto)

        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("🔍 Buscar por PC, Prestador, Atividade, Status, NF...")
        self.txt_busca.setStyleSheet("""
            QLineEdit {
                background-color: rgba(15, 23, 42, 150);
                color: #e2e8f0;
                border: 1px solid rgba(148, 163, 184, 55);
                border-radius: 14px;
                padding: 10px 16px;
                font-size: 12px;
                min-width: 260px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(96, 165, 250, 200);
                background-color: rgba(15, 23, 42, 210);
            }
            QLineEdit::placeholder {
                color: #64748b;
            }
        """)

        self.txt_busca.textChanged.connect(self.filtrar_tabela)

        # Botão "Remover filtro" (mesmo estilo do dropdown/total)
        self.btn_remover_filtro = QPushButton("✕ Remover filtro")
        self.btn_remover_filtro.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #a78bfa;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #6d5dd3;
                border-radius: 8px;
                padding: 6px 15px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        self.btn_remover_filtro.setVisible(False)
        self.btn_remover_filtro.clicked.connect(self.remover_filtro)

        layout_acoes.addWidget(self.btn_novo)
        layout_acoes.addWidget(self.btn_exportar)
        layout_acoes.addWidget(self.btn_fechar_medicao)
        layout_acoes.addWidget(self.btn_limpar_projeto)
        layout_acoes.addStretch()
        layout_acoes.addWidget(self.btn_remover_filtro)
        layout_acoes.addWidget(self.txt_busca)
        
        layout_principal.addLayout(layout_acoes)

        # --- 3. FORMULÁRIO (glass + animação expandir/recolher) ---
        self.frame_formulario = QFrame()
        self.frame_formulario.setObjectName("formLancamento")
        self.frame_formulario.setVisible(False)
        self.frame_formulario.setMaximumHeight(0)
        self.frame_formulario.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.frame_formulario.setStyleSheet("""
            QFrame#formLancamento {
                background-color: rgba(15, 23, 42, 175);
                border: 1px solid rgba(148, 163, 184, 55);
                border-radius: 16px;
            }
            QFrame#formLancamento QLineEdit,
            QFrame#formLancamento QComboBox {
                background-color: rgba(15, 23, 42, 210);
                color: #f8fafc;
                border: 1px solid rgba(148, 163, 184, 70);
                border-radius: 10px;
                padding: 9px 12px;
                font-size: 13px;
                min-height: 18px;
            }
            QFrame#formLancamento QLineEdit:focus,
            QFrame#formLancamento QComboBox:focus {
                border: 1px solid rgba(96, 165, 250, 200);
                background-color: rgba(15, 23, 42, 240);
            }
            QFrame#formLancamento QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QFrame#formLancamento QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #f8fafc;
                selection-background-color: #6366f1;
                border: 1px solid #334155;
            }
            QFrame#formLancamento QPushButton {
                background-color: #6366f1;
                color: white;
                font-weight: 800;
                border-radius: 10px;
                padding: 10px 16px;
                border: 1px solid rgba(199, 210, 254, 60);
            }
            QFrame#formLancamento QPushButton:hover {
                background-color: #4f46e5;
            }
            QFrame#formLancamento QPushButton#btn_fechar {
                background-color: rgba(71, 85, 105, 200);
                border: 1px solid rgba(148, 163, 184, 70);
            }
            QFrame#formLancamento QPushButton#btn_fechar:hover {
                background-color: rgba(100, 116, 139, 220);
            }
            QFrame#formLancamento QPushButton#btn_excluir {
                background-color: #e11d48;
                border: 1px solid rgba(253, 164, 175, 80);
            }
            QFrame#formLancamento QPushButton#btn_excluir:hover {
                background-color: #be123c;
            }
        """)
        self._anim_formulario = None
        

        # VALOR A PAGAR
        grid = QGridLayout(self.frame_formulario)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setSpacing(12)

        estilo_radio_grupo = """
            QFrame {
                background-color: #1e293b;
                border: none;
                padding: 0px;
            }
            QRadioButton {
                color: #f8fafc;
                font-size: 12px;
                spacing: 4px;
                background: #1e293b;
            }
            QRadioButton::indicator {
                width: 12px;
                height: 12px;
            }
            QRadioButton::indicator:checked {
                background-color: #6d5dd3;
                border: 2px solid #6d5dd3;
                border-radius: 6px;
            }
            QRadioButton::indicator:unchecked {
                background-color: #1e293b;
                border: 2px solid #64748b;
                border-radius: 6px;
            }
        """

        grupo_insercao = QFrame()
        grupo_insercao.setStyleSheet(estilo_radio_grupo)
        layout_grupo = QHBoxLayout(grupo_insercao)
        layout_grupo.setContentsMargins(4, 0, 4, 0)
        layout_grupo.setSpacing(6)

        self.radio_valor = QRadioButton("R$")
        self.radio_porcentagem = QRadioButton("%")
        self.radio_valor.setChecked(True)

        self.radio_valor.toggled.connect(self.toggle_modo_insercao)
        self.radio_porcentagem.toggled.connect(self.toggle_modo_insercao)

        layout_grupo.addWidget(self.radio_valor)
        layout_grupo.addWidget(self.radio_porcentagem)

        # VALORES PAGOS
        grupo_pagos = QFrame()
        grupo_pagos.setStyleSheet(estilo_radio_grupo)
        layout_grupo_pagos = QHBoxLayout(grupo_pagos)
        layout_grupo_pagos.setContentsMargins(4, 0, 4, 0)
        layout_grupo_pagos.setSpacing(6)

        self.radio_valor_pago = QRadioButton("R$")
        self.radio_porcentagem_pago = QRadioButton("%")
        self.radio_valor_pago.setChecked(True)

        self.radio_valor_pago.toggled.connect(self.toggle_modo_pagos)
        self.radio_porcentagem_pago.toggled.connect(self.toggle_modo_pagos)

        layout_grupo_pagos.addWidget(self.radio_valor_pago)
        layout_grupo_pagos.addWidget(self.radio_porcentagem_pago)

        
        # Componentes do Formulário
        self.txt_pc = QLineEdit(); self.txt_pc.setPlaceholderText("PC (ex: PC_13825) *")
        self.txt_pc.editingFinished.connect(self.tentar_carregar_pc_existente)
        self.combo_prestador = QComboBox()
        self.combo_prestador.setEditable(True)
        self.combo_prestador.setInsertPolicy(QComboBox.NoInsert)  # não cria item novo ao digitar
        self.completer_prestador = QCompleter(self.combo_prestador.model(), self.combo_prestador)
        self.completer_prestador.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer_prestador.setFilterMode(Qt.MatchContains)
        self.completer_prestador.setCompletionMode(QCompleter.PopupCompletion)
        self.combo_prestador.setCompleter(self.completer_prestador)
        # Estilo do popup do autocomplete (lista filtrada) — mesmo tema escuro
        self.completer_prestador.popup().setStyleSheet("""
            QListView {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                selection-background-color: #6d5dd3;
                selection-color: #ffffff;
                outline: 0;
                padding: 6px;
                min-height: 36px;
            }
            QListView::item {
                min-height: 28px;
                padding: 6px 10px;
            }
        """)
        self.txt_atividade = QLineEdit(); self.txt_atividade.setPlaceholderText("Atividade / Serviço")
        self.txt_valor_total = QLineEdit(); self.txt_valor_total.setPlaceholderText("Valor Total PC (R$) *")

        # Valores pagos
        self.txt_valores_pagos = QLineEdit()
        self.txt_valores_pagos.setPlaceholderText("Valores Pagos (R$)")
        self.txt_valores_pagos.setText("0")
        self.txt_valores_pagos.textChanged.connect(self.atualizar_preview_porcentagem)

        # Valor a Pagar
        self.txt_valor_a_pagar = QLineEdit()
        self.txt_valor_a_pagar.setPlaceholderText("Valor a Pagar (R$)")
        self.txt_valor_a_pagar.textChanged.connect(self.atualizar_preview_porcentagem)
        self.txt_valor_total.textChanged.connect(self.atualizar_preview_porcentagem)
        

        # Instanciação do Label do Preview (CORREÇÃO DO BUG DE ATRIBUTO)
        self.lbl_preview_porcentagem = QLabel("")
        self.lbl_preview_porcentagem.setStyleSheet("color: #a78bfa; font-weight: bold; font-size: 12px; padding-left: 5px;")
        self.lbl_preview_porcentagem.setVisible(False)

        self.combo_status = QComboBox(); self.combo_status.addItems(["MOBILIZAÇÃO", "ADIANT", "CONCLUSÃO"])
        self.txt_oc = QLineEdit(); self.txt_oc.setPlaceholderText("OC / PO")
        self.txt_end_id = QLineEdit(); self.txt_end_id.setPlaceholderText("END ID")
        self.txt_nota_fiscal = QLineEdit(); self.txt_nota_fiscal.setPlaceholderText("Nota Fiscal (Opcional)")
        self.txt_regional = QLineEdit(); self.txt_regional.setPlaceholderText("Regional (ex: TSL, TLE)")

        # --- ARRANJO ORGANIZADO DO GRID ---
        # Linha 0
        grid.addWidget(self.txt_pc, 0, 0)
        grid.addWidget(self.combo_prestador, 0, 1, 1, 2)
        grid.addWidget(self.txt_oc, 0, 3)
        grid.addWidget(self.txt_end_id, 0, 4)

        # Linha 1
        grid.addWidget(self.txt_atividade, 1, 0, 1, 4)
        grid.addWidget(self.txt_regional, 1, 4)

        # Linha 2: Valor Total, Valores Pagos (+radio), Valor a Pagar (+radio), Status, Nota Fiscal
        grid.addWidget(self.txt_valor_total, 2, 0)
        grid.addWidget(self.txt_valores_pagos, 2, 1)
        grid.addWidget(grupo_pagos, 2, 1, 1, 1, Qt.AlignRight)
        grid.addWidget(self.txt_valor_a_pagar, 2, 2)
        grid.addWidget(grupo_insercao, 2, 2, 1, 1, Qt.AlignRight)
        grid.addWidget(self.combo_status, 2, 3)
        grid.addWidget(self.txt_nota_fiscal, 2, 4)


        # Linha 3: Preview (ocupando toda a linha)
        grid.addWidget(self.lbl_preview_porcentagem, 3, 0, 1, 3)

        # Linha 4 (Botões)
        layout_botoes = QHBoxLayout()
        self.btn_excluir = QPushButton("🗑️ Excluir Lançamento", objectName="btn_excluir")
        self.btn_excluir.clicked.connect(self.excluir_registro)
        self.btn_excluir.setVisible(False)

        self.btn_importar_pc = QPushButton("📄 Importar PC (PDF)")
        self.btn_importar_pc.setToolTip("Lê um PDF de medição e preenche o formulário")
        self.btn_importar_pc.setStyleSheet("""
            QPushButton {
                background-color: rgba(13, 148, 136, 220);
                color: white;
                font-weight: 800;
                border-radius: 10px;
                padding: 10px 16px;
                border: 1px solid rgba(94, 234, 212, 70);
            }
            QPushButton:hover { background-color: rgba(15, 118, 110, 240); }
        """)
        self.btn_importar_pc.clicked.connect(self.importar_pc_pdf)

        self.btn_salvar = QPushButton("Salvar Lançamento")
        self.btn_salvar.clicked.connect(self.salvar_registro)

        self.btn_fechar = QPushButton("Cancelar", objectName="btn_fechar")
        self.btn_fechar.clicked.connect(self.fechar_formulario)

        layout_botoes.addWidget(self.btn_excluir)
        layout_botoes.addWidget(self.btn_importar_pc)
        layout_botoes.addStretch()
        layout_botoes.addWidget(self.btn_fechar)
        layout_botoes.addWidget(self.btn_salvar)

        grid.addLayout(layout_botoes, 4, 0, 1, 5)

        layout_principal.addWidget(self.frame_formulario)

        # --- 4. TABELA ---
        self.tabela = QTableWidget()
        self.tabela.setWordWrap(True)
        self.tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tabela.setColumnCount(14)
        colunas = ["PC", "Prestador", "Atividade", "Valor Total", "Valor Líquido", 
                   "Valores Pagos", "Saldo a Pagar", "Valor a Pagar", "Saldo Aberto", 
                   "Status", "OC", "END ID", "NF", "Regional"]
        self.tabela.setHorizontalHeaderLabels(colunas)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.doubleClicked.connect(self.abrir_formulario_edicao)
        self.tabela.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabela.customContextMenuRequested.connect(self.on_tabela_menu_contexto)

        self.tabela.setAlternatingRowColors(False)
        self.tabela.setShowGrid(False)
        self.tabela.setCornerButtonEnabled(False)
        self.tabela.verticalHeader().setDefaultSectionSize(42)
        
        self.tabela.setStyleSheet("""
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
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #1e293b;
                width: 10px;
                height: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #475569;
                min-height: 24px;
                min-width: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background: #64748b;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                border: none;
                background: none;
            }
        """)
        
        layout_principal.addWidget(self.tabela)

    def toggle_modo_insercao(self):
        """Alterna entre modo valor e porcentagem"""
        if self.radio_porcentagem.isChecked():
            self.txt_valor_a_pagar.setPlaceholderText("Percentual a pagar(%)")
        else:
            self.txt_valor_a_pagar.setPlaceholderText("Valor a Pagar (R$)")
            self.lbl_preview_porcentagem.setVisible(False)
            self.lbl_preview_porcentagem.setText("")
        self.atualizar_preview_porcentagem()

    def toggle_modo_pagos(self):
        """Alterna entre modo valor e porcentagem"""
        if self.radio_porcentagem_pago.isChecked():
            self.txt_valores_pagos.setPlaceholderText("Percentual já pago(%)")
        else:
            self.txt_valores_pagos.setPlaceholderText("Valores pagos (R$)")
        self.atualizar_preview_porcentagem()

    def atualizar_preview_porcentagem(self):
        """
        Mostra o valor real em R$ quando o usuário digita uma porcentagem.
        A porcentagem recai sobre o VALOR TOTAL, não sobre o saldo a pagar.
        Também mostra o impacto dos Valores Pagos (se em porcentagem).
        """
        try:
            total = utils.str_para_float(self.txt_valor_total.text())
            
            # Processa Valores Pagos (pode ser valor ou porcentagem)
            pagos = 0.0
            texto_pagos = self.txt_valores_pagos.text().strip()
            
            if texto_pagos and total > 0:
                if self.radio_porcentagem_pago.isChecked():
                    # Valores Pagos em porcentagem sobre o total
                    percentual_pago = utils.str_para_float(texto_pagos.replace('%', ''))
                    pagos = (percentual_pago / 100.0) * total
                else:
                    pagos = utils.str_para_float(texto_pagos)
            
            saldo_a_pagar = max(0.0, total - pagos)
            
            # Processa Valor a Pagar (pode ser valor ou porcentagem)
            if self.radio_porcentagem.isChecked():
                # Valor a Pagar em porcentagem sobre o VALOR TOTAL
                percentual_texto = self.txt_valor_a_pagar.text().strip().replace('%', '')
                percentual = utils.str_para_float(percentual_texto)
                
                if percentual > 0 and total > 0:
                    valor_real = (percentual / 100.0) * total
                    valor_real = min(valor_real, saldo_a_pagar)  # Não pode ultrapassar o saldo
                    
                    self.lbl_preview_porcentagem.setText(
                        f"💡 {percentual:g}% do Total ({utils.float_para_moeda(total)}) = {utils.float_para_moeda(valor_real)} | "
                        f"Saldo a Pagar: {utils.float_para_moeda(saldo_a_pagar)}"
                    )
                    self.lbl_preview_porcentagem.setVisible(True)
                    return
            else:
                # Modo valor - apenas mostra o saldo atual
                valor_a_pagar = utils.str_para_float(self.txt_valor_a_pagar.text())
                if valor_a_pagar > 0:
                    saldo_aberto = saldo_a_pagar - valor_a_pagar
                    if saldo_aberto < 0:
                        self.lbl_preview_porcentagem.setText(
                            f"⚠️ Valor excede o saldo a pagar! Saldo: {utils.float_para_moeda(saldo_a_pagar)}"
                        )
                        self.lbl_preview_porcentagem.setVisible(True)
                        return
                    
        except Exception:
            pass
    
        self.lbl_preview_porcentagem.setVisible(False)
        self.lbl_preview_porcentagem.setText("")

    def exibir_alerta(self, titulo, mensagem):
        alerta(self, titulo, mensagem)

    def criar_card(self, titulo, valor_inicial, cor_grad_inicio, cor_grad_fim, cor_borda, icone=""):
        frame = QFrame(self)
        frame.setMinimumHeight(78)
        frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {cor_grad_inicio},
                    stop: 0.55 rgba(255, 255, 255, 28),
                    stop: 1 {cor_grad_fim}
                );
                border-radius: 16px;
                border: 1px solid {cor_borda};
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # Badge circular com ícone (Dashboard)
        if icone:
            badge = QLabel()
            badge.setPixmap(pixmap_icone(icone, "#ffffff", 18))
            badge.setFixedSize(40, 40)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("""
                background-color: rgba(255, 255, 255, 38);
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 40);
            """)
            layout.addWidget(badge, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(2)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet("""
            QLabel {
                color: #e2e8f0;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
                background: transparent;
                border: none;
            }
        """)

        lbl_valor = QLabel(valor_inicial)
        lbl_valor.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 20px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)

        col.addWidget(lbl_titulo)
        col.addWidget(lbl_valor)
        layout.addLayout(col, 1)

        # Chevron sutil a direita (estilo V2)
        chevron = QLabel("›")
        chevron.setStyleSheet("""
            color: rgba(255, 255, 255, 170);
            font-size: 22px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        layout.addWidget(chevron, 0, Qt.AlignVCenter)

        return lbl_valor

    def carregar_projetos_combo(self):
        self.combo_projeto.blockSignals(True)
        self.combo_projeto.clear()
        projetos = database.carregar_projetos()
        for p in projetos:
            self.combo_projeto.addItem(p)
        self.combo_projeto.blockSignals(False)

    def carregar_fornecedores_combo(self):
        """Recarrega a lista de fornecedores preservando a seleção atual (se ainda existir)."""
        atual = self.combo_prestador.currentText()
        self.combo_prestador.blockSignals(True)
        self.combo_prestador.clear()
        fornecedores = database.carregar_fornecedores()
        for f in fornecedores:
            razao = utils.limpar_texto(f.get('RAZÃO SOCIAL', ''))
            if razao:
                self.combo_prestador.addItem(razao)
        # Restaura o prestador que estava selecionado (ou o último usado)
        if atual:
            idx = self.combo_prestador.findText(atual)
            if idx >= 0:
                self.combo_prestador.setCurrentIndex(idx)
        self.combo_prestador.blockSignals(False)

    def mudar_projeto_ativo(self):
        self.ciclo_id_ativo = None
        self.carregar_dados_tabela()

    def projeto_atual(self):
        return self.combo_projeto.currentText() or "PROJETO AEV"

    def _titulo_aba(self, ciclo):
        titulo = (ciclo.get("titulo") or "").strip()
        if titulo:
            return titulo
        return database.TIPOS_CICLO.get(ciclo.get("tipo"), "Medição")

    def atualizar_barra_abas(self):
        """Recarrega a barra de abas do projeto atual e seleciona o ciclo ativo."""
        proj = self.projeto_atual()
        self._ciclos_cache = database.listar_ciclos_abertos(proj)

        self._bloqueando_abas = True
        while self.tab_ciclos.count() > 0:
            self.tab_ciclos.removeTab(0)

        idx_selecionado = 0
        for i, ciclo in enumerate(self._ciclos_cache):
            self.tab_ciclos.addTab(self._titulo_aba(ciclo))
            self.tab_ciclos.setTabData(i, ciclo["id"])
            if self.ciclo_id_ativo and ciclo["id"] == self.ciclo_id_ativo:
                idx_selecionado = i

        if self._ciclos_cache:
            if self.ciclo_id_ativo is None:
                self.ciclo_id_ativo = self._ciclos_cache[0]["id"]
                idx_selecionado = 0
            # Confirma se o ciclo ativo ainda existe
            ids = [c["id"] for c in self._ciclos_cache]
            if self.ciclo_id_ativo not in ids:
                self.ciclo_id_ativo = self._ciclos_cache[0]["id"]
                idx_selecionado = 0
            self.tab_ciclos.setCurrentIndex(idx_selecionado)
        else:
            self.ciclo_id_ativo = None

        self.btn_nova_aba.setEnabled(True)
        self._bloqueando_abas = False

    def on_aba_alterada(self, index):
        if self._bloqueando_abas or index < 0:
            return
        ciclo_id = self.tab_ciclos.tabData(index)
        if ciclo_id and ciclo_id != self.ciclo_id_ativo:
            self.ciclo_id_ativo = ciclo_id
            self.fechar_formulario()
            self._recarregar_tabela_ciclo()

    def on_aba_duplo_clique(self, index):
        """Duplo clique na aba → editar título (e opcionalmente o tipo)."""
        if index < 0:
            return
        ciclo_id = self.tab_ciclos.tabData(index)
        if not ciclo_id:
            return
        self._editar_aba(ciclo_id)

    def on_aba_menu_contexto(self, pos):
        """Botão direito na aba → Renomear / Excluir."""
        index = self.tab_ciclos.tabAt(pos)
        if index < 0:
            return
        ciclo_id = self.tab_ciclos.tabData(index)
        if not ciclo_id:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b; color: #f8fafc;
                border: 1px solid #334155; padding: 4px;
            }
            QMenu::item { padding: 8px 24px; }
            QMenu::item:selected { background-color: #6d5dd3; }
        """)
        acao_editar = menu.addAction("✏️ Editar título / tipo")
        acao_excluir = menu.addAction("🗑️ Excluir aba")
        escolhida = menu.exec(self.tab_ciclos.mapToGlobal(pos))

        if escolhida == acao_editar:
            self._editar_aba(ciclo_id)
        elif escolhida == acao_excluir:
            self._excluir_aba(ciclo_id)

    def _editar_aba(self, ciclo_id):
        ciclo = database.obter_ciclo(ciclo_id)
        if not ciclo:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Editar aba")
        dialog.setMinimumWidth(380)
        dialog.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #f8fafc; font-size: 13px; }
            QComboBox, QLineEdit {
                background-color: #1e293b; color: #f8fafc;
                border: 1px solid #334155; border-radius: 6px; padding: 8px;
            }
            QPushButton {
                background-color: #6d5dd3; color: white; font-weight: bold;
                border-radius: 6px; padding: 8px 16px;
            }
            QPushButton:hover { background-color: #5b4bc4; }
        """)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Tipo de medição:"))
        combo_tipo = QComboBox()
        for key, label in database.TIPOS_CICLO.items():
            combo_tipo.addItem(label, key)
        idx_tipo = combo_tipo.findData(ciclo.get("tipo"))
        if idx_tipo >= 0:
            combo_tipo.setCurrentIndex(idx_tipo)
        layout.addWidget(combo_tipo)

        layout.addWidget(QLabel("Título da aba:"))
        txt_titulo = QLineEdit()
        txt_titulo.setText(ciclo.get("titulo") or "")
        txt_titulo.setPlaceholderText("Deixe em branco para usar o nome do tipo")
        layout.addWidget(txt_titulo)

        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(dialog.accept)
        botoes.rejected.connect(dialog.reject)
        layout.addWidget(botoes)

        if dialog.exec() != QDialog.Accepted:
            return

        tipo = combo_tipo.currentData()
        titulo = txt_titulo.text().strip()
        if not titulo:
            titulo = database.TIPOS_CICLO.get(tipo, "Medição")

        if database.atualizar_ciclo(ciclo_id, titulo=titulo, tipo=tipo):
            self.carregar_dados_tabela()
        else:
                erro(self, "Erro ao editar aba", "Não foi possível atualizar a aba.\n\nVerifique se a aba ainda está aberta e tente novamente.")

    def _excluir_aba(self, ciclo_id):
        ciclo = database.obter_ciclo(ciclo_id)
        nome = self._titulo_aba(ciclo) if ciclo else "esta aba"

        # Conta lançamentos do ciclo
        lancs = database.carregar_lancamentos(
            self.projeto_atual(), ciclo_id=ciclo_id
        )
        extra = ""
        if lancs:
            extra = (
                f"\n\nEsta aba possui {len(lancs)} lançamento(s), que serão "
                "excluídos permanentemente (não vão para o histórico).\n"
                "Se quiser registrar no histórico, use 'Fechar Medição'."
            )

        resp = confirmar(self, "Excluir aba", f"Deseja excluir a aba '{nome}'?{extra}")
        if not resp:
            return

        if database.excluir_ciclo(ciclo_id):
            if self.ciclo_id_ativo == ciclo_id:
                self.ciclo_id_ativo = None
            self.fechar_formulario()
            self.carregar_dados_tabela()
        else:
                erro(self, "Erro ao excluir aba", "Não foi possível excluir a aba.\n\nVerifique se:\n• A aba ainda existe\n• O banco de dados não está em uso por outro programa")

    def dialog_novo_ciclo(self):
        """Diálogo: tipo + título opcional. Retorna (tipo, titulo) ou None."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nova aba de medição")
        dialog.setMinimumWidth(380)
        dialog.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #f8fafc; font-size: 13px; }
            QComboBox, QLineEdit {
                background-color: #1e293b; color: #f8fafc;
                border: 1px solid #334155; border-radius: 6px; padding: 8px;
            }
            QPushButton {
                background-color: #6d5dd3; color: white; font-weight: bold;
                border-radius: 6px; padding: 8px 16px;
            }
            QPushButton:hover { background-color: #5b4bc4; }
        """)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Tipo de medição:"))
        combo_tipo = QComboBox()
        for key, label in database.TIPOS_CICLO.items():
            combo_tipo.addItem(label, key)
        layout.addWidget(combo_tipo)

        layout.addWidget(QLabel("Título da aba (opcional):"))
        txt_titulo = QLineEdit()
        txt_titulo.setPlaceholderText("Deixe em branco para usar o nome do tipo")
        layout.addWidget(txt_titulo)

        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(dialog.accept)
        botoes.rejected.connect(dialog.reject)
        layout.addWidget(botoes)

        if dialog.exec() != QDialog.Accepted:
            return None
        tipo = combo_tipo.currentData()
        titulo = txt_titulo.text().strip() or None
        return tipo, titulo

    def criar_nova_aba(self):
        proj = self.projeto_atual()
        qtd = database.contar_ciclos_abertos(proj)
        if qtd >= database.LIMITE_ABAS_POR_PROJETO:
            alerta(self, "Limite de abas", f"Limite de {database.LIMITE_ABAS_POR_PROJETO} abas atingido neste projeto.\nFeche a medição de uma das abas para abrir uma nova.")
            return

        resultado = self.dialog_novo_ciclo()
        if not resultado:
            return
        tipo, titulo = resultado
        novo_id = database.criar_ciclo(proj, tipo=tipo, titulo=titulo)
        if not novo_id:
            erro(self, "Erro ao criar aba",
                "Não foi possível criar a nova aba.\n\n"
                "Verifique se:\n"
                f"• O limite de {database.LIMITE_ABAS_POR_PROJETO} abas por projeto não foi atingido\n"
                "• O projeto selecionado é válido\n"
                "• O banco de dados permite gravação",
            )
            return

        self.ciclo_id_ativo = novo_id
        self.fechar_formulario()
        self.carregar_dados_tabela()


    def _registrar_atalhos(self):
        """Atalhos de teclado da tela de lançamentos."""
        def _at(seq, slot, contexto=Qt.ShortcutContext.WindowShortcut):
            # WindowShortcut: funciona mesmo após fechar modal (foco "perdido")
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(contexto)
            sc.activated.connect(slot)
            return sc

        _at("Esc", self._atalho_esc)
        _at("Ctrl+N", self.abrir_formulario_novo)
        _at("Ctrl+Return", self._atalho_salvar)
        _at("Ctrl+Enter", self._atalho_salvar)
        _at("Ctrl+I", self.importar_pc_pdf)
        _at("Ctrl+Tab", self.criar_nova_aba)
        _at("Ctrl+F", self.fechar_medicao)
        _at("Ctrl+L", self.limpar_medicao_projeto)
        _at("Ctrl+S", self.exportar_excel)

    def _formulario_aberto(self):
        return (
            self.frame_formulario.isVisible()
            and self.frame_formulario.maximumHeight() > 0
        )

    def _focar_campo_formulario(self, campo=None):
        """Garante foco no formulário após abrir / fechar modal."""
        alvo = campo or self.txt_pc
        def _go():
            if self._formulario_aberto():
                alvo.setFocus(Qt.FocusReason.OtherFocusReason)
                if hasattr(alvo, "selectAll"):
                    try:
                        alvo.selectAll()
                    except Exception:
                        pass
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, _go)
        QTimer.singleShot(320, _go)  # após animação de abertura

    def _atalho_esc(self):
        if self._formulario_aberto():
            self.fechar_formulario()

    def _atalho_salvar(self):
        if self._formulario_aberto():
            self.salvar_registro()

    def garantir_ciclo_ativo(self):
        """Garante que existe um ciclo ativo; se não, oferece criar. Retorna True se ok."""
        if self.ciclo_id_ativo:
            return True
        proj = self.projeto_atual()
        ciclos = database.listar_ciclos_abertos(proj)
        if ciclos:
            self.ciclo_id_ativo = ciclos[0]["id"]
            return True

        resposta = confirmar(
            self,
            "Iniciar medição",
            f"O projeto '{proj}' não possui medição aberta.\n\n"
            "Deseja criar uma nova aba agora?",
        )
        if not resposta:
            return False

        resultado = self.dialog_novo_ciclo()
        if not resultado:
            return False
        tipo, titulo = resultado
        novo_id = database.criar_ciclo(proj, tipo=tipo, titulo=titulo)
        if not novo_id:
            erro(self, "Erro ao criar medição",
                "Não foi possível criar a medição.\n\n"
                "Verifique se:\n"
                f"• O limite de {database.LIMITE_ABAS_POR_PROJETO} abas por projeto não foi atingido\n"
                "• O projeto selecionado é válido",
            )
            return False
        self.ciclo_id_ativo = novo_id
        self.atualizar_barra_abas()
        return True

    @staticmethod
    def _pilula_status(texto):
        """QLabel em forma de pílula para a coluna Status (estilo Dashboard)."""
        t = utils.limpar_texto(texto).upper()
        if "MOBILIZA" in t:
            fundo, frente, borda = "rgba(13, 148, 136, 210)", "#ecfeff", "rgba(45, 212, 191, 140)"
            curto = "MOBILIZ."
        elif "ADIANT" in t or "ADVANCE" in t:
            fundo, frente, borda = "rgba(217, 119, 6, 210)", "#fffbeb", "rgba(251, 191, 36, 140)"
            curto = "ADIANT."
        elif "CONCLU" in t:
            fundo, frente, borda = "rgba(109, 40, 217, 210)", "#f5f3ff", "rgba(167, 139, 250, 140)"
            curto = "CONCL."
        else:
            fundo, frente, borda = "rgba(71, 85, 105, 160)", "#e2e8f0", "rgba(148, 163, 184, 80)"
            curto = (texto or "—")[:10]
        lbl = QLabel(curto)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedHeight(26)
        lbl.setMinimumWidth(78)
        lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {fundo};
                color: {frente};
                border-radius: 11px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 0.3px;
                border: 1px solid {borda};
            }}
        """)
        return lbl

    def _recarregar_tabela_ciclo(self):
        """Recarrega só a tabela/cards do ciclo ativo (sem remontar abas)."""
        proj_nome = self.projeto_atual()
        if self.ciclo_id_ativo:
            self.dados_carregados = database.carregar_lancamentos(
                proj_nome, ciclo_id=self.ciclo_id_ativo
            )
        else:
            self.dados_carregados = []

        self.tabela.setUpdatesEnabled(False)
        self.tabela.setRowCount(0)
        cols_financeiras = {3, 4, 5, 6, 7, 8}

        for i, row_data in enumerate(self.dados_carregados):
            valores = list(row_data.values())[:14]
            self.tabela.insertRow(i)
            for j, val in enumerate(valores):
                if j in cols_financeiras:
                    texto_item = utils.float_para_moeda(val)
                else:
                    texto_item = utils.limpar_texto(val)
                if j == 9:
                    # Coluna Status -> pilula colorida (estilo V2)
                    self.tabela.setItem(i, j, QTableWidgetItem(""))
                    self.tabela.setCellWidget(i, j, self._pilula_status(texto_item))
                    continue
                item = QTableWidgetItem(texto_item)
                if j in cols_financeiras:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabela.setItem(i, j, item)

        self.filtrar_tabela()
        self.atualizar_resumo_topo()
        header = self.tabela.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        self.tabela.setColumnWidth(0, 110)
        self.tabela.setColumnWidth(1, 160)
        self.tabela.setColumnWidth(2, 380)
        self.tabela.setColumnWidth(3, 110)
        self.tabela.setColumnWidth(9, 100)
        self.tabela.setUpdatesEnabled(True)

    def _criar_glow_wrapper(self, card_frame):
        """Envolve o card em um QFrame que fornece espaço para a borda de glow animada."""
        wrapper = QFrame(self)
        wrapper.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                padding: 4px;
            }
        """)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(card_frame)
        return wrapper

    def atualizar_cards(self, lancamentos):
        # Se filtro por card ativo, cards mostram valores do ciclo inteiro (não recalcula)
        if self._filtro_status:
            lancamentos = self.dados_carregados

        tot_mob = sum(
            utils.str_para_float(l.get("VALOR A PAGAR", 0))
            for l in lancamentos 
            if "MOBILIZA" in utils.limpar_texto(l.get("STATUS PC", "")).upper()
        )

        tot_adi = sum(
            utils.str_para_float(l.get("VALOR A PAGAR", 0))
            for l in lancamentos 
            if "ADIANT" in utils.limpar_texto(l.get("STATUS PC", "")).upper() or "ADVANCE" in utils.limpar_texto(l.get("STATUS PC", "")).upper()
        )

        tot_conc = sum(
            utils.str_para_float(l.get("VALOR A PAGAR", 0))
            for l in lancamentos 
            if "CONCLU" in utils.limpar_texto(l.get("STATUS PC", "")).upper()
        )

        self.lbl_card_mobilizacao.setText(utils.float_para_moeda(tot_mob))
        self.lbl_card_adiantamento.setText(utils.float_para_moeda(tot_adi))
        self.lbl_card_conclusao.setText(utils.float_para_moeda(tot_conc))

    def atualizar_resumo_topo(self):
        """Contador de lançamentos por status + total da medição (Σ valor a pagar).

        Sempre considera o ciclo inteiro (self.dados_carregados), sem interferência
        da busca — assim o total exibido bate com a planilha exportada.
        """
        def plural(n, singular, plural_txt):
            return f"{n} {singular}" if n == 1 else f"{n} {plural_txt}"

        lancamentos = self.dados_carregados
        n_total = len(lancamentos)
        n_mob = sum(
            1 for l in lancamentos
            if "MOBILIZA" in utils.limpar_texto(l.get("STATUS PC", "")).upper()
        )
        n_adi = sum(
            1 for l in lancamentos
            if "ADIANT" in utils.limpar_texto(l.get("STATUS PC", "")).upper()
            or "ADVANCE" in utils.limpar_texto(l.get("STATUS PC", "")).upper()
        )
        n_con = sum(
            1 for l in lancamentos
            if "CONCLU" in utils.limpar_texto(l.get("STATUS PC", "")).upper()
        )
        total_medicao = sum(
            utils.str_para_float(l.get("VALOR A PAGAR", 0))
            for l in lancamentos
        )

        self.lbl_contador.setText(
            f"{plural(n_total, 'Lançamento', 'Lançamentos')} — "
            f"{plural(n_mob, 'Mobilização', 'Mobilizações')} • "
            f"{plural(n_adi, 'Adiantamento', 'Adiantamentos')} • "
            f"{plural(n_con, 'Conclusão', 'Conclusões')}"
        )
        self.lbl_total_medicao.setText(
            f'<span style="color:#bfdbfe;">Total da Medição:</span> '
            f'<span style="color:#ffffff; font-weight:800;">'
            f"{utils.float_para_moeda(total_medicao)}</span>"
        )

    def carregar_dados_tabela(self):
        self.atualizar_barra_abas()
        self._recarregar_tabela_ciclo()

    def filtrar_tabela(self):
        termo = self.txt_busca.text().lower().strip()
        lancamentos_visiveis = []

        for row in range(self.tabela.rowCount()):
            match = False
            if not termo:
                match = True
            else:
                for col in range(self.tabela.columnCount()):
                    item = self.tabela.item(row, col)
                    if item and termo in item.text().lower():
                        match = True
                        break

            # Filtro por card (status) — só a tabela filtra; cards/contador/total não mudam
            if match and self._filtro_status and row < len(self.dados_carregados):
                status_lanc = utils.limpar_texto(self.dados_carregados[row].get("STATUS PC", "")).upper()
                match = self._filtro_status in status_lanc

            self.tabela.setRowHidden(row, not match)

            if match and row < len(self.dados_carregados):
                lancamentos_visiveis.append(self.dados_carregados[row])

        self.atualizar_cards(lancamentos_visiveis)

    def toggle_filtro_card(self, chave):
        """Alterna o filtro de status ao clicar no card."""
        if self._filtro_status == chave:
            self.remover_filtro()
        else:
            self._filtro_status = chave
            self._aplicar_visual_filtro()
            self.filtrar_tabela()

    def remover_filtro(self):
        """Remove o filtro de status e restaura visual dos cards."""
        self._filtro_status = None
        self._reset_visual_cards()
        self.filtrar_tabela()

    def _aplicar_visual_filtro(self):
        """Glow RGB no card selecionado + esmaece os outros."""
        self.btn_remover_filtro.setVisible(True)

        for chave, wrapper in self._card_frames.items():
            if chave == self._filtro_status:
                self._iniciar_glow(wrapper)
            else:
                # Esmaece o card DENTRO do wrapper (preserva stylesheet do wrapper)
                card = wrapper.findChild(QFrame)
                if card:
                    style = card.styleSheet()
                    if "opacity: 0.35" not in style:
                        card.setStyleSheet(style + "\nQFrame { opacity: 0.35; }")

    def _reset_visual_cards(self):
        """Remove glow e restaura opacidade de todos os cards."""
        self.btn_remover_filtro.setVisible(False)
        self._parar_glow()
        for chave, wrapper in self._card_frames.items():
            # Restaura wrapper (sem borda de glow)
            wrapper.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                    padding: 4px;
                }
            """)
            # Restaura stylesheet original do card (sem opacity)
            card = wrapper.findChild(QFrame)
            if card:
                orig = self._card_original_style.get(chave, "")
                card.setStyleSheet(orig)

    def _iniciar_glow(self, wrapper):
        """Inicia animação RGB na borda do wrapper (não toca no card)."""
        self._parar_glow()
        self._glow_frame_idx = 0
        self._glow_target = wrapper
        self._animacao_glow = self.startTimer(50)  # 50ms por frame

    def _parar_glow(self):
        """Para a animação RGB e restaura o wrapper."""
        if self._animacao_glow is not None:
            self.killTimer(self._animacao_glow)
            self._animacao_glow = None
        if hasattr(self, '_glow_target') and self._glow_target is not None:
            self._glow_target.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                    padding: 4px;
                }
            """)

    def timerEvent(self, event):
        """Atualiza a cor da borda RGB (apenas no wrapper, preserva o card)."""
        if self._animacao_glow is None or not hasattr(self, '_glow_target'):
            return
        if event.timerId() == self._animacao_glow:
            self._glow_frame_idx = (self._glow_frame_idx + 1) % 100
            # HSL: hue de 0 a 360
            hue = int(self._glow_frame_idx * 3.6)
            cor = QColor.fromHsl(hue, 255, 128).name()
            # Apenas o wrapper recebe a borda animada; o card dentro mantém seu stylesheet
            self._glow_target.setStyleSheet(f"""
                QFrame {{
                    border: 2px solid {cor};
                    border-radius: 16px;
                    padding: 4px;
                    background: transparent;
                }}
            """)

    def importar_pc_pdf(self):
        """Lê PDF de medição e preenche o formulário de novo lançamento."""
        if not self.garantir_ciclo_ativo():
            return

        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar PDF do PC",
            "",
            "PDF (*.pdf)",
        )
        if not caminho:
            return

        try:
            dados = importar_pc_medicao(caminho)
        except ValueError as e:
            erro(self, "Erro na importação", str(e))
            return
        except Exception as e:
            erro(self, "Erro na importação",
                "Não foi possível ler o PDF.\n\n"
                "Verifique se:\n"
                "• O arquivo não está aberto em outro programa\n"
                "• É um PC de medição com texto (não só imagem digitalizada)\n\n"
                f"Detalhe técnico: {e}",
            )
            return

        # Novo lançamento (não força modo edição da linha atual)
        self.pc_em_edicao = None
        self.btn_excluir.setVisible(False)
        self.btn_salvar.setText("Salvar Lançamento")

        self.txt_pc.setText(dados.pc)
        self.txt_oc.setText(dados.oc)
        self.txt_end_id.setText(dados.end_id)
        self.txt_atividade.setText(dados.atividade)
        self.txt_regional.setText(dados.regional)
        self.txt_valor_total.setText(
            f"{dados.valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if dados.valor_total
            else ""
        )
        # Usuário informa pago / a pagar / status / NF
        self.txt_valores_pagos.setText("0")
        self.txt_valor_a_pagar.clear()
        self.txt_nota_fiscal.clear()
        self.radio_valor.setChecked(True)
        self.radio_valor_pago.setChecked(True)
        self.txt_valor_a_pagar.setPlaceholderText("Valor a Pagar (R$)")
        self.txt_valores_pagos.setPlaceholderText("Valores Pagos (R$)")
        self.lbl_preview_porcentagem.setVisible(False)

        fornecedores = database.carregar_fornecedores()
        match = match_prestador_cadastrado(
            dados.razao_social, dados.fantasia, fornecedores
        )
        avisos = list(dados.warnings)
        if match:
            idx = self.combo_prestador.findText(match)
            if idx >= 0:
                self.combo_prestador.setCurrentIndex(idx)
            else:
                self.combo_prestador.setCurrentText(match)
        else:
            self.combo_prestador.setCurrentIndex(-1)
            self.combo_prestador.setEditText("")
            nome_pdf = dados.razao_social or dados.fantasia or "(não lido)"
            avisos.append(
                f"Prestador « {nome_pdf} » não encontrado no cadastro. "
                "Cadastre-o em Cadastros ou selecione manualmente."
            )

        self._mostrar_formulario_animado()

        msg = "Arquivo importado com sucesso.\n\nCheque os campos preenchidos!"
        if avisos:
            msg += "\n\nAtenção:\n• " + "\n• ".join(avisos)

        tipo_icone = "alerta" if avisos else "info"
        if not match and (dados.razao_social or dados.fantasia):
            foi_para_cadastro = importacao_pc(
                self, msg, tipo_icone, com_botao_cadastro=True
            )
            if foi_para_cadastro:
                parent = self.window()
                if hasattr(parent, "mudar_tela"):
                    parent.mudar_tela(1)
            return
        informar(self, "Importação de PC", msg)

        # Após import: PC na mesma aba ou em outro ciclo
        self.tentar_carregar_pc_existente()
        self._focar_campo_formulario(self.txt_valor_a_pagar)

    def _aplicar_dados_pc_no_formulario(self, dados, modo_edicao=False, preencher_pagos=True):
        """Preenche o formulário com dados de um PC (edição ou nova parcela)."""
        prestador = utils.limpar_texto(dados.get("PRESTADOR", ""))
        if prestador:
            index = self.combo_prestador.findText(prestador)
            if index >= 0:
                self.combo_prestador.setCurrentIndex(index)
            else:
                self.combo_prestador.setCurrentText(prestador)

        atividade = utils.limpar_texto(dados.get("ATIVIDADE/SERVIÇO", ""))
        if atividade:
            self.txt_atividade.setText(atividade)

        total = utils.str_para_float(dados.get("VALOR TOTAL DO PC", 0))
        if dados.get("VALOR TOTAL DO PC") not in (None, ""):
            self.txt_valor_total.setText(str(dados.get("VALOR TOTAL DO PC", "")))

        if preencher_pagos:
            pagos = utils.str_para_float(dados.get("VALORES PAGOS", 0))
            if total > 0 and pagos >= 0:
                self.radio_porcentagem_pago.setChecked(True)
                self.txt_valores_pagos.setPlaceholderText("Percentual já pago(%)")
                self.txt_valores_pagos.setText(
                    self._formatar_percentual_exibicao((pagos / total) * 100.0)
                )
            else:
                self.radio_valor_pago.setChecked(True)
                self.txt_valores_pagos.setPlaceholderText("Valores Pagos (R$)")
                self.txt_valores_pagos.setText(str(dados.get("VALORES PAGOS", "0") or "0"))
        self.txt_valor_a_pagar.clear()
        self.radio_porcentagem.setChecked(True)
        self.txt_valor_a_pagar.setPlaceholderText("Percentual a pagar(%)")

        oc = utils.limpar_texto(dados.get("OC", ""))
        if oc:
            self.txt_oc.setText(oc)
        end_id = utils.limpar_texto(dados.get("END ID", ""))
        if end_id:
            self.txt_end_id.setText(end_id)
        regional = utils.limpar_texto(dados.get("REGIONAL", ""))
        if regional:
            self.txt_regional.setText(regional)

        if modo_edicao:
            nf = utils.limpar_texto(dados.get("NOTA FISCAL", ""))
            if nf:
                self.txt_nota_fiscal.setText(nf)
            status = utils.limpar_texto(dados.get("STATUS PC", ""))
            if status:
                idx_status = self.combo_status.findText(status)
                if idx_status >= 0:
                    self.combo_status.setCurrentIndex(idx_status)

        self.lbl_preview_porcentagem.setVisible(False)
        if hasattr(self, "atualizar_preview_porcentagem"):
            self.atualizar_preview_porcentagem()

    def tentar_carregar_pc_existente(self):
        """
        Ao informar um PC:
        - Se já existe NESTA aba → pergunta se deseja editar.
        - Se existe em OUTRO ciclo/histórico → pré-preenche base + valor já pago.
        """
        if self.pc_em_edicao:
            return

        pc = utils.limpar_texto(self.txt_pc.text())
        if not pc:
            return

        proj = self.projeto_atual()
        ciclo = self.ciclo_id_ativo

        # 1) Mesmo ciclo → confirmação antes de editar
        existente_ciclo = database.buscar_lancamento_por_pc(pc, proj, ciclo_id=ciclo)
        if existente_ciclo:
            resp = confirmar(self, "PC já lançado", f"O PC « {pc} » já existe nesta medição (aba atual).\n\nDeseja editar o lançamento existente?\n\n• Sim — carrega os dados para alteração\n• Não — mantém o formulário como está (evita sobrescrever por engano)")
            if not resp:
                return

            self.pc_em_edicao = pc
            self._aplicar_dados_pc_no_formulario(
                existente_ciclo, modo_edicao=True, preencher_pagos=True
            )
            self.btn_excluir.setVisible(True)
            self.btn_salvar.setText("Atualizar Lançamento")
            self._mostrar_formulario_animado()
            self._focar_campo_formulario(self.txt_valor_a_pagar)
            return

        # 2) Outro ciclo / histórico → nova parcela
        base = database.buscar_base_pc_projeto(pc, proj, excluir_ciclo_id=ciclo)
        if not base:
            return

        pagos = utils.str_para_float(base.get("VALORES PAGOS", 0))
        total = utils.str_para_float(base.get("VALOR TOTAL DO PC", 0))
        self.pc_em_edicao = None
        self.btn_excluir.setVisible(False)
        self.btn_salvar.setText("Salvar Lançamento")
        self._aplicar_dados_pc_no_formulario(base, modo_edicao=False, preencher_pagos=True)
        self._mostrar_formulario_animado()

        if total > 0 and pagos >= 0:
            pct = self._formatar_percentual_exibicao((pagos / total) * 100.0)
            pagos_txt = f"R$ {pagos:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            extra = f"Já pago: {pagos_txt} ({pct}%)\n\n"
        else:
            extra = ""

        informar(
            self,
            "PC encontrado em medição anterior",
            f"O PC « {pc} » já foi lançado em outra medição deste projeto.\n\n"
            f"Dados base e valor já pago foram preenchidos.\n{extra}"
            "Informe o valor a pagar desta parcela e revise os campos antes de salvar.",
        )
        self._focar_campo_formulario(self.txt_valor_a_pagar)

    def abrir_formulario_novo(self):
        if not self.garantir_ciclo_ativo():
            return
        self.carregar_fornecedores_combo()
        self.pc_em_edicao = None
        self.txt_pc.clear()
        self.txt_pc.setReadOnly(False)
        self.txt_atividade.clear()
        self.txt_valor_total.clear()
        self.txt_valor_a_pagar.clear()
        self.txt_valores_pagos.setText("0")
        self.txt_oc.clear()
        self.txt_end_id.clear()
        self.txt_nota_fiscal.clear()
        self.txt_regional.clear()
        self.btn_excluir.setVisible(False)

        self.radio_valor.setChecked(True)
        self.radio_valor_pago.setChecked(True)
        self.lbl_preview_porcentagem.setVisible(False)
        self.lbl_preview_porcentagem.setText("")
        self.txt_valor_a_pagar.setPlaceholderText("Valor a Pagar (R$)")
        self.txt_valores_pagos.setPlaceholderText("Valores Pagos (R$)")
        self.btn_salvar.setText("Salvar Lançamento")
        self._mostrar_formulario_animado()
        self._focar_campo_formulario(self.txt_pc)

    def abrir_formulario_edicao(self):
        self.carregar_fornecedores_combo()
        row = self.tabela.currentRow()
        self.pc_em_edicao = self.tabela.item(row, 0).text()
        
        self.txt_pc.setText(self.pc_em_edicao)
        self.txt_pc.setReadOnly(False)
        
        prestador = self.tabela.item(row, 1).text()
        index = self.combo_prestador.findText(prestador)
        if index >= 0:
            self.combo_prestador.setCurrentIndex(index)
        
        self.txt_atividade.setText(self.tabela.item(row, 2).text())
        
        if row < len(self.dados_carregados):
            dados_row = self.dados_carregados[row]
            total = utils.str_para_float(dados_row.get("VALOR TOTAL DO PC", 0))
            pagos = utils.str_para_float(dados_row.get("VALORES PAGOS", 0))
            a_pagar = utils.str_para_float(dados_row.get("VALOR A PAGAR", 0))

            self.txt_valor_total.setText(str(dados_row.get("VALOR TOTAL DO PC", "")))

            # Edição: reexibe em % (recalculado a partir do total) e mantém rádios em %
            # para o usuário só corrigir o número sem trocar o modo.
            if total > 0:
                pct_pagos = (pagos / total) * 100.0
                pct_a_pagar = (a_pagar / total) * 100.0
                self.txt_valores_pagos.setText(self._formatar_percentual_exibicao(pct_pagos))
                self.txt_valor_a_pagar.setText(self._formatar_percentual_exibicao(pct_a_pagar))
            else:
                self.txt_valores_pagos.setText(str(dados_row.get("VALORES PAGOS", "0")))
                self.txt_valor_a_pagar.setText(str(dados_row.get("VALOR A PAGAR", "")))

        self.combo_status.setCurrentText(self.tabela.item(row, 9).text())
        self.txt_oc.setText(self.tabela.item(row, 10).text())
        self.txt_end_id.setText(self.tabela.item(row, 11).text())
        self.txt_nota_fiscal.setText(self.tabela.item(row, 12).text())
        self.txt_regional.setText(self.tabela.item(row, 13).text())
        
        self.btn_excluir.setVisible(True)
        self.btn_salvar.setText("Atualizar Lançamento")

        # Rádios em % + placeholders de percentual
        self.radio_porcentagem.setChecked(True)
        self.radio_porcentagem_pago.setChecked(True)
        self.txt_valor_a_pagar.setPlaceholderText("Percentual a pagar(%)")
        self.txt_valores_pagos.setPlaceholderText("Percentual já pago(%)")
        self.lbl_preview_porcentagem.setVisible(False)
        self.atualizar_preview_porcentagem()
        self._mostrar_formulario_animado()
        self._focar_campo_formulario(self.txt_valor_a_pagar)

    def _formatar_percentual_exibicao(self, pct):
        """Formata % para o campo de edição (evita 50.0000001)."""
        try:
            pct = float(pct)
        except (TypeError, ValueError):
            return "0"
        if abs(pct - round(pct)) < 0.005:
            return str(int(round(pct)))
        return f"{pct:.2f}".rstrip("0").rstrip(".")

    def _parar_anim_formulario(self):
        if self._anim_formulario is not None:
            self._anim_formulario.stop()
            self._anim_formulario = None

    def _mostrar_formulario_animado(self):
        """Expande o formulário com animação (reaproveita se já estiver aberto)."""
        frame = self.frame_formulario
        # Já aberto e expandido — só garante visível
        if frame.isVisible() and frame.maximumHeight() > 40:
            frame.setMaximumHeight(16777215)
            return

        self._parar_anim_formulario()
        frame.setVisible(True)
        frame.setMaximumHeight(0)
        frame.updateGeometry()
        QApplication.processEvents()

        alvo = max(frame.sizeHint().height(), frame.minimumSizeHint().height(), 220)
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
        """Recolhe o formulário com animação e só então esconde."""
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

    def fechar_formulario(self):
        self._ocultar_formulario_animado()

    def salvar_registro(self):
        """Valida regras financeiras, campos obrigatórios e salva o lançamento."""
        pc = utils.limpar_texto(self.txt_pc.text())
        
        if not pc:
            self.exibir_alerta("Campo Obrigatório", "O campo 'PC' é obrigatório!")
            self.txt_pc.setFocus()
            return

        prestador = self.combo_prestador.currentText().strip()
        if not prestador:
            self.exibir_alerta("Seleção Inválida", "Selecione um Prestador / Fornecedor para o lançamento.")
            self.combo_prestador.setFocus()
            return

        # Processa VALOR TOTAL
        total = utils.str_para_float(self.txt_valor_total.text())
        if total <= 0:
            self.exibir_alerta("Valor Inválido", "O 'Valor Total do PC' deve ser maior que zero!")
            self.txt_valor_total.setFocus()
            return

        # Processa VALORES PAGOS (pode ser valor ou porcentagem)
        pagos = 0.0
        texto_pagos = self.txt_valores_pagos.text().strip()
        
        if texto_pagos:
            if self.radio_porcentagem_pago.isChecked():
                percentual_pago = utils.str_para_float(texto_pagos.replace('%', ''))
                pagos = (percentual_pago / 100.0) * total
            else:
                pagos = utils.str_para_float(texto_pagos)
            
            if pagos < 0:
                self.exibir_alerta("Valor Inválido", "Os 'Valores Pagos' não podem ser negativos.")
                self.txt_valores_pagos.setFocus()
                return

        # Calcula SALDO A PAGAR
        saldo_a_pagar = max(0.0, total - pagos)

        # Processa VALOR A PAGAR (pode ser valor ou porcentagem)
        a_pagar = 0.0
        texto_a_pagar = self.txt_valor_a_pagar.text().strip()
        
        if texto_a_pagar:
            if self.radio_porcentagem.isChecked():
                # Porcentagem sobre o VALOR TOTAL
                percentual_texto = texto_a_pagar.replace('%', '')
                percentual = utils.str_para_float(percentual_texto)
                a_pagar = (percentual / 100.0) * total
            else:
                a_pagar = utils.str_para_float(texto_a_pagar)
            
            if a_pagar < 0:
                self.exibir_alerta("Valor Inválido", "O 'Valor a Pagar' não pode ser negativo.")
                self.txt_valor_a_pagar.setFocus()
                return
        
        # Valida se o valor a pagar não excede o saldo a pagar
        if a_pagar > saldo_a_pagar:
            self.exibir_alerta(
                "Saldo Excedido", 
                f"O 'Valor a Pagar' (R$ {a_pagar:,.2f}) ultrapassa o saldo restante do PC (R$ {saldo_a_pagar:,.2f}).\n\n"
                f"Valor Total: R$ {total:,.2f}\n"
                f"Valores Pagos: R$ {pagos:,.2f}"
            )
            self.txt_valor_a_pagar.setFocus()
            return
        
        saldo_aberto = saldo_a_pagar - a_pagar

        dados = [
            pc,
            prestador,
            utils.limpar_texto(self.txt_atividade.text()),
            total,
            0.0,
            pagos,
            saldo_a_pagar,
            a_pagar,
            saldo_aberto,
            self.combo_status.currentText(),
            utils.limpar_texto(self.txt_oc.text()),
            utils.limpar_texto(self.txt_end_id.text()),
            utils.limpar_texto(self.txt_nota_fiscal.text()),
            utils.limpar_texto(self.txt_regional.text())
        ]

        proj = self.projeto_atual()
        if not self.garantir_ciclo_ativo():
            return
        ciclo_id = self.ciclo_id_ativo

        if self.pc_em_edicao:
            sucesso, erro = database.atualizar_lancamento(
                self.pc_em_edicao, dados, nome_projeto=proj, ciclo_id=ciclo_id
            )
        else:
            sucesso, erro = database.adicionar_lancamento(
                dados, nome_projeto=proj, ciclo_id=ciclo_id
            )

        if sucesso:
            informar(self, "Sucesso", f"Lançamento registrado com sucesso no projeto '{proj}'!")
            self.fechar_formulario()
            self.carregar_dados_tabela()
        else:
            erro(self, "Erro ao salvar lançamento", erro or "Não foi possível gravar o lançamento no banco de dados.")

    def on_tabela_menu_contexto(self, pos):
        """Menu rápido na tabela: excluir lançamento da linha."""
        row = self.tabela.indexAt(pos).row()
        if row < 0:
            return
        item_pc = self.tabela.item(row, 0)
        if not item_pc:
            return
        pc = item_pc.text().strip()
        if not pc:
            return

        self.tabela.selectRow(row)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(15, 23, 42, 245);
                color: #f8fafc;
                border: 1px solid rgba(148, 163, 184, 70);
                border-radius: 10px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 18px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: rgba(225, 29, 72, 180);
            }
        """)
        acao = menu.addAction("Excluir lançamento")
        escolhido = menu.exec(self.tabela.viewport().mapToGlobal(pos))
        if escolhido == acao:
            self._excluir_lancamento_pc(pc)

    def _excluir_lancamento_pc(self, pc):
        """Exclui um PC do ciclo ativo (com confirmação)."""
        proj = self.projeto_atual()
        if not confirmar(
            self,
            "Confirmar exclusão",
            f"Tem certeza que deseja excluir o lançamento « {pc} » "
            f"do projeto « {proj} »?",
        ):
            return
        sucesso, msg_erro = database.deletar_lancamento(
            pc, nome_projeto=proj, ciclo_id=self.ciclo_id_ativo
        )
        if sucesso:
            informar(self, "Sucesso", f"Lançamento « {pc} » excluído!")
            if self.pc_em_edicao and self.pc_em_edicao == pc:
                self.fechar_formulario()
            self.carregar_dados_tabela()
        else:
            erro(
                self,
                "Erro ao excluir",
                msg_erro or "Não foi possível excluir o lançamento do banco de dados.",
            )

    def excluir_registro(self):
        if not self.pc_em_edicao:
            return
        self._excluir_lancamento_pc(self.pc_em_edicao)

    def exportar_excel(self):
        proj = self.projeto_atual()
        if not self.garantir_ciclo_ativo():
            return
        nome_sugerido = f"MEDICAO_{proj.replace(' ', '_')}.xlsx"

        caminho_arquivo, _ = QFileDialog.getSaveFileName(
            self,
            f"Salvar Planilha do Financeiro - {proj}",
            nome_sugerido,
            "Arquivo Excel (*.xlsx)"
        )
        if caminho_arquivo:
            sucesso, erro = database.exportar_planilha_medicao(
                caminho_arquivo, nome_projeto=proj, ciclo_id=self.ciclo_id_ativo
            )
            if sucesso:
                total_medicao = sum(
                    utils.str_para_float(l.get("VALOR A PAGAR", 0))
                    for l in self.dados_carregados
                )
                planilha_pronta(
                    self,
                    caminho_arquivo,
                    total_medicao,
                    proj,
                )
            else:
                erro(self, "Erro na exportação", erro or "Não foi possível gerar a planilha de exportação.")

    def _resumo_ciclo(self):
        """Retorna contagens e total da medição atual (ciclo inteiro)."""
        lancamentos = self.dados_carregados
        n_total = len(lancamentos)
        n_mob = sum(1 for l in lancamentos if "MOBILIZA" in utils.limpar_texto(l.get("STATUS PC", "")).upper())
        n_adi = sum(1 for l in lancamentos if "ADIANT" in utils.limpar_texto(l.get("STATUS PC", "")).upper() or "ADVANCE" in utils.limpar_texto(l.get("STATUS PC", "")).upper())
        n_con = sum(1 for l in lancamentos if "CONCLU" in utils.limpar_texto(l.get("STATUS PC", "")).upper())
        total = sum(utils.str_para_float(l.get("VALOR A PAGAR", 0)) for l in lancamentos)

        def plural(n, sing, plur):
            return f"{n} {sing}" if n == 1 else f"{n} {plur}"

        return {
            "total": n_total,
            "mob": n_mob,
            "adi": n_adi,
            "con": n_con,
            "valor": total,
            "texto_contador": f"{plural(n_total, 'Lançamento', 'Lançamentos')} — {plural(n_mob, 'Mobilização', 'Mobilizações')} • {plural(n_adi, 'Adiantamento', 'Adiantamentos')} • {plural(n_con, 'Conclusão', 'Conclusões')}",
            "texto_total": f"Total da medição: {utils.float_para_moeda(total)}",
        }

    def fechar_medicao(self):
        proj = self.projeto_atual()
        if not self.ciclo_id_ativo:
            informar(self, "Nenhuma medição aberta", "Não há aba de medição aberta para fechar neste projeto.")
            return

        ciclo = database.obter_ciclo(self.ciclo_id_ativo)
        nome_aba = self._titulo_aba(ciclo) if ciclo else "Medição"

        resumo = self._resumo_ciclo()
        confirmacao = confirmar(
            self,
            "Fechar Medição do Ciclo",
            f"Confira antes de fechar a aba '{nome_aba}':\n\n"
            f"📊 {resumo['texto_contador']}\n"
            f"💰 {resumo['texto_total']}\n\n"
            "Isso irá:\n"
            "1. Gerar e salvar a planilha do financeiro.\n"
            "2. Registrar os lançamentos no histórico.\n"
            "3. Acumular o 'Valor a Pagar' em 'Valores Pagos'.\n"
            "4. Fechar esta aba (as outras abas do projeto continuam abertas).\n\n"
            "PCs com saldo em aberto poderão ser relançados em uma nova aba.",
        )

        if not confirmacao:
            return

        nome_sugerido = f"MEDICAO_CONSOLIDADA_{proj.replace(' ', '_')}.xlsx"
        caminho_arquivo, _ = QFileDialog.getSaveFileName(
            self,
            f"Salvar Fechamento - {nome_aba}",
            nome_sugerido,
            "Arquivo Excel (*.xlsx)"
        )

        if caminho_arquivo:
            sucesso, erro = database.fechar_e_consolidar_medicao(
                caminho_arquivo, nome_projeto=proj, ciclo_id=self.ciclo_id_ativo
            )
            if sucesso:
                planilha_pronta(
                    self,
                    caminho_arquivo,
                    resumo["valor"],
                    proj,
                )
                self.ciclo_id_ativo = None
                self.fechar_formulario()
                self.carregar_dados_tabela()
            else:
                erro(self, "Erro no Fechamento", erro or "Ocorreu um erro ao tentar fechar a medição.\nNenhum dado do banco foi alterado.")

    def limpar_medicao_projeto(self):
        """Recomeça só a aba/ciclo ativo (não apaga outras abas nem histórico)."""
        proj = self.projeto_atual()
        ciclo_id = self.ciclo_id_ativo

        if not ciclo_id:
            alerta(
                self,
                "Nenhuma aba ativa",
                "Selecione ou crie uma aba de medição antes de recomeçar.\n\n"
                "O recomeçar apaga apenas os lançamentos da aba atual.",
            )
            return

        ciclo = database.obter_ciclo(ciclo_id)
        nome_aba = self._titulo_aba(ciclo) if ciclo else "aba atual"
        msg = (
            f"Você está prestes a EXCLUIR os lançamentos da aba « {nome_aba} » "
            f"do projeto « {proj} ».\n\n"
            "• Outras abas permanecem intactas\n"
            "• Histórico / medições fechadas não são alterados\n"
            "• Cadastros de fornecedores permanecem\n\n"
            "Deseja continuar?"
        )

        if not confirmar(self, "Recomeçar medição da aba", msg):
            return
        if not confirmar(
            self,
            "Confirmação explícita",
            "Esta operação NÃO poderá ser desfeita para os lançamentos desta aba.\n\n"
            "Confirma a exclusão?",
        ):
            return

        sucesso, msg_erro = database.limpar_lancamentos_projeto(
            nome_projeto=proj, ciclo_id=ciclo_id
        )
        if sucesso:
            informar(
                self,
                "Aba reiniciada",
                f"Lançamentos da aba « {nome_aba} » removidos.\n"
                "A aba continua aberta para novos lançamentos.",
            )
            self.fechar_formulario()
            self.carregar_dados_tabela()
        else:
            erro(
                self,
                "Erro ao recomeçar",
                msg_erro or "Não foi possível remover os lançamentos do banco de dados.",
            )
