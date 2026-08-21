import os
import sys

def get_base_path():
    """Retorna o caminho base do aplicativo (funciona para .exe e .py)"""
    if getattr(sys, 'frozen', False):
        # Estamos rodando como executável
        return os.path.dirname(sys.executable)
    else:
        # Estamos rodando como script Python
        return os.path.dirname(os.path.abspath(__file__))

def get_data_path():
    """Retorna o caminho onde os dados (banco, templates) devem ser armazenados"""
    base_path = get_base_path()
    
    # Em produção, usamos a pasta do executável ou uma subpasta 'data'
    if getattr(sys, 'frozen', False):
        data_path = os.path.join(base_path, 'data')
    else:
        data_path = base_path
    
    # Cria a pasta se não existir
    os.makedirs(data_path, exist_ok=True)
    return data_path

def get_resource_path(relative_path):
    """Retorna o caminho para recursos (templates, etc) - funciona .exe e .py"""
    if getattr(sys, 'frozen', False):
        # PyInstaller cria uma pasta temporária para os arquivos empacotados
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)