# TEMPLATE-APP — Base genérica para sistemas desktop

Guia para **criar um novo sistema** reutilizando a arquitetura validada do Gerenciador de Medições, **sem** amarrar o domínio (medição, PC, fornecedor, etc.).

Use este arquivo como checklist e mapa mental ao iniciar um app novo.

---

## 1. Quando usar esta base

Serve bem quando o problema se parece com:

> Cadastros mestres + movimentos/documentos por contexto + (opcional) períodos paralelos + fechamento + histórico

Exemplos: ordens de serviço, pedidos por filial, comissões, inventário por período, adiantamentos, tickets, controle de contratos.

**Não** é a melhor base se você precisa de multi-usuário online, API pública ou sincronização em tempo real (aí o núcleo muda: servidor + auth).

---

## 2. Stack sugerida

| Peça | Tecnologia | Papel |
|------|------------|--------|
| UI | PySide6 | Desktop Qt |
| Dados | SQLite (`sqlite3`) | Offline, um arquivo |
| Planilhas (opcional) | openpyxl | Import/export |
| Empacote | PyInstaller (onedir) | `.exe` + pasta `data/` |
| Linguagem | Python 3.10+ | — |

Mínimo em `requirements.txt`:

```
PySide6>=6.4.0
openpyxl>=3.1.0
```

---

## 3. Esqueleto de pastas

```
MeuSistema/
├── main.py                 # Shell: sidebar + stack de telas
├── database.py             # SQLite, migração, CRUD, (export)
├── paths.py                # .py vs .exe — dados e recursos
├── utils.py                # Formatação, helpers de tabela
├── validators.py           # (opcional) regras de campo
│
├── ui_cadastro.py           # Ex.: entidades mestres
├── ui_movimento.py          # Ex.: lançamentos / documentos
├── ui_historico.py          # (opcional) fechamentos passados
├── ui_dashboard.py          # (opcional) totais / estatística
│
├── app.db                  # Gerado em runtime (não versionar se tiver dados reais)
├── assets/                 # Templates, ícones, seed (opcional)
├── build.spec
├── requirements.txt
├── README.md
└── TEMPLATE-APP.md         # Este arquivo
```

**Regra:** UI não executa SQL; `database` não monta widget; `paths` não conhece regra de negócio.

---

## 4. Camadas

```
main.py
  └── QStackedWidget
        ├── ui_cadastro
        ├── ui_movimento
        └── ui_historico / ui_dashboard
              │
              ▼
         database.py  →  SQLite (app.db)
              │
         paths.py     →  onde está o .db e os arquivos embutidos
```

### `main.py`

- Inicializa o banco **uma vez** no start: `database.inicializar_banco()`.
- Sidebar com botões checkable.
- Ao **mudar de tela**, chama `recarregar()` / `carregar_*` da tela ativa (evita dados velhos).

### `database.py`

- `get_connection()` com `PRAGMA foreign_keys = ON`.
- `inicializar_banco()`: `CREATE TABLE IF NOT EXISTS` + `_migrar_banco()`.
- Seed **somente** se o banco estiver virgem (critério explícito).
- Funções de escrita retornam `(sucesso: bool, mensagem_erro: str)`.

### `paths.py`

```text
get_base_path()       → pasta do script ou do executável
get_data_path()       → onde grava o .db (ex.: data/ no frozen)
get_resource_path(x)  → template/seed dentro do pacote (_MEIPASS no PyInstaller)
```

---

## 5. Modelo de dados genérico

Renomeie conforme o domínio.

| Conceito genérico | Exemplo A | Exemplo B |
|-------------------|-----------|-----------|
| **Contexto** | Projeto / Obra | Filial / Cliente |
| **Cadastro mestre** | Fornecedor | Produto / Técnico |
| **Movimento** | Lançamento | Pedido / OS |
| **Período paralelo** (opcional) | Ciclo / Aba | Caixa do dia / Turno |
| **Histórico** | Medição fechada | Pedido faturado |

### Tabelas mínimas

```sql
-- Contexto
CREATE TABLE contextos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT UNIQUE NOT NULL
);

-- Cadastro mestre
CREATE TABLE entidades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT UNIQUE NOT NULL,
  documento TEXT UNIQUE,      -- CPF/CNPJ/código
  -- outros campos...
);

-- (Opcional) períodos paralelos no mesmo contexto
CREATE TABLE periodos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contexto_id INTEGER NOT NULL,
  titulo TEXT,
  tipo TEXT,                  -- ex.: NORMAL, EXTRA, AJUSTE
  aberto INTEGER DEFAULT 1,
  data_criacao TEXT,
  ordem INTEGER DEFAULT 0,
  FOREIGN KEY (contexto_id) REFERENCES contextos(id)
);

-- Movimentos
CREATE TABLE movimentos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contexto_id INTEGER NOT NULL,
  periodo_id INTEGER,         -- se usar abas/períodos
  codigo TEXT NOT NULL,       -- identificador do item
  -- valores, status, datas...
  FOREIGN KEY (contexto_id) REFERENCES contextos(id),
  FOREIGN KEY (periodo_id) REFERENCES periodos(id)
);

-- Histórico de fechamento (snapshot)
CREATE TABLE historico (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contexto_id INTEGER NOT NULL,
  data_fechamento TEXT,
  tipo_periodo TEXT,
  -- cópia dos campos relevantes do movimento
  data_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Seed seguro

```text
SE movimentos == 0 E historico == 0 E entidades == 0
    → pode importar seed / planilha base
SENÃO
    → nunca sobrescrever dados de produção
```

---

## 6. Migração incremental

```python
def _migrar_banco(cursor):
    # 1) Criar tabelas novas com IF NOT EXISTS
    # 2) PRAGMA table_info → ADD COLUMN se faltar
    # 3) Backfill (ex.: periodo_id nulo → criar período padrão)
    # 4) Nunca DROP em produção sem plano de backup
```

Upgrade de versão = **ALTER + backfill**, não recriar o `.db`.

---

## 7. Contrato de erro

```python
def criar_entidade(dados) -> tuple[bool, str]:
    ...
    return True, ""
    # ou
    return False, (
        "Não foi possível salvar.\n\n"
        "Verifique se:\n"
        "• O nome já não está cadastrado\n"
        "• O documento está correto"
    )
```

Na UI:

```python
ok, erro = database.criar_entidade(dados)
if not ok:
    QMessageBox.critical(self, "Erro", erro)
```

Situações típicas para mensagem clara:

| Falha | Orientar o usuário a |
|-------|----------------------|
| UNIQUE / duplicado | Qual campo conflita e o valor |
| Arquivo Excel aberto | Fechar o arquivo e tentar de novo |
| Sem permissão de pasta | Escolher outro destino / rodar como usuário com escrita |
| Registro sumiu | Atualizar lista / verificar se está no período certo |
| Limite de abas/períodos | Fechar um período antes de abrir outro |

---

## 8. Padrões de UI

### Shell

- Sidebar fixa (~220–240px), botões checkable.
- `QStackedWidget` para telas.
- Tema dark opcional (paleta slate): `#0f172a`, `#1e293b`, `#3b82f6`, `#f8fafc`.

### Tela CRUD

- Formulário + tabela.
- Duplo clique → editar.
- Validar campos obrigatórios **na UI** antes de chamar o banco.
- Duplicidade: checar no banco e devolver mensagem específica.

### Tela de movimento

- Filtro por **contexto** (combo).
- (Opcional) barra de **abas** = períodos abertos.
- Tabela + formulário lateral ou superior.
- Cards de resumo (totais) calculados sobre os dados visíveis.
- Busca local na tabela (`setRowHidden`).

### Completer (listas longas)

```python
combo.setEditable(True)
completer = QCompleter(lista)
completer.setFilterMode(Qt.MatchContains)
completer.setCaseSensitivity(Qt.CaseInsensitive)
combo.setCompleter(completer)
combo.setInsertPolicy(QComboBox.NoInsert)
```

### Períodos paralelos (opcional)

Só implemente se o usuário precisar de **dois trabalhos abertos no mesmo contexto**:

- Criar período: tipo + título opcional.
- Limite por contexto (ex.: 8).
- Fechar período: exportar (se houver) → histórico → marcar `aberto = 0`.
- Excluir período: destrutivo, sem histórico (com confirmação).
- Contexto da tela = combo global; abas sempre do contexto selecionado.

---

## 9. Fechamento de período (padrão seguro)

```text
1. Exportar arquivo (Excel/PDF) se o processo exigir
2. Se exportar falhar → ABORTAR (banco intacto)
3. Gravar snapshot no histórico
4. Atualizar saldos / status nos movimentos
5. Marcar período como fechado
6. Atualizar a UI (remover aba / limpar lista)
```

Nunca grave histórico se o passo 1 for obrigatório e tiver falhado.

---

## 10. Build e distribuição

1. `build.spec` em modo **onedir** (mais estável com PySide6).
2. Incluir templates/seed em `datas`.
3. `.db` em `get_data_path()` (ex.: `./data/app.db` ao lado do exe).
4. Na atualização: **backup do `.db` do cliente** antes de trocar o executável.
5. Não distribuir o seu `app.db` de desenvolvimento por cima do do usuário.

---

## 11. Checklist — novo app

### Fundação

- [ ] `paths.py` (base / data / resource)
- [ ] `database.inicializar_banco` + `_migrar_banco`
- [ ] Seed só se banco virgem
- [ ] `main` com sidebar + stack
- [ ] Uma tela CRUD
- [ ] Uma tela de movimento

### Qualidade

- [ ] Escrita no banco retorna `(ok, erro)`
- [ ] Mensagens de UNIQUE / arquivo bloqueado claras
- [ ] Refresh ao entrar na tela
- [ ] `.gitignore` com `.db` local, `dist/`, `build/`, `.venv/`

### Deploy

- [ ] `requirements.txt`
- [ ] `build.spec` + script de build
- [ ] README do produto (para o usuário final)
- [ ] Nota de versão + “faça backup do banco”

### Opcional

- [ ] Períodos/abas paralelos
- [ ] Histórico + filtros
- [ ] Dashboard / estatística
- [ ] Export Excel/PDF
- [ ] Completer em combos grandes

---

## 12. Ordem de implementação sugerida

```text
1. paths + database vazio (1 tabela contexto + 1 entidade)
2. main + tela CRUD funcionando
3. Tela de movimento (sem período)
4. Validações e mensagens de erro
5. Histórico / fechamento (se existir no negócio)
6. Períodos/abas (só se o fluxo real exigir)
7. Export e build
8. Teste de upgrade de .db antigo → novo
```

Evite começar pelo executável ou pelo tema visual: primeiro o fluxo de dados.

---

## 13. O que copiar vs o que inventar

| Copiar da base validada | Inventar no domínio novo |
|-------------------------|---------------------------|
| Separação main / ui / database / paths | Nomes de tabelas e campos |
| Migração incremental | Regras de cálculo |
| `(ok, msg)` + QMessageBox | Status e workflows |
| Seed só se virgem | Planilhas e templates |
| Refresh ao mudar tela | Textos e labels |
| PyInstaller onedir + data/ | Integrações externas |
| Completer + dark theme (se quiser) | Relatórios específicos |

---

## 14. Anti-padrões a evitar

1. SQL dentro de `ui_*.py`.
2. Reimportar seed toda vez que a tabela de movimento estiver vazia (apaga o sentido de “usuário limpou de propósito”).
3. Mensagem só “Erro ao salvar” sem causa.
4. Fechar período no banco antes de garantir o arquivo exportado (se o arquivo for obrigatório).
5. Um único `.db` de dev versionado e sobrescrito no PC do cliente.
6. Abas por contexto misturando outro contexto na mesma barra (confunde o usuário).

---

## 15. Mapa rápido de renomeação

Ao clonar o projeto de medições:

| Nome antigo | Nome genérico |
|-------------|---------------|
| `projetos` | `contextos` |
| `fornecedores` | `entidades` |
| `lancamentos` | `movimentos` |
| `ciclos` | `periodos` |
| `historico_medicoes` | `historico` |
| `ui_lancamentos` | `ui_movimento` |
| `fechar_medicao` | `fechar_periodo` |
| `medicao.db` | `app.db` |

Ajuste labels na sidebar e nos títulos — a mecânica permanece.

---

*Template derivado da arquitetura do Gerenciador de Medições (PySide6 + SQLite + ciclos/abas + migração segura + erros orientativos). Adapte o domínio; preserve os padrões.*
