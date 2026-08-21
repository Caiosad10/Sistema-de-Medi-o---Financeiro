import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QFrame, QApplication
)
from PySide6.QtCore import Qt
import database  # Importando o arquivo que construímos!
from utils import str_para_float
from validators import validar_campo_preenchido, validar_valor_positivo


class TelaCadastro(QWidget):
    def __init__(self):
        super().__init__()
        # Variável de controle para saber se estamos criando um novo ou editando
        self.fornecedor_em_edicao_cnpj = None
        
        self.init_ui()
        self.carregar_dados_tabela()

    def init_ui(self):
        # Layout Principal
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)

        # --- CARD DO FORMULÁRIO (BENTO UI) ---
        card_form = QFrame()
        card_form.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 10px;
                padding: 15px;
            }
            QLineEdit, QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton#btn_limpar { background-color: #475569; }
            QPushButton#btn_limpar:hover { background-color: #334155; }
        """)
        
        layout_grid = QGridLayout(card_form)
        
        # Instanciando Campos
        self.txt_razao = QLineEdit(); self.txt_razao.setPlaceholderText("Razão Social *")
        self.txt_fantasia = QLineEdit(); self.txt_fantasia.setPlaceholderText("Razão Fantasia")
        self.txt_cnpj = QLineEdit(); self.txt_cnpj.setPlaceholderText("CNPJ / CPF *")
        
        self.txt_banco = QLineEdit(); self.txt_banco.setPlaceholderText("Banco")
        self.txt_agencia = QLineEdit(); self.txt_agencia.setPlaceholderText("Agência")
        self.txt_conta = QLineEdit(); self.txt_conta.setPlaceholderText("Conta")
        
        self.combo_tipo_pix = QComboBox()
        self.combo_tipo_pix.addItems(["CNPJ", "CPF", "E-MAIL", "Nº TELEFONE", "ALEATÓRIA"])
        self.txt_chave_pix = QLineEdit(); self.txt_chave_pix.setPlaceholderText("Chave PIX")

        # Adicionando ao Grid
        layout_grid.addWidget(self.txt_razao, 0, 0, 1, 2)
        layout_grid.addWidget(self.txt_fantasia, 0, 2)
        layout_grid.addWidget(self.txt_cnpj, 0, 3)
        
        layout_grid.addWidget(self.txt_banco, 1, 0)
        layout_grid.addWidget(self.txt_agencia, 1, 1)
        layout_grid.addWidget(self.txt_conta, 1, 2)
        layout_grid.addWidget(self.combo_tipo_pix, 1, 3)
        layout_grid.addWidget(self.txt_chave_pix, 1, 4)

        # Botões de Ação
        layout_botoes = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar Cadastro")
        self.btn_salvar.clicked.connect(self.salvar_registro)
        
        self.btn_limpar = QPushButton("Limpar Campos")
        self.btn_limpar.setObjectName("btn_limpar")
        self.btn_limpar.clicked.connect(self.limpar_campos)
        
        layout_botoes.addWidget(self.btn_salvar)
        layout_botoes.addWidget(self.btn_limpar)
        layout_grid.addLayout(layout_botoes, 2, 0, 1, 2)

        layout_principal.addWidget(card_form)

        # --- TABELA DE DADOS (TREEVIEW / QTABLEWIDGET) ---
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(8)
        self.tabela.setHorizontalHeaderLabels([
            "Razão Social", "Razão Fantasia", "CNPJ/CPF", "Banco", "Agência", "Conta", "Tipo PIX", "Chave PIX"
        ])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers) # Impede edição direta na célula, força o clique duplo
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.doubleClicked.connect(self.ao_clicar_duplo)
        
        # Estilo escuro para a tabela
        self.tabela.setStyleSheet("""
            QTableWidget { background-color: #0f172a; color: #f8fafc; border: 1px solid #334155; }
            QHeaderView::section { background-color: #1e293b; color: white; padding: 5px; border: 1px solid #334155; }
        """)

        layout_principal.addWidget(self.tabela)

    def exibir_alerta(self, titulo: str, mensagem: str):
        """Exibe modal de aviso estilizado com o tema Bento UI."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(titulo)
        msg.setText(mensagem)
        msg.setStyleSheet("""
            QMessageBox { background-color: #1e293b; color: #f8fafc; }
            QLabel { color: #f8fafc; }
            QPushButton { background-color: #3b82f6; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #2563eb; }
        """)
        msg.exec()


    def carregar_dados_tabela(self):
        """Puxa os dados do database.py e preenche a tabela"""
        fornecedores = database.carregar_fornecedores()
        self.tabela.setRowCount(0)
        
        for row_idx, f in enumerate(fornecedores):
            self.tabela.insertRow(row_idx)
            # Pega exatamente os 8 valores da nossa planilha
            valores = list(f.values())[:8]
            for col_idx, valor in enumerate(valores):
                # Se for NaN ou None, converte para string vazia
                val_str = str(valor) if valor not in [None, "nan"] else ""
                item = QTableWidgetItem(val_str)
                self.tabela.setItem(row_idx, col_idx, item)

    def ao_clicar_duplo(self):
        """Joga os dados da linha selecionada para os campos de texto"""
        row = self.tabela.currentRow()
        
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
        
        # Trava o CNPJ para saber quem estamos atualizando
        self.fornecedor_em_edicao_cnpj = self.tabela.item(row, 2).text()
        self.btn_salvar.setText("Atualizar Cadastro")

    def salvar_registro(self):
        """Aplica as validações de interface e salva no database.py"""
        razao = self.txt_razao.text().strip()
        cnpj = self.txt_cnpj.text().strip()

        # 1. Validação de Campos Obrigatórios
        if not razao:
            self.exibir_alerta("Campo Obrigatório", "O campo 'Razão Social' é obrigatório!")
            self.txt_razao.setFocus()
            return

        if not cnpj:
            self.exibir_alerta("Campo Obrigatório", "O campo 'CNPJ / CPF' é obrigatório!")
            self.txt_cnpj.setFocus()
            return

        # 2. Formatação e preparação da tupla de dados
        dados = [
            razao,
            self.txt_fantasia.text().strip(),
            cnpj,
            self.txt_banco.text().strip(),
            self.txt_agencia.text().strip(),
            self.txt_conta.text().strip(),
            self.combo_tipo_pix.currentText(),
            self.txt_chave_pix.text().strip()
        ]

        # 3. Persistência
        if self.fornecedor_em_edicao_cnpj:
            sucesso = database.atualizar_fornecedor(self.fornecedor_em_edicao_cnpj, dados)
            msg = "Fornecedor atualizado com sucesso!"
        else:
            sucesso = database.adicionar_fornecedor(dados)
            msg = "Novo fornecedor cadastrado!"
            
        if sucesso:
            QMessageBox.information(self, "Sucesso", msg)
            self.limpar_campos()
            self.carregar_dados_tabela()
        else:
            QMessageBox.critical(self, "Erro", "Houve um problema ao salvar os dados no sistema.")

    def limpar_campos(self):
        """Reseta o formulário"""
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

# Apenas para testar o arquivo isoladamente
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TelaCadastro()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec())