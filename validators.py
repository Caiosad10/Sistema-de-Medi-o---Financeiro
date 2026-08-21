from datetime import datetime
from PySide6.QtWidgets import QLineEdit, QComboBox, QMessageBox

def exibir_alerta(parent, titulo: str, mensagem: str):
    """Exibe um modal de erro padronizado para o usuário."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(titulo)
    msg.setText(mensagem)
    msg.setStyleSheet("""
        QMessageBox {
            background-color: #1e293b;
            color: #f8fafc;
        }
        QLabel {
            color: #f8fafc;
        }
        QPushButton {
            background-color: #3b82f6;
            color: white;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2563eb;
        }
    """)
    msg.exec()

def validar_campo_preenchido(campo: QLineEdit, nome_campo: str, parent=None) -> bool:
    """Verifica se um campo de texto não está vazio."""
    texto = campo.text().strip()
    if not texto:
        exibir_alerta(parent, "Campo Obrigatório", f"O campo '{nome_campo}' precisa ser preenchido.")
        campo.setFocus()
        return False
    return True

def validar_selecao_combo(combo: QComboBox, nome_campo: str, parent=None) -> bool:
    """Verifica se uma opção válida foi selecionada no ComboBox."""
    if combo.currentIndex() < 0 or combo.currentData() is None:
        exibir_alerta(parent, "Seleção Inválida", f"Selecione uma opção válida para '{nome_campo}'.")
        combo.setFocus()
        return False
    return True

def validar_valor_positivo(valor_float: float, nome_campo: str, parent=None) -> bool:
    """Garante que o valor numérico é estritamente maior que zero."""
    if valor_float <= 0:
        exibir_alerta(parent, "Valor Inválido", f"O campo '{nome_campo}' deve ter um valor maior que zero.")
        return False
    return True

def validar_limite_saldo(valor_medido: float, saldo_disponivel: float, parent=None) -> bool:
    """Garante que o valor inserido não ultrapassa o saldo restante do contrato/item."""
    if valor_medido > saldo_disponivel:
        exibir_alerta(
            parent, 
            "Saldo Excedido", 
            f"O valor medido (R$ {valor_medido:,.2f}) ultrapassa o saldo disponível (R$ {saldo_disponivel:,.2f})."
        )
        return False
    return True