import re

# Colunas padronizadas de lançamento (usadas em Lançamentos, Histórico e Estatísticas)
CHAVES_LANCAMENTO = [
    "PC", "PRESTADOR", "ATIVIDADE/SERVIÇO", "VALOR TOTAL DO PC", "VALOR LIQUIDO",
    "VALORES PAGOS", "SALDO A PAGAR", "VALOR A PAGAR", "SALDO EM ABERTO",
    "STATUS PC", "OC", "END ID", "NOTA FISCAL", "REGIONAL"
]

HEADERS_LANCAMENTO = [
    "PC", "Prestador", "Atividade", "Valor Total", "Valor Líquido",
    "Valores Pagos", "Saldo a Pagar", "Valor a Pagar", "Saldo Aberto",
    "Status", "OC", "END ID", "NF", "Regional"
]

COLS_FINANCEIRAS = {3, 4, 5, 6, 7, 8}

ESTILO_TABELA_LANCAMENTOS = """
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
"""


def preencher_tabela_lancamentos(tabela, dados):
    """Preenche uma QTableWidget com as 14 colunas padrão de lançamento."""
    from PySide6.QtWidgets import QTableWidgetItem
    from PySide6.QtCore import Qt

    tabela.setUpdatesEnabled(False)
    tabela.setRowCount(0)
    for i, row_data in enumerate(dados):
        tabela.insertRow(i)
        for j, chave in enumerate(CHAVES_LANCAMENTO):
            val = row_data.get(chave, "")
            if j in COLS_FINANCEIRAS:
                texto = float_para_moeda(val)
            else:
                texto = limpar_texto(val)
            item = QTableWidgetItem(texto)
            if j in COLS_FINANCEIRAS:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tabela.setItem(i, j, item)
    tabela.setUpdatesEnabled(True)


def configurar_tabela_lancamentos(tabela):
    """Aplica cabeçalhos e estilo padrão de tabela de lançamentos."""
    from PySide6.QtWidgets import QHeaderView, QTableWidget

    tabela.setColumnCount(len(HEADERS_LANCAMENTO))
    tabela.setHorizontalHeaderLabels(HEADERS_LANCAMENTO)
    tabela.setWordWrap(True)
    tabela.setEditTriggers(QTableWidget.NoEditTriggers)
    tabela.setAlternatingRowColors(False)
    tabela.setShowGrid(False)
    tabela.setCornerButtonEnabled(False)
    tabela.verticalHeader().setVisible(False)
    tabela.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    tabela.setStyleSheet(ESTILO_TABELA_LANCAMENTOS)
    tabela.setColumnWidth(0, 110)
    tabela.setColumnWidth(1, 160)
    tabela.setColumnWidth(2, 280)


'''def calcular_valor_porcentagem(percentual: float, valor_total: float, valores_pagos: float = 0.0) -> float:
    """Calcula percentual sobre o saldo a pagar (total - já pago), não sobre o total bruto."""
    if percentual <= 0:
        return 0.0
    saldo_base = max(0.0, valor_total)
    return (percentual / 100.0) * saldo_base
'''

def str_para_float(texto) -> float:
    """
    Converte qualquer entrada de texto (ex: 'R$ 1.000,50', '1000,50', '1.000,50', '1000.5')
    para float puro do Python.
    """
    if texto is None:
        return 0.0
    
    texto_str = str(texto).strip()
    if not texto_str or texto_str.lower() in ("nan", "none"):
        return 0.0

    # Remove R$, espaços e símbolos indesejados mantendo apenas dígitos, vírgula, ponto e sinal negativo
    limpo = re.sub(r'[^\d,.-]', '', texto_str)

    # Se contiver vírgula e ponto (ex: 1.000,50), remove o ponto de milhar e substitui a vírgula por ponto
    if ',' in limpo and '.' in limpo:
        limpo = limpo.replace('.', '').replace(',', '.')
    # Se contiver apenas vírgula (ex: 1000,50)
    elif ',' in limpo:
        limpo = limpo.replace(',', '.')

    try:
        return float(limpo)
    except (ValueError, TypeError):
        return 0.0

def float_para_moeda(valor) -> str:
    """
    Converte um número float para formato de moeda brasileira (ex: R$ 1.000,50).
    """
    try:
        val_float = float(valor) if valor is not None else 0.0
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

def float_para_str_br(valor) -> str:
    """
    Converte um número float para string decimal brasileira sem o prefixo R$ (ex: 1000,50).
    """
    try:
        val_float = float(valor) if valor is not None else 0.0
        return f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0,00"

def limpar_texto(texto) -> str:
    """
    Garante que o retorno seja uma string limpa sem espaços nas pontas e trata nulos.
    """
    if texto is None:
        return ""
    txt = str(texto).strip()
    return "" if txt.lower() in ("nan", "none") else txt