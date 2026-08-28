# Gerenciador de Medições (SisMed)

Sistema desktop para **gestão de medições, lançamentos financeiros e pagamentos por projeto**, com histórico, estatísticas e exportação Excel.

Este README descreve a arquitetura real do projeto e serve como **base reutilizável** para criar outros sistemas no mesmo estilo (cadastro + lançamentos + fechamento de ciclo + histórico).

---

## Índice

1. [Visão geral](#1-visão-geral)
2. [Stack e requisitos](#2-stack-e-requisitos)
3. [Estrutura de pastas](#3-estrutura-de-pastas)
4. [Arquitetura](#4-arquitetura)
5. [Modelo de dados](#5-modelo-de-dados)
6. [Módulos da interface](#6-módulos-da-interface)
7. [Fluxos de negócio](#7-fluxos-de-negócio)
8. [Padrões que valem a pena copiar](#8-padrões-que-valem-a-pena-copiar)
9. [Como rodar em desenvolvimento](#9-como-rodar-em-desenvolvimento)
10. [Build do executável](#10-build-do-executável)
11. [Migração e compatibilidade de banco](#11-migração-e-compatibilidade-de-banco)
12. [Como adaptar esta base para outro sistema](#12-como-adaptar-esta-base-para-outro-sistema)
13. [Checklist de novo projeto](#13-checklist-de-novo-projeto)

---

## 1. Visão geral

### O que o sistema faz

| Área | Função |
|------|--------|
| **Cadastros** | Prestadores/fornecedores (dados bancários, PIX) |
| **Lançamentos** | Lançamentos por projeto e por **ciclo (aba)** |
| **Abas de ciclo** | Várias medições em paralelo no mesmo projeto (medição semanal, saldos finais, emergencial) |
| **Fechamento** | Exporta planilha, grava histórico, acumula valores pagos, fecha a aba |
| **Histórico** | Medições fechadas, filtro por mês e tipo |
| **Estatísticas** | Totais do projeto e por prestador; filtro por tipo no histórico |

### Princípios de desenho

- **Desktop offline**: SQLite local, sem servidor.
- **UI em camadas**: `main` só navega; cada tela é um módulo; `database` concentra persistência.
- **Ciclos paralelos**: um projeto pode ter várias abas abertas sem copiar a pasta do sistema.
- **Fechamento seguro**: se a exportação Excel falhar, o banco **não** é alterado.
- **Mensagens de erro orientativas**: o usuário recebe o *quê* e o *como verificar*, não só “erro”.
- **Executável + dados**: paths distintos para código empacotado e pasta de dados.

---

## 2. Stack e requisitos

```
Python 3.10+
PySide6 >= 6.4.0      # UI (Qt for Python)
openpyxl >= 3.1.0     # Excel (template + exportação)
sqlite3               # built-in
PyInstaller           # build (dev/deploy)
```

Arquivo `requirements.txt`:

```
PySide6>=6.4.0
openpyxl>=3.1.0
```

Tema visual: dark “Bento UI” (slate + azul), CSS embutido nos widgets — sem QSS externo obrigatório.

---

## 3. Estrutura de pastas

```
GerenciadorMedição - MASTER/
├── main.py                 # Janela principal, sidebar, stack de telas
├── database.py             # SQLite, migrações, regras de persistência
├── paths.py                # Caminhos .py vs .exe (dados e recursos)
├── utils.py                # Formatação moeda, texto, tabelas
├── validators.py           # Validações auxiliares
│
├── ui_cadastro.py           # Tela de fornecedores
├── ui_lancamentos.py        # Lançamentos + abas de ciclo + formulário
├── ui_medicoes_fechadas.py  # Container Histórico | Estatísticas
├── ui_historico.py          # Lista e detalhe de medições fechadas
├── ui_estatistica.py        # Cards e resumo por prestador
│
├── medicao.db               # Banco local (gerado/atualizado em runtime)
├── TEMPLATE_*.xlsx          # Modelo de planilha de exportação
├── PROJETO_*_DADOS.xlsx     # Dados iniciais (só em instalação virgem)
│
├── build.spec               # PyInstaller
├── build_app.ps1            # Script de build (Windows)
└── README.md
```

**Regra de ouro:** UI não fala SQL; `database.py` não monta widget. `utils.py` não conhece regra de negócio.

---

## 4. Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│  main.py                                                │
│  Sidebar → QStackedWidget → Telas                       │
│  Ao trocar de tela: recarrega dados da tela ativa       │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
    ┌────────▼────────┐          ┌────────▼────────┐
    │  ui_*.py        │          │  ui_*.py        │
    │  Formulários    │          │  Tabelas/Cards  │
    │  Validação UI   │          │  Filtros        │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             └────────────┬───────────────┘
                          │
                 ┌────────▼────────┐
                 │  database.py    │
                 │  CRUD + migração│
                 │  export Excel   │
                 │  (ok, msg_erro) │
                 └────────┬────────┘
                          │
                 ┌────────▼────────┐
                 │  SQLite         │
                 │  medicao.db     │
                 └─────────────────┘
```

### Responsabilidades

| Camada | Responsabilidade | Não faz |
|--------|------------------|---------|
| `main` | Shell, navegação, refresh ao entrar na tela | Regra de medição |
| `ui_*` | Captura, validação de formulário, feedback | SQL cru |
| `database` | Persistência, migração, export, mensagens de erro de I/O | Layout |
| `paths` | Onde está o `.db` e os templates no `.exe` | Negócio |
| `utils` | `str_para_float`, `float_para_moeda`, preencher tabela | Persistência |

### Contrato de erro (recomendado)

Funções sensíveis de escrita retornam:

```python
(sucesso: bool, mensagem_erro: str)  # mensagem vazia se ok
```

A UI mostra `mensagem_erro` no `QMessageBox`, com orientações do tipo “verifique se o arquivo não está aberto no Excel”.

---

## 5. Modelo de dados

### Tabelas principais

```
projetos
  id, nome (UNIQUE)

fornecedores
  id, razao_social (UNIQUE), razao_fantasia, cnpj_cpf (UNIQUE),
  banco, agencia, conta, tipo_pix, chave_pix

ciclos                          # “abas” de medição abertas/fechadas
  id, projeto_id, titulo, tipo, aberto (0|1), data_criacao, ordem

lancamentos
  id, projeto_id, ciclo_id, pc, prestador, atividade,
  valor_total, valor_liquido, valores_pagos, saldo_a_pagar,
  valor_a_pagar, saldo_aberto, status_pc, oc, end_id, nota_fiscal, regional

historico_medicoes              # snapshot no fechamento
  …mesmos campos de valor + data_fechamento, mes_referencia,
  valor_medido, status, tipo_ciclo
```

### Tipos de ciclo (`tipo`)

| Código | Rótulo na UI |
|--------|----------------|
| `NOVA_MEDICAO` | Medição |
| `SALDOS_FINAIS` | Saldos Finais |
| `SOLICITACAO_EMERGENCIAL` | Solicitação Emergencial |

Limite configurável: `LIMITE_ABAS_POR_PROJETO = 8`.

### Ideia central: ciclo = aba

- Cada **aba** na tela de Lançamentos é um registro em `ciclos` com `aberto = 1`.
- Lançamentos da aba carregam com `WHERE ciclo_id = ?`.
- Fechar medição: exporta → histórico (com `tipo_ciclo`) → acumula `valores_pagos` → zera `valor_a_pagar` → `aberto = 0`.
- Excluir aba (menu de contexto): apaga lançamentos da aba **sem** histórico (ação destrutiva consciente).

### Instalação virgem vs banco já usado

```text
Se lançamentos == 0 E histórico == 0 E fornecedores == 0
    → importar planilha base (se existir)
Senão
    → NÃO reimportar (preserva banco de produção)
```

---

## 6. Módulos da interface

### Sidebar (`main.py`)

1. Cadastros  
2. Lançamentos  
3. Medições Fechadas (abas internas: Histórico | Estatísticas)

Ao entrar em Lançamentos / Medições Fechadas, a tela **recarrega** dados (evita estatística “velha”).

### Cadastros (`ui_cadastro.py`)

- CRUD de fornecedor.
- Duplicidade tratada **antes** do `INSERT` (razão social / CNPJ) com mensagem explícita.

### Lançamentos (`ui_lancamentos.py`)

- Seletor de **projeto** (global na tela).
- **Barra de abas** de ciclo + botão `+`.
- Cards de status (Mobilização / Adiantamento / Conclusão) sobre `valor_a_pagar`.
- Formulário: PC, prestador (combo editável + `QCompleter` com `MatchContains`), valores com rádio **R$ / %**.
- Na **edição**, reabre em **%** recalculado a partir do total (só UX; banco continua em R$).
- Ações: Novo, Exportar, Fechar Medição, Recomeçar (limpa aba atual).

### Histórico / Estatística

- Histórico: filtros projeto, mês, **tipo**; título do fechamento usa o rótulo do tipo.
- Estatística: “Todos” = saldo atual (`lancamentos`); tipo específico = agregados do **histórico**.

---

## 7. Fluxos de negócio

### Novo lançamento

1. Garante ciclo ativo (cria aba se o projeto estiver sem ciclo).  
2. Valida UI (PC, prestador, total > 0, regras de %).  
3. Converte % → R$ se necessário.  
4. `adicionar_lancamento` / `atualizar_lancamento` com `ciclo_id`.

### Fechar medição (aba atual)

1. Usuário escolhe caminho do `.xlsx`.  
2. `exportar_planilha_medicao` (template openpyxl). Se falhar → **aborta**, banco intacto.  
3. Copia linhas com `valor_a_pagar > 0` para `historico_medicoes` + `tipo_ciclo`.  
4. Atualiza saldos nos lançamentos daquele ciclo.  
5. `ciclos.aberto = 0`; UI remove a aba.

### Trabalhar em paralelo (motivo das abas)

Cenários reais cobertos:

- 4 medições semanais + 1 saldo final no mesmo mês.  
- Solicitação emergencial sem fechar a medição atual.  
- Mesmo projeto, várias abas; projeto é o contexto da barra de abas (não se mistura projeto por aba).

---

## 8. Padrões que valem a pena copiar

Use estes padrões em **qualquer** sistema derivado.

### 1. Paths dual (dev / exe)

```python
# paths.py
get_base_path()      # pasta do script ou do .exe
get_data_path()      # onde fica o .db (ex.: data/ no frozen)
get_resource_path()  # templates dentro do _MEIPASS no PyInstaller
```

### 2. Migração incremental

```python
CREATE TABLE IF NOT EXISTS ...
PRAGMA table_info(...)  # ADD COLUMN se faltar
# depois: backfill de FKs / flags
```

Nunca “drop and recreate” em produção.

### 3. Retorno `(bool, mensagem)`

Evita `print` só no console e alerta genérico na UI.

### 4. Tela “burra”, database “esperto”

Toda regra que mexe em saldo, histórico ou arquivo fica em `database.py`.

### 5. Refresh ao focar a tela

```python
def mudar_tela(self, indice):
    ...
    if indice == 1:
        self.tela_lancamentos.carregar_dados_tabela()
    elif indice == 2:
        self.tela_medicoes_fechadas.recarregar()
```

### 6. Completer em combo editável

`QComboBox.setEditable(True)` + `QCompleter` com `Qt.MatchContains` para busca tipo “Google” em listas longas.

### 7. Tema dark consistente

Paleta recorrente: `#0f172a`, `#1e293b`, `#334155`, `#3b82f6`, `#f8fafc`.  
Um estilo de card/botão copiado entre telas mantém identidade sem framework extra.

---

## 9. Como rodar em desenvolvimento

```bash
cd "GerenciadorMedição - MASTER"
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Na primeira execução:

- Cria `medicao.db` ao lado do script (modo não frozen).
- Se banco virgem, pode importar dados do Excel base.

---

## 10. Build do executável

- Spec: `build.spec` (modo **onedir**, mais estável com PySide6).
- Script auxiliar: `build_app.ps1`.
- Templates Excel entram em `datas` do Analysis.
- Em produção, o `.db` fica em `data/` relativo ao executável (`get_data_path`).

Boas práticas de distribuição:

1. Backup do `medicao.db` do usuário antes de atualizar o `.exe`.  
2. Não substituir a pasta `data/` do cliente com a do desenvolvedor.  
3. Testar upgrade: abrir build nova em cima de um `.db` da versão anterior.

---

## 11. Migração e compatibilidade de banco

A versão com abas é compatível com bancos da linha 2.x:

| Situação no BD antigo | Comportamento |
|----------------------|---------------|
| Só histórico / sem medição ativa | Não reimporta planilha; tela de lançamentos vazia |
| Lançamentos com `valor_a_pagar > 0` | Ganha ciclo aberto “Medição” |
| Só residual (`valor_a_pagar = 0`) | Ciclo migrado **fechado** (não polui a tela) |
| Já usado (tem fornecedor ou histórico) | Nunca reseta pela planilha base |

Sempre preferir **ALTER + backfill** a recriar tabelas.

---

## 12. Como adaptar esta base para outro sistema

Esta base serve bem para qualquer domínio do tipo:

> **Cadastros mestres + documentos/lançamentos por “contexto” + fechamento periódico + histórico**

Exemplos: ordens de serviço, medições de obra, controle de adiantamentos, comissões, inventário por período, pedidos por filial.

### Passo a passo sugerido

1. **Copie o esqueleto**  
   `main.py`, `paths.py`, `database.py` (só o shell), `utils.py`, uma tela CRUD, uma tela de “movimento”.

2. **Renomeie o domínio**  
   - `projetos` → clientes / obras / filiais  
   - `fornecedores` → o cadastro mestre que for  
   - `lancamentos` → itens do movimento  
   - `ciclos` → se precisar de “várias abas/períodos abertos”

3. **Defina o equivalente ao “fechar medição”**  
   O que exporta? O que vai para histórico? O que zera ou acumula?

4. **Mantenha os padrões**  
   Paths dual, migração, `(bool, msg)`, refresh ao mudar de tela, mensagens orientativas.

5. **UI**  
   Reuse sidebar + stack; troque labels e colunas da tabela; preserve o dark theme se quiser identidade visual da família de apps.

6. **Excel**  
   Só se o processo exigir planilha: um template + uma função de export isolada em `database` ou `export_excel.py`.

### O que *não* copiar cegamente

- Regras de % de adiantamento/mobilização (são deste negócio).  
- Lista fixa `PROJETOS_SISTEMA` (pode virar cadastro dinâmico).  
- Template Excel específico de medição AEV.

### O que *sempre* copiar

- Separação UI / database / paths.  
- Migração segura.  
- Critério “não reimportar seed se o banco já foi usado”.  
- Fechamento transacional (export falhou → não grava histórico).  
- Abas/ciclos **se** o usuário precisar de trabalhos paralelos no mesmo contexto.

---

## 13. Checklist de novo projeto

Use ao iniciar um sistema “irmão”:

- [ ] `paths.py` com `get_data_path` / `get_resource_path`
- [ ] `database.inicializar_banco()` + `_migrar_banco()`
- [ ] Seed só se banco virgem
- [ ] `main` com sidebar + `QStackedWidget`
- [ ] Uma tela CRUD com mensagens de UNIQUE claras
- [ ] Uma tela de movimento com tabela + formulário
- [ ] Funções de escrita retornando `(ok, erro)`
- [ ] Refresh ao entrar na tela
- [ ] Spec PyInstaller onedir + pasta `data/`
- [ ] Instrução de backup do `.db` na atualização
- [ ] (Opcional) ciclos/abas se houver paralelismo
- [ ] (Opcional) histórico + estatística + filtros

---

## Glossário rápido

| Termo no sistema | Significado |
|------------------|-------------|
| Projeto | Contexto global (obra/contrato) |
| Ciclo / aba | Período de trabalho aberto (medição, saldo final, emergencial) |
| PC | Identificador do lançamento |
| Fechar medição | Exportar + histórico + acumular pagos + fechar ciclo |
| Recomeçar | Apaga lançamentos da aba (sem histórico) |
| Valores pagos / a pagar | Acumulado já pago vs valor desta medição |

---

## Licença / uso interno

Projeto orientado a uso interno (CITRA / medições). Adapte este README e a estrutura conforme a política da equipe ao derivar novos sistemas.

---

*Documentação alinhada à base com abas de ciclo, migração segura de BD legado, exportação Excel e mensagens de erro orientativas.*
