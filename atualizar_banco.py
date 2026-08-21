import sqlite3
import os
from paths import get_data_path
from database import _migrar_banco, inicializar_banco

DB_NAME = os.path.join(get_data_path(), "medicao.db")

def atualizar_banco():
    """Executa migrações pendentes no banco de dados."""
    inicializar_banco()
    print(f"Banco atualizado com sucesso em: {DB_NAME}")

if __name__ == "__main__":
    atualizar_banco()
