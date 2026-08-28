import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFrame, QApplication, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer
import database
import utils

class TelaHistorico(QWidget):
    def __init__(self):
        super().__init__()
        self.medicao_selecionada = None
        self.dados_histórico = []
        self.init_ui()
        self.carregar_projetos_combo()
        self.carregar_dados_iniciais()
    
    def init_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)
        
        # Stacked widget para alternar entre lista e visualização
        self.stacked = QStackedWidget()
        
        # --- TELA 1: LISTA DE MEDIÇÕES ---
        tela_lista = QWidget()
        layout_lista = QVBoxLayout(tela_lista)
        layout_lista.setContentsMargins(0, 0, 0, 0)
        
        # Filtros
        frame_filtros = QFrame()
        frame_filtros.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 10px;
                padding: 15px;
            }
            QLabel {
                color: #f8fafc;
                font-weight: bold;
            }
            QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
                min-width: 150px;
            }
        """)
        layout_filtros = QHBoxLayout(frame_filtros)
        
        lbl_projeto = QLabel("Projeto:")
        self.combo_projeto = QComboBox()
        self.combo_projeto.currentIndexChanged.connect(self.carregar_historico)
        
        lbl_mes = QLabel("Mês:")
        self.combo_mes = QComboBox()
        self.combo_mes.addItem("Todos")
        self.combo_mes.currentIndexChanged.connect(self.carregar_historico)

        lbl_tipo = QLabel("Tipo:")
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItem("Todos", None)
        for key, label in database.TIPOS_CICLO.items():
            self.combo_tipo.addItem(label, key)
        self.combo_tipo.currentIndexChanged.connect(self.carregar_historico)
        
        layout_filtros.addWidget(lbl_projeto)
        layout_filtros.addWidget(self.combo_projeto)
        layout_filtros.addSpacing(16)
        layout_filtros.addWidget(lbl_mes)
        layout_filtros.addWidget(self.combo_mes)
        layout_filtros.addSpacing(16)
        layout_filtros.addWidget(lbl_tipo)
        layout_filtros.addWidget(self.combo_tipo)
        layout_filtros.addStretch()
        
        layout_lista.addWidget(frame_filtros)
        
        # Lista de medições
        self.lista_medicoes = QTableWidget()
        self.lista_medicoes.setColumnCount(3)
        self.lista_medicoes.setHorizontalHeaderLabels(["Fechamento", "Total", "Qtd. PCs"])
        self.lista_medicoes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lista_medicoes.setEditTriggers(QTableWidget.NoEditTriggers)
        self.lista_medicoes.setSelectionBehavior(QTableWidget.SelectRows)
        self.lista_medicoes.doubleClicked.connect(self.abrir_visualizacao)
        self.lista_medicoes.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #334155;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #1e293b;
            }
            QTableWidget::item:hover {
                background-color: #334155;
            }
            QTableWidget::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
        """)
        self.lista_medicoes.verticalHeader().setVisible(False)
        
        layout_lista.addWidget(self.lista_medicoes)
        
        # --- TELA 2: VISUALIZAÇÃO READ-ONLY ---
        tela_visualizacao = QWidget()
        layout_visualizacao = QVBoxLayout(tela_visualizacao)
        layout_visualizacao.setContentsMargins(0, 0, 0, 0)
        
        # Botão voltar
        self.btn_voltar = QPushButton("← Voltar para lista")
        self.btn_voltar.setStyleSheet("""
            QPushButton {
                background-color: #475569;
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.btn_voltar.clicked.connect(self.voltar_para_lista)
        
        layout_visualizacao.addWidget(self.btn_voltar)

        self.lbl_titulo_medicao = QLabel("")
        self.lbl_titulo_medicao.setStyleSheet("color: #f8fafc; font-size: 16px; font-weight: bold; padding: 4px 0 8px 0;")
        layout_visualizacao.addWidget(self.lbl_titulo_medicao)
        
        # Cards da medição (copiados da tela de lançamentos)
        layout_cards = QHBoxLayout()
        self.card_mobilizacao = self.criar_card_visualizacao("Mobilização", "R$ 0,00", "#b45309")
        self.card_adiantamento = self.criar_card_visualizacao("Adiantamento", "R$ 0,00", "#1d4ed8")
        self.card_conclusao = self.criar_card_visualizacao("Conclusão", "R$ 0,00", "#6d28d9")
        
        layout_cards.addWidget(self.card_mobilizacao)
        layout_cards.addWidget(self.card_adiantamento)
        layout_cards.addWidget(self.card_conclusao)
        
        layout_visualizacao.addLayout(layout_cards)
        
        # Tabela de detalhes (idêntica à tela de lançamentos, somente leitura)
        self.tabela_detalhes = QTableWidget()
        utils.configurar_tabela_lancamentos(self.tabela_detalhes)
        
        layout_visualizacao.addWidget(self.tabela_detalhes)
        
        # Adiciona as telas ao stacked
        self.stacked.addWidget(tela_lista)          # Índice 0
        self.stacked.addWidget(tela_visualizacao)   # Índice 1
        
        layout_principal.addWidget(self.stacked)
    
    def criar_card_visualizacao(self, titulo, valor, cor):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {cor},
                    stop: 1 #0f172a
                );
                border-radius: 12px;
                border: 1px solid {cor};
                padding: 6px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)
        
        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        
        lbl_valor = QLabel(valor)
        lbl_valor.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: 800; background: transparent; border: none;")
        lbl_valor.setObjectName("valor_card")
        
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_valor)
        
        return frame
    
    def carregar_projetos_combo(self):
        self.combo_projeto.blockSignals(True)
        self.combo_projeto.clear()
        projetos = database.carregar_projetos()
        for p in projetos:
            self.combo_projeto.addItem(p)
        self.combo_projeto.blockSignals(False)
    
    def carregar_dados_iniciais(self):
        if self.combo_projeto.count() > 0:
            self.carregar_historico()
    
    def carregar_historico(self):
        projeto = self.combo_projeto.currentText()
        if not projeto:
            return
        
        mes = self.combo_mes.currentText()
        mes_ref = None if mes == "Todos" else mes
        
        # Atualiza lista de meses disponíveis
        meses = database.carregar_meses_com_historico(projeto)
        self.combo_mes.blockSignals(True)
        self.combo_mes.clear()
        self.combo_mes.addItem("Todos")
        for m in meses:
            self.combo_mes.addItem(m)
        if mes_ref and mes_ref in meses:
            index = self.combo_mes.findText(mes_ref)
            if index >= 0:
                self.combo_mes.setCurrentIndex(index)
        self.combo_mes.blockSignals(False)
        
        tipo_filtro = self.combo_tipo.currentData()

        # Carrega medições
        dados = database.carregar_historico_medicoes(projeto, mes_ref, tipo_ciclo=tipo_filtro)
        self.dados_histórico = dados
        
        self.lista_medicoes.setRowCount(0)
        for row_idx, item in enumerate(dados):
            self.lista_medicoes.insertRow(row_idx)
            rotulo = database.rotulo_tipo_ciclo(item.get("tipo_ciclo"))
            self.lista_medicoes.setItem(
                row_idx, 0,
                QTableWidgetItem(f"📅 {rotulo} — {item['data_fechamento']}")
            )
            self.lista_medicoes.setItem(row_idx, 1, QTableWidgetItem(utils.float_para_moeda(item['total_pago'])))
            self.lista_medicoes.setItem(row_idx, 2, QTableWidgetItem(str(item['quantidade_pcs'])))
    
    def abrir_visualizacao(self):
        row = self.lista_medicoes.currentRow()
        if row < 0 or row >= len(self.dados_histórico):
            return
        
        item = self.dados_histórico[row]
        data_fechamento = item['data_fechamento']
        tipo_ciclo = item.get("tipo_ciclo") or "NOVA_MEDICAO"
        rotulo = database.rotulo_tipo_ciclo(tipo_ciclo)
        projeto = self.combo_projeto.currentText()

        self.lbl_titulo_medicao.setText(
            f"{rotulo} fechada em {data_fechamento} — {projeto} "
            f"({utils.float_para_moeda(item.get('total_pago', 0))} neste ciclo)"
        )
        
        # Carrega detalhes
        detalhes = database.carregar_detalhes_medicao(
            data_fechamento, projeto, tipo_ciclo=tipo_ciclo
        )
        
        # Atualiza cards (baseado no Valor a Pagar do ciclo fechado)
        total_mob = sum(
            utils.str_para_float(d.get("VALOR A PAGAR", 0))
            for d in detalhes
            if "MOBILIZA" in utils.limpar_texto(d.get("STATUS PC", "")).upper()
        )
        total_adi = sum(
            utils.str_para_float(d.get("VALOR A PAGAR", 0))
            for d in detalhes
            if "ADIANT" in utils.limpar_texto(d.get("STATUS PC", "")).upper()
        )
        total_conc = sum(
            utils.str_para_float(d.get("VALOR A PAGAR", 0))
            for d in detalhes
            if "CONCLU" in utils.limpar_texto(d.get("STATUS PC", "")).upper()
        )
        
        # Atualiza os labels dos cards
        for card in [self.card_mobilizacao, self.card_adiantamento, self.card_conclusao]:
            for child in card.findChildren(QLabel):
                if child.objectName() == "valor_card":
                    if card == self.card_mobilizacao:
                        child.setText(utils.float_para_moeda(total_mob))
                    elif card == self.card_adiantamento:
                        child.setText(utils.float_para_moeda(total_adi))
                    elif card == self.card_conclusao:
                        child.setText(utils.float_para_moeda(total_conc))
        
        utils.preencher_tabela_lancamentos(self.tabela_detalhes, detalhes)
        
        self.stacked.setCurrentIndex(1)
    
    def voltar_para_lista(self):
        self.stacked.setCurrentIndex(0)
        self.carregar_historico()