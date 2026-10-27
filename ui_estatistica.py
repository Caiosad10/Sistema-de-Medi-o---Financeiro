import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFrame, QApplication, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
import database
import utils

class TelaEstatisticas(QWidget):
    def __init__(self):
        super().__init__()
        self.prestador_selecionado = None
        self.init_ui()
        self._registrar_atalhos()
        self.carregar_projetos_combo()
        self.carregar_dados()
    
    def init_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)
        
        # Stacked para alternar entre resumo e detalhes do prestador
        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("background: transparent;")
        
        # --- TELA 1: RESUMO ---
        tela_resumo = QWidget()
        layout_resumo = QVBoxLayout(tela_resumo)
        layout_resumo.setContentsMargins(0, 0, 0, 0)
        
        # Filtros
        frame_filtros = QFrame()
        frame_filtros.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 90);
                border: 1px solid rgba(148, 163, 184, 40);
                border-radius: 16px;
                padding: 10px;
            }
            QLabel {
                color: #e2e8f0;
                font-weight: 700;
                background: transparent;
            }
            QComboBox {
                background-color: rgba(15, 23, 42, 210);
                color: #f8fafc;
                border: 1px solid rgba(148, 163, 184, 70);
                border-radius: 10px;
                padding: 8px 12px;
                min-width: 150px;
            }
            QComboBox:hover {
                border: 1px solid rgba(96, 165, 250, 180);
            }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #f8fafc;
                selection-background-color: #6366f1;
                border: 1px solid #334155;
            }

        """)
        layout_filtros = QHBoxLayout(frame_filtros)
        
        lbl_projeto = QLabel("Projeto:")
        self.combo_projeto = QComboBox()
        self.combo_projeto.currentIndexChanged.connect(self.carregar_dados)

        lbl_tipo = QLabel("Tipo:")
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItem("Todos (saldo atual)", None)
        for key, label in database.TIPOS_CICLO.items():
            self.combo_tipo.addItem(label, key)
        self.combo_tipo.currentIndexChanged.connect(self.carregar_dados)
        
        layout_filtros.addWidget(lbl_projeto)
        layout_filtros.addWidget(self.combo_projeto)
        layout_filtros.addSpacing(16)
        layout_filtros.addWidget(lbl_tipo)
        layout_filtros.addWidget(self.combo_tipo)
        layout_filtros.addStretch()
        
        layout_resumo.addWidget(frame_filtros)
        
        # Cards de totais
        layout_cards = QHBoxLayout()
        layout_cards.setSpacing(14)
        self.card_total = self.criar_card_estatistica("💰 TOTAL DO PROJETO", "R$ 0,00", "rgba(109, 93, 211, 200)")
        self.card_pago = self.criar_card_estatistica("✅ TOTAL PAGO", "R$ 0,00", "rgba(16, 185, 129, 200)")
        self.card_saldo = self.criar_card_estatistica("⏳ SALDO EM ABERTO", "R$ 0,00", "rgba(245, 158, 11, 200)")
        
        layout_cards.addWidget(self.card_total)
        layout_cards.addWidget(self.card_pago)
        layout_cards.addWidget(self.card_saldo)
        
        layout_resumo.addLayout(layout_cards)
        
        # Filtro de prestador (fora da tabela para não sobrepor o cabeçalho)
        frame_filtro_prestador = QFrame()
        frame_filtro_prestador.setObjectName("frame_filtro_prestador")
        frame_filtro_prestador.setStyleSheet("""
            QFrame#frame_filtro_prestador {
                background-color: rgba(15, 23, 42, 90);
                border: 1px solid rgba(148, 163, 184, 40);
                border-radius: 16px;
            }
            QFrame#frame_filtro_prestador QLabel {
                color: #e2e8f0;
                font-weight: 700;
                background: transparent;
            }
            QFrame#frame_filtro_prestador QComboBox {
                background-color: rgba(15, 23, 42, 210);
                color: #f8fafc;
                border: 1px solid rgba(148, 163, 184, 70);
                border-radius: 10px;
                padding: 8px 12px;
                min-width: 150px;
            }
            QFrame#frame_filtro_prestador QComboBox:hover {
                border: 1px solid rgba(96, 165, 250, 180);
            }
        """)
        layout_filtro_prestador = QHBoxLayout(frame_filtro_prestador)
        layout_filtro_prestador.setContentsMargins(15, 12, 15, 12)

        lbl_prestador = QLabel("👤 Resumo por Prestador - Filtro:")
        self.combo_prestador = QComboBox()
        self.combo_prestador.addItem("Todos")
        self.combo_prestador.currentIndexChanged.connect(self.carregar_dados)

        layout_filtro_prestador.addWidget(lbl_prestador)
        layout_filtro_prestador.addWidget(self.combo_prestador)
        layout_filtro_prestador.addStretch()

        layout_resumo.addWidget(frame_filtro_prestador)

        self.tabela_prestadores = QTableWidget()
        self.tabela_prestadores.setColumnCount(4)
        self.tabela_prestadores.setHorizontalHeaderLabels(["Prestador", "Valores Pagos", "Saldo em Aberto", "Total"])
        self.tabela_prestadores.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela_prestadores.horizontalHeader().setMinimumHeight(42)
        self.tabela_prestadores.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tabela_prestadores.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela_prestadores.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_prestadores.doubleClicked.connect(self.abrir_detalhes_prestador)
        self.tabela_prestadores.setStyleSheet("""
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
            QHeaderView::section {
                background-color: rgba(15, 23, 42, 200);
                color: #94a3b8;
                font-weight: 700;
                font-size: 11px;
                padding: 12px 10px;
                border: none;
                border-bottom: 1px solid rgba(148, 163, 184, 50);
            }
            QTableWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid rgba(148, 163, 184, 22);
            }
            QTableWidget::item:hover {
                background-color: rgba(51, 65, 85, 120);
            }
            QTableWidget::item:selected {
                background-color: rgba(99, 102, 241, 180);
                color: #ffffff;
            }

        """)
        self.tabela_prestadores.verticalHeader().setVisible(False)

        layout_resumo.addWidget(self.tabela_prestadores)
        
        # --- TELA 2: DETALHES DO PRESTADOR ---
        tela_detalhes = QWidget()
        layout_detalhes = QVBoxLayout(tela_detalhes)
        layout_detalhes.setContentsMargins(0, 0, 0, 0)
        
        self.btn_voltar_detalhes = QPushButton("← Voltar para resumo")
        self.btn_voltar_detalhes.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 23, 42, 140);
                color: #e2e8f0;
                font-weight: 700;
                font-size: 12px;
                border: 1px solid rgba(148, 163, 184, 55);
                border-radius: 12px;
                padding: 10px 18px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(51, 65, 85, 200);
                border: 1px solid rgba(147, 197, 253, 140);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(99, 102, 241, 160);
            }

        """)
        self.btn_voltar_detalhes.clicked.connect(self.voltar_para_resumo)
        
        layout_detalhes.addWidget(self.btn_voltar_detalhes)
        
        self.lbl_titulo_prestador = QLabel("Lançamentos - Prestador")
        self.lbl_titulo_prestador.setStyleSheet("color: #f8fafc; font-size: 18px; font-weight: bold; padding: 10px 0;")
        layout_detalhes.addWidget(self.lbl_titulo_prestador)
        
        self.tabela_lancamentos_prestador = QTableWidget()
        utils.configurar_tabela_lancamentos(self.tabela_lancamentos_prestador)
        
        layout_detalhes.addWidget(self.tabela_lancamentos_prestador)
        
        # Adiciona as telas ao stacked
        self.stacked.addWidget(tela_resumo)        # Índice 0
        self.stacked.addWidget(tela_detalhes)      # Índice 1
        
        layout_principal.addWidget(self.stacked)
    

    def _registrar_atalhos(self):
        sc = QShortcut(QKeySequence("Esc"), self)
        sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc.activated.connect(self._atalho_esc)

    def _atalho_esc(self):
        if self.stacked.currentIndex() == 1:
            self.voltar_para_resumo()

    def criar_card_estatistica(self, titulo, valor, cor):
        frame = QFrame()
        frame.setMinimumHeight(80)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {cor},
                    stop: 0.5 rgba(255, 255, 255, 22),
                    stop: 1 rgba(15, 23, 42, 120)
                );
                border-radius: 16px;
                border: 1px solid {cor};
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet(
            "color: #e2e8f0; font-size: 12px; font-weight: 700; "
            "letter-spacing: 0.4px; background: transparent; border: none;"
        )

        lbl_valor = QLabel(valor)
        lbl_valor.setStyleSheet(
            "color: #ffffff; font-size: 20px; font-weight: 800; "
            "background: transparent; border: none;"
        )
        lbl_valor.setObjectName("valor_card_est")

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
    
    def carregar_dados(self):
        projeto = self.combo_projeto.currentText()
        if not projeto:
            return
        
        prestador_filtro = self.combo_prestador.currentText()
        if prestador_filtro == "Todos":
            prestador_filtro = None

        tipo_filtro = self.combo_tipo.currentData()

        if tipo_filtro:
            # Filtro por tipo → dados do histórico (pagamentos já fechados daquele tipo)
            dados = database.carregar_estatisticas_por_tipo(
                projeto, tipo_ciclo=tipo_filtro, prestador_filtro=prestador_filtro
            )
            totais = dados.get("totais", {})
            prestadores = dados.get("prestadores", [])
            total_pago = totais.get("total_pago", 0)
            qtd = totais.get("quantidade_pcs", 0)
            fechamentos = totais.get("quantidade_fechamentos", 0)

            for card in [self.card_total, self.card_pago, self.card_saldo]:
                for child in card.findChildren(QLabel):
                    if child.objectName() == "valor_card_est":
                        if card == self.card_total:
                            child.setText(f"{fechamentos} fechamento(s)")
                        elif card == self.card_pago:
                            child.setText(utils.float_para_moeda(total_pago))
                        elif card == self.card_saldo:
                            child.setText(f"{qtd} PC(s)")

            # Ajusta títulos dos cards no modo tipo
            self._set_titulo_card(self.card_total, "📋 FECHAMENTOS")
            self._set_titulo_card(self.card_pago, "✅ TOTAL PAGO (HISTÓRICO)")
            self._set_titulo_card(self.card_saldo, "📦 QTD. PCs")
        else:
            # Todos → saldo atual do projeto (lançamentos)
            dados = database.carregar_estatisticas_projeto(projeto, prestador_filtro)
            totais = dados.get("totais", {})
            prestadores = dados.get("prestadores", [])

            for card in [self.card_total, self.card_pago, self.card_saldo]:
                for child in card.findChildren(QLabel):
                    if child.objectName() == "valor_card_est":
                        if card == self.card_total:
                            child.setText(utils.float_para_moeda(totais.get("total_projeto", 0)))
                        elif card == self.card_pago:
                            child.setText(utils.float_para_moeda(totais.get("total_pago", 0)))
                        elif card == self.card_saldo:
                            child.setText(utils.float_para_moeda(totais.get("saldo_em_aberto", 0)))

            self._set_titulo_card(self.card_total, "💰 TOTAL DO PROJETO")
            self._set_titulo_card(self.card_pago, "✅ TOTAL PAGO")
            self._set_titulo_card(self.card_saldo, "⏳ SALDO EM ABERTO")
        
        # Atualiza combo de prestadores
        self.combo_prestador.blockSignals(True)
        self.combo_prestador.clear()
        self.combo_prestador.addItem("Todos")
        for p in prestadores:
            if p.get("prestador"):
                self.combo_prestador.addItem(p["prestador"])
        if prestador_filtro and self.combo_prestador.findText(prestador_filtro) >= 0:
            self.combo_prestador.setCurrentText(prestador_filtro)
        self.combo_prestador.blockSignals(False)
        
        # Preenche tabela
        self.tabela_prestadores.setRowCount(0)
        for row_idx, p in enumerate(prestadores):
            self.tabela_prestadores.insertRow(row_idx)
            self.tabela_prestadores.setItem(row_idx, 0, QTableWidgetItem(p.get("prestador", "")))
            self.tabela_prestadores.setItem(row_idx, 1, QTableWidgetItem(utils.float_para_moeda(p.get("pago", 0))))
            if tipo_filtro:
                # No modo histórico por tipo não há "saldo em aberto" por prestador
                self.tabela_prestadores.setItem(
                    row_idx, 2, QTableWidgetItem(str(p.get("qtd_pcs", 0)))
                )
                self.tabela_prestadores.setItem(
                    row_idx, 3, QTableWidgetItem(utils.float_para_moeda(p.get("pago", 0)))
                )
            else:
                self.tabela_prestadores.setItem(
                    row_idx, 2, QTableWidgetItem(utils.float_para_moeda(p.get("saldo", 0)))
                )
                self.tabela_prestadores.setItem(
                    row_idx, 3, QTableWidgetItem(utils.float_para_moeda(p.get("total", 0)))
                )

    def _set_titulo_card(self, card, texto):
        for child in card.findChildren(QLabel):
            if child.objectName() != "valor_card_est":
                # título do card (primeiro label sem objectName de valor)
                if "valor" not in (child.objectName() or "").lower():
                    child.setText(texto)
                    break
    
    def abrir_detalhes_prestador(self):
        row = self.tabela_prestadores.currentRow()
        if row < 0:
            return

        prestador = self.tabela_prestadores.item(row, 0).text()
        if not prestador:
            return

        projeto = self.combo_projeto.currentText()
        tipo_filtro = self.combo_tipo.currentData()

        # Tipo específico → histórico fechado; "Todos" → lançamentos abertos atuais
        if tipo_filtro:
            lancamentos = database.carregar_historico_prestador(
                projeto, prestador, tipo_ciclo=tipo_filtro
            )
            self.lbl_titulo_prestador.setText(
                f"Histórico - {prestador} - {projeto} ({database.rotulo_tipo_ciclo(tipo_filtro)})"
            )
        else:
            lancamentos = database.carregar_lancamentos_prestador(projeto, prestador)
            self.lbl_titulo_prestador.setText(f"Lançamentos - {prestador} - {projeto}")

        utils.preencher_tabela_lancamentos(self.tabela_lancamentos_prestador, lancamentos)
        self.stacked.setCurrentIndex(1)
    
    def voltar_para_resumo(self):
        self.stacked.setCurrentIndex(0)
        self.carregar_dados()