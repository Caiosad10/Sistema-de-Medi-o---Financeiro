import sys
from PySide6.QtWidgets import (
    QRadioButton, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QFrame, QFileDialog, QApplication, QCompleter
)
from PySide6.QtCore import Qt
import database
import utils 
from utils import str_para_float

class TelaLancamentos(QWidget):
    def __init__(self):
        super().__init__()
        self.pc_em_edicao = None
        self.dados_carregados = []
        self.init_ui()
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
        lbl_icone.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 14px;")
        
        self.combo_projeto = QComboBox()
        self.combo_projeto.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #38bdf8;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                padding: 6px 15px;
                min-width: 220px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #f8fafc;
                selection-background-color: #3b82f6;
            }
        """)
        self.combo_projeto.currentIndexChanged.connect(self.mudar_projeto_ativo)

        layout_topo_projeto.addWidget(lbl_icone)
        layout_topo_projeto.addWidget(self.combo_projeto)
        layout_topo_projeto.addStretch()
        
        layout_principal.addLayout(layout_topo_projeto)

        # --- 1. DASHBOARD DE STATUS (GRADIENTES BENTO UI) ---
        layout_cards = QHBoxLayout()
        self.lbl_card_mobilizacao = self.criar_card("Status: Mobilização", "R$ 0,00", "#b45309", "#78350f", "#f59e0b")
        self.lbl_card_adiantamento = self.criar_card("Status: Adiantamento", "R$ 0,00", "#1d4ed8", "#1e3a8a", "#60a5fa")
        self.lbl_card_conclusao = self.criar_card("Status: Conclusão", "R$ 0,00", "#6d28d9", "#4c1d95", "#a78bfa")
        self.lbl_card_saldo_aberto = self.criar_card("Saldo em Aberto (Total)", "R$ 0,00", "#be123c", "#881337", "#f43f5e")

        layout_cards.addWidget(self.lbl_card_mobilizacao.parentWidget())
        layout_cards.addWidget(self.lbl_card_adiantamento.parentWidget())
        layout_cards.addWidget(self.lbl_card_conclusao.parentWidget())
        
        # Guardamos o widget pai e o ocultamos visualmente
        card_saldo_widget = self.lbl_card_saldo_aberto.parentWidget()
        layout_cards.addWidget(card_saldo_widget)
        card_saldo_widget.setVisible(False)
        
        layout_principal.addLayout(layout_cards)

        # --- 2. BARRA DE AÇÕES (Botões e Campo de Busca) ---
        layout_acoes = QHBoxLayout()
        
        self.btn_novo = QPushButton("+ Novo Lançamento")
        self.btn_novo.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #059669; }
            QPushButton:pressed { background-color: #047857; }
        """)
        self.btn_novo.clicked.connect(self.abrir_formulario_novo)
        
        self.btn_exportar = QPushButton("📥 Exportar Financeiro")
        self.btn_exportar.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #0369a1; }
            QPushButton:pressed { background-color: #075985; }
        """)
        self.btn_exportar.clicked.connect(self.exportar_excel)

        self.btn_fechar_medicao = QPushButton("🔒 Fechar Medição")
        self.btn_fechar_medicao.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #7c3aed; }
            QPushButton:pressed { background-color: #6d28d9; }
        """)
        self.btn_fechar_medicao.clicked.connect(self.fechar_medicao)

        self.btn_limpar_projeto = QPushButton("🧹 Recomeçar Medição")
        self.btn_limpar_projeto.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #b91c1c; }
            QPushButton:pressed { background-color: #991b1b; }
        """)
        self.btn_limpar_projeto.clicked.connect(self.limpar_medicao_projeto)

        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("🔍 Buscar por PC, Prestador, Atividade, Status, NF...")
        self.txt_busca.setStyleSheet("""
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
                background-color: #0f172a;
            }
            QLineEdit::placeholder {
                color: #64748b;
            }
        """)
        self.txt_busca.textChanged.connect(self.filtrar_tabela)

        layout_acoes.addWidget(self.btn_novo)
        layout_acoes.addWidget(self.btn_exportar)
        layout_acoes.addWidget(self.btn_fechar_medicao)
        layout_acoes.addWidget(self.btn_limpar_projeto)
        layout_acoes.addStretch()
        layout_acoes.addWidget(self.txt_busca)
        
        layout_principal.addLayout(layout_acoes)

        # --- 3. FORMULÁRIO ---
        self.frame_formulario = QFrame()
        self.frame_formulario.setVisible(False)
        self.frame_formulario.setStyleSheet("""
            QFrame { background-color: #1e293b; border-radius: 10px; padding: 15px; }
            QLineEdit, QComboBox { background-color: #0f172a; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 8px; }
            QPushButton { background-color: #3b82f6; color: white; font-weight: bold; border-radius: 6px; padding: 10px 15px; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton#btn_fechar { background-color: #64748b; }
            QPushButton#btn_fechar:hover { background-color: #475569; }
            QPushButton#btn_excluir { background-color: #ef4444; }
            QPushButton#btn_excluir:hover { background-color: #dc2626; }
        """)
        

        # VALOR A PAGAR
        grid = QGridLayout(self.frame_formulario)
        grid.setSpacing(10)

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
                background-color: #3b82f6;
                border: 2px solid #3b82f6;
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
                selection-background-color: #3b82f6;
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
        self.lbl_preview_porcentagem.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px; padding-left: 5px;")
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

        self.btn_salvar = QPushButton("Salvar Lançamento")
        self.btn_salvar.clicked.connect(self.salvar_registro)
        
        self.btn_fechar = QPushButton("Cancelar", objectName="btn_fechar")
        self.btn_fechar.clicked.connect(self.fechar_formulario)
        
        layout_botoes.addWidget(self.btn_excluir)
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

        self.tabela.setAlternatingRowColors(False)
        self.tabela.setShowGrid(False)
        self.tabela.setCornerButtonEnabled(False)
        self.tabela.verticalHeader().setDefaultSectionSize(42)
        
        self.tabela.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 12px;
                gridline-color: transparent;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #0f172a;
            }
            QTableWidget::item:hover {
                background-color: #334155;
                color: #38bdf8;
            }
            QTableWidget::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #94a3b8;
                font-weight: bold;
                font-size: 12px;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #334155;
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
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(titulo)
        msg.setText(mensagem)
        msg.setStyleSheet("""
            QMessageBox { background-color: #1e293b; color: #f8fafc; }
            QLabel { color: #f8fafc; }
            QPushButton { background-color: #3b82f6; color: white; border-radius: 4px; padding: 6px 12px; }
        """)
        msg.exec()

    def criar_card(self, titulo, valor_inicial, cor_grad_inicio, cor_grad_fim, cor_borda):
        frame = QFrame(self)
        frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {cor_grad_inicio},
                    stop: 1 {cor_grad_fim}
                );
                border-radius: 12px;
                border: 1px solid {cor_borda};
                padding: 6px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)
        
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
                font-size: 22px;
                font-weight: 800;
                background: transparent;
                border: none;
            }
        """)
        
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_valor)
        
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
        self.carregar_dados_tabela()

    def projeto_atual(self):
        return self.combo_projeto.currentText() or "PROJETO AEV"

    def atualizar_cards(self, lancamentos):
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

    def carregar_dados_tabela(self):
        proj_nome = self.projeto_atual()
        self.dados_carregados = database.carregar_lancamentos(proj_nome)
        
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
                    
                item = QTableWidgetItem(texto_item)
                if j in cols_financeiras:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabela.setItem(i, j, item)
                
        self.filtrar_tabela()
        
        header = self.tabela.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        self.tabela.setColumnWidth(0, 110)
        self.tabela.setColumnWidth(1, 160)
        self.tabela.setColumnWidth(2, 380)
        self.tabela.setColumnWidth(3, 110)
        
        self.tabela.setUpdatesEnabled(True)

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

            self.tabela.setRowHidden(row, not match)

            if match and row < len(self.dados_carregados):
                lancamentos_visiveis.append(self.dados_carregados[row])

        self.atualizar_cards(lancamentos_visiveis)

    def tentar_carregar_pc_existente(self):
        """Se o PC já existir de um ciclo anterior, pré-preenche os dados acumulados."""
        if self.pc_em_edicao:
            return

        pc = utils.limpar_texto(self.txt_pc.text())
        if not pc:
            return

        existente = database.buscar_lancamento_por_pc(pc, self.projeto_atual())
        if not existente:
            return

        self.pc_em_edicao = pc

        prestador = utils.limpar_texto(existente.get("PRESTADOR", ""))
        index = self.combo_prestador.findText(prestador)
        if index >= 0:
            self.combo_prestador.setCurrentIndex(index)

        self.txt_atividade.setText(utils.limpar_texto(existente.get("ATIVIDADE/SERVIÇO", "")))
        self.txt_valor_total.setText(str(existente.get("VALOR TOTAL DO PC", "")))
        self.txt_valores_pagos.setText(str(existente.get("VALORES PAGOS", "")))
        self.txt_valor_a_pagar.clear()
        self.txt_oc.setText(utils.limpar_texto(existente.get("OC", "")))
        self.txt_end_id.setText(utils.limpar_texto(existente.get("END ID", "")))
        self.txt_nota_fiscal.setText(utils.limpar_texto(existente.get("NOTA FISCAL", "")))
        self.txt_regional.setText(utils.limpar_texto(existente.get("REGIONAL", "")))

        status = utils.limpar_texto(existente.get("STATUS PC", ""))
        if status:
            idx_status = self.combo_status.findText(status)
            if idx_status >= 0:
                self.combo_status.setCurrentIndex(idx_status)

        self.btn_excluir.setVisible(True)
        self.btn_salvar.setText("Atualizar Lançamento")

    def abrir_formulario_novo(self):
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
        self.frame_formulario.setVisible(True)

        self.radio_valor.setChecked(True)
        self.radio_valor_pago.setChecked(True)
        self.lbl_preview_porcentagem.setVisible(False)
        self.lbl_preview_porcentagem.setText("")
        self.txt_valor_a_pagar.setPlaceholderText("Valor a Pagar (R$)")
        self.txt_valores_pagos.setPlaceholderText("Valores Pagos (R$)")
        self.btn_salvar.setText("Salvar Lançamento")

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
            self.txt_valor_total.setText(str(dados_row.get("VALOR TOTAL DO PC", "")))
            self.txt_valores_pagos.setText(str(dados_row.get("VALORES PAGOS", "")))
            self.txt_valor_a_pagar.setText(str(dados_row.get("VALOR A PAGAR", "")))

        self.combo_status.setCurrentText(self.tabela.item(row, 9).text())
        self.txt_oc.setText(self.tabela.item(row, 10).text())
        self.txt_end_id.setText(self.tabela.item(row, 11).text())
        self.txt_nota_fiscal.setText(self.tabela.item(row, 12).text())
        self.txt_regional.setText(self.tabela.item(row, 13).text())
        
        self.btn_excluir.setVisible(True)
        self.frame_formulario.setVisible(True)
        self.btn_salvar.setText("Atualizar Lançamento")

        self.radio_valor.setChecked(True)
        self.lbl_preview_porcentagem.setVisible(False)

    def fechar_formulario(self):
        self.frame_formulario.setVisible(False)

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

        if self.pc_em_edicao:
            sucesso = database.atualizar_lancamento(self.pc_em_edicao, dados, nome_projeto=proj)
        else:
            sucesso = database.adicionar_lancamento(dados, nome_projeto=proj)

        if sucesso:
            QMessageBox.information(self, "Sucesso", f"Lançamento registrado com sucesso no projeto '{proj}'!")
            self.fechar_formulario()
            self.carregar_dados_tabela()
        else:
            QMessageBox.critical(self, "Erro", "Erro ao gravar as informações do lançamento no banco de dados.")

    def excluir_registro(self):
        if not self.pc_em_edicao:
            return

        proj = self.projeto_atual()

        resposta = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Tem certeza que deseja excluir o lançamento '{self.pc_em_edicao}' do projeto '{proj}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if resposta == QMessageBox.Yes:
            sucesso = database.deletar_lancamento(self.pc_em_edicao, nome_projeto=proj)
            if sucesso:
                QMessageBox.information(self, "Sucesso", f"Lançamento '{self.pc_em_edicao}' excluído!")
                self.fechar_formulario()
                self.carregar_dados_tabela()
            else:
                QMessageBox.critical(self, "Erro", "Erro ao excluir o lançamento do banco de dados.")

    def exportar_excel(self):
        proj = self.projeto_atual()
        nome_sugerido = f"MEDICAO_{proj.replace(' ', '_')}.xlsx"

        caminho_arquivo, _ = QFileDialog.getSaveFileName(
            self,
            f"Salvar Planilha do Financeiro - {proj}",
            nome_sugerido,
            "Arquivo Excel (*.xlsx)"
        )
        if caminho_arquivo:
            sucesso = database.exportar_planilha_medicao(caminho_arquivo, nome_projeto=proj)
            if sucesso:
                QMessageBox.information(self, "Exportação Concluída", f"Planilha do projeto '{proj}' salva com sucesso em:\n{caminho_arquivo}")
            else:
                QMessageBox.critical(self, "Erro", "Não foi possível gerar a planilha de exportação.")

    def fechar_medicao(self):
        proj = self.projeto_atual()
        
        confirmacao = QMessageBox.question(
            self,
            "Fechar Medição do Ciclo",
            f"Deseja fechar e consolidar a medição do projeto '{proj}'?\n\n"
            "Isso irá:\n"
            "1. Gerar e salvar a planilha do financeiro.\n"
            "2. Registrar os lançamentos no histórico.\n"
            "3. Acumular o 'Valor a Pagar' em 'Valores Pagos'.\n"
            "4. Limpar a tela para iniciar o próximo ciclo de medição.\n\n"
            "PCs com saldo em aberto poderão ser relançados informando os valores já pagos.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirmacao != QMessageBox.Yes:
            return

        nome_sugerido = f"MEDICAO_CONSOLIDADA_{proj.replace(' ', '_')}.xlsx"
        caminho_arquivo, _ = QFileDialog.getSaveFileName(
            self,
            f"Salvar Fechamento da Medição - {proj}",
            nome_sugerido,
            "Arquivo Excel (*.xlsx)"
        )

        if caminho_arquivo:
            sucesso = database.fechar_e_consolidar_medicao(caminho_arquivo, nome_projeto=proj)
            if sucesso:
                QMessageBox.information(
                    self, 
                    "Medição Encerrada", 
                    f"A medição do projeto '{proj}' foi consolidada com sucesso!\n\n"
                    f"Planilha salva em:\n{caminho_arquivo}\n\n"
                    "A tela de lançamentos foi limpa para o próximo ciclo.",
                )
                self.carregar_dados_tabela()
            else:
                QMessageBox.critical(
                    self, 
                    "Erro no Fechamento", 
                    "Ocorreu um erro ao tentar fechar a medição. Nenhum dado do banco foi alterado."
                )

    def limpar_medicao_projeto(self):
        proj = self.projeto_atual()

        primeiro_alerta = QMessageBox.warning(
            self,
            "⚠️ ATENÇÃO: Limpar Lançamentos",
            f"Você está prestes a EXCLUIR TODOS OS LANÇAMENTOS do projeto '{proj}'.\n\n"
            "Os cadastros de fornecedores serão mantidos intactos.\n"
            "Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if primeiro_alerta != QMessageBox.Yes:
            return

        segundo_alerta = QMessageBox.question(
            self,
            "Confirmação Explicita",
            f"Esta operação NÃO PODERÁ SER DESFEITA.\n\n"
            f"Confirma a exclusão definitiva de todos os registros do projeto '{proj}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if segundo_alerta == QMessageBox.Yes:
            sucesso = database.limpar_lancamentos_projeto(nome_projeto=proj)
            if sucesso:
                QMessageBox.information(
                    self, 
                    "Lançamentos Removidos", 
                    f"Todos os lançamentos do projeto '{proj}' foram limpos com sucesso!"
                )
                self.carregar_dados_tabela()
            else:
                QMessageBox.critical(
                    self, 
                    "Erro ao Limpar", 
                    "Não foi possível remover os lançamentos do banco de dados."
                )