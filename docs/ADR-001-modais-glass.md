# ADR-001 — Modais "Glass" (overlay interno com blur)

**Status:** Aprovado ✅
**Data:** 2026-10-26
**Contexto:** Substituição dos `QMessageBox` nativos do Qt.

## Decisão

Todos os modais de confirmação / informação / aviso / erro do sistema
usam a classe `_ModalGlass` em `ui_modal.py`:

- O modal é um **QWidget filho** da janela que o invocou (não um QDialog separado).
- Antes de exibir, tira um "print" da janela (`janela.grab()`), aplica
  `QGraphicsBlurEffect` (raio 16, QualityHint) e usa como fundo.
- Camadas:
  1. `QLabel` com o pixmap desfocado (`setScaledContents(True)`)
  2. `QWidget` overlay escuro `rgba(0, 0, 0, 160)`
  3. `QFrame#painelGlass` central: `rgba(15, 23, 42, 235)`,
     `border-radius: 16px`, borda `rgba(59, 130, 246, 130)`
- O bloqueio é feito com `QEventLoop` local + `deleteLater()` ao fechar
  (método `exec()` próprio — **não** herdar de QDialog).

## Funções públicas (usar sempre estas, nunca `_ModalGlass` direto)

| Função | Retorno | Uso |
|---|---|---|
| `confirmar(janela, titulo, msg)` | `bool` (True = "Sim") | perguntas Sim/Não |
| `informar(janela, titulo, msg)` | — | info, botão Ok |
| `alerta(janela, titulo, msg)` | — | aviso, botão Ok |
| `erro(janela, titulo, msg)` | — | erro, botão Ok |
| `importacao_pc(janela, msg, tipo_icone, com_botao_cadastro)` | `bool` (True = "Ir para Cadastros") | resultado de importação de PDF |
| `planilha_pronta(janela, caminho, total, proj)` | `bool` (True = "Abrir Pasta") | sucesso de exportação |

## Regras de implementação (aprendidas nesta migração)

1. **`setGeometry(janela.rect())` ANTES de montar o painel.**
   Chamar `_montar_painel()` antes deixa `self.width()/height() == 0`
   e o modal cai no canto superior esquerdo (bug corrigido em 2026-10-26).
2. Guardar `self._fundo_label` e `self._overlay` como atributos e
   redimensioná-los no `resizeEvent` + recentralizar o painel.
3. `QFileDialog` (abrir/salvar arquivo) **continua nativo do Windows** —
   apenas modais de mensagem usam o glass.
4. Nunca referenciar `_ModalGlass` fora de `ui_modal.py`
   (erro `"_ModalGlass" is not defined` na Ln 1321 de `ui_lancamentos.py`).

## Para reutilizar em projetos futuros

Copiar `ui_modal.py` inteiro e importar as 6 funções públicas.
Ajustar apenas cores/bordas no stylesheet de `QFrame#painelGlass`
para o tema do novo projeto.
