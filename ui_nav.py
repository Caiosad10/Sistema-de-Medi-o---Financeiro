"""
ui_nav.py — Menu flutuante "glass" (hamburger) no canto superior esquerdo.

Estilo Apple: pill glass translúcido com blur real do fundo atrás do painel.
- Botão flutuante (☰) sempre visível no canto superior esquerdo
- Clique → painel expande na vertical a partir do próprio botão
- Scrim escuro translúcido fecha ao clicar fora
- NÃO modal (sem QEventLoop) — a UI continua interativa
- Fecha sozinho ao escolher um item

Uso:
    from ui_nav import MenuFlutuanteGlass
    menu = MenuFlutuanteGlass(janela, itens=[(0, "📊", "Lançamentos"), ...],
                              ao_navegar=self.mudar_tela)
    menu.definir_indice(0)
"""
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QLabel, QPushButton,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect,
)
from PySide6.QtCore import Qt, QEvent, QPropertyAnimation, QEasingCurve, QRect, QRectF
from PySide6.QtGui import QPixmap, QImage, QPainter, QPainterPath

_LARGURA_PAINEL = 240
_TAM_BOTAO = 52
_MARGIN = 24
_RAIO = 16


def _regiao_desfocada(janela, rect, raio=24):
    """Captura uma região da janela, aplica blur e devolve o pixmap."""
    if janela is None or rect.width() <= 0 or rect.height() <= 0:
        return QPixmap()
    pix = janela.grab(rect)
    if pix.isNull():
        return QPixmap()
    cena = QGraphicsScene()
    item = QGraphicsPixmapItem(pix)
    efeito = QGraphicsBlurEffect()
    efeito.setBlurRadius(raio)
    efeito.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(efeito)
    cena.addItem(item)
    img = QImage(pix.size(), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    cena.render(painter)
    painter.end()
    return QPixmap.fromImage(img)


def _arredondar_pixmap(pix, raio=_RAIO):
    """Devolve o pixmap com cantos arredondados."""
    if pix.isNull():
        return pix
    saida = QPixmap(pix.size())
    saida.fill(Qt.GlobalColor.transparent)
    p = QPainter(saida)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(saida.rect()), raio, raio)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pix)
    p.end()
    return saida


class MenuFlutuanteGlass(QWidget):
    """Overlay flutuante: botão glass no canto + painel que expande na vertical."""

    def __init__(self, janela, itens, ao_navegar=None, botao=None, largura_rail=0):
        super().__init__(janela)
        self._janela = janela
        self._itens = itens
        self._ao_navegar = ao_navegar
        self._largura_rail = largura_rail
        self._botao_externo = botao is not None
        self._aberto = False
        self._indice_ativo = 0
        self._anim = None

        # Cobre SÓ a área do conteúdo (rail fica de fora) e nasce ESCONDIDO -
        # menu fechado não intercepta cliques do usuário.
        x0 = largura_rail if largura_rail > 0 else 0
        if janela is not None:
            self.setGeometry(x0, 0, max(1, janela.width() - x0), janela.height())
        else:
            self.resize(1280, 720)

        # Botão fornecido pela rail (main.py); senão cria o flutuante
        self._botao = botao

        self._montar()
        self.hide()

        if self._botao_externo:
            self._botao.clicked.connect(self.toggle)

        if janela is not None:
            janela.installEventFilter(self)

    def _montar(self):
        # Camada 1: scrim escuro translúcido (fecha ao clicar)
        self._scrim = QWidget(self)
        self._scrim.setStyleSheet("background-color: rgba(2, 6, 23, 110);")
        self._scrim.setGeometry(0, 0, self.width(), self.height())
        self._scrim.lower()
        self._scrim.mousePressEvent = lambda e: self.fechar()
        self._scrim.hide()  # só aparece quando o menu abre (bug: nascia visível = tela escura)

        # Camada 2: fundo desfocado atrás do painel (blur do glass)
        self._fundo = QLabel(self)
        self._fundo.setScaledContents(True)
        self._fundo.lower()

        # Botão flutuante glass (pill) — só se NÃO veio da rail
        if self._botao is None:
            self._botao = QPushButton("☰", self)
            self._botao.setFixedSize(_TAM_BOTAO, _TAM_BOTAO)
            self._botao.setStyleSheet("""
                QPushButton {
                    background-color: rgba(15, 23, 42, 205);
                    color: #f8fafc;
                    font-size: 20px;
                    font-weight: bold;
                    border: 1px solid rgba(255, 255, 255, 70);
                    border-radius: 26px;
                }
                QPushButton:hover { background-color: rgba(30, 41, 59, 225); }
                QPushButton:pressed { background-color: rgba(51, 65, 85, 235); }
            """)
            self._botao.setCursor(Qt.CursorShape.PointingHandCursor)
            self._botao.clicked.connect(self.toggle)

        # Camada 3: painel glass (conteúdo)
        self._painel = QFrame(self)
        self._painel.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(15, 23, 42, 228);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: {_RAIO}px;
            }}
            QLabel {{ color: #f8fafc; background: transparent; border: none; }}
            QLabel#tituloNav {{ font-size: 12px; font-weight: 800; color: #94a3b8; padding: 2px 14px 6px 14px; }}
            QPushButton {{
                background-color: transparent;
                color: #cbd5e1;
                text-align: left;
                padding: 11px 16px;
                font-size: 13px;
                font-weight: 600;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 35); color: #f8fafc; }}
            QPushButton:checked {{ background-color: #6d5dd3; color: #ffffff; }}
        """)
        self._painel.hide()

        layout = QVBoxLayout(self._painel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)

        lbl_titulo = QLabel("MEDIÇÃO - CITRA")
        lbl_titulo.setObjectName("tituloNav")
        layout.addWidget(lbl_titulo)

        divisor = QFrame()
        divisor.setFrameShape(QFrame.HLine)
        divisor.setStyleSheet("background-color: rgba(255, 255, 255, 45); margin: 2px 6px 6px 6px;")
        layout.addWidget(divisor)

        self._botoes_itens = {}
        for indice, icone, titulo in self._itens:
            btn = QPushButton(f"{icone}   {titulo}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c, i=indice: self._navegar(i))
            layout.addWidget(btn)
            self._botoes_itens[indice] = btn

        self._painel.setFixedWidth(_LARGURA_PAINEL)
        self._painel.adjustSize()

        self._posicionar()

    def _x0(self):
        """X do overlay na janela: após a rail (0 no modo flutuante)."""
        return self._largura_rail if self._largura_rail > 0 else 0

    def _posicionar(self):
        if not self._botao_externo:
            self._botao.move(_MARGIN, _MARGIN)
        # Scrim cobre o overlay inteiro (coords relativas ao overlay)
        self._scrim.setGeometry(0, 0, self.width(), self.height())

    def _rect_fechado(self):
        # Semente da animação: mesmo X/L do painel aberto, altura mínima
        r = self._rect_aberto()
        return QRect(r.x(), r.y(), r.width(), 4)

    def _rect_aberto(self):
        # Coords RELATIVAS ao overlay
        h = self._painel.sizeHint().height()
        x = 8 if self._largura_rail > 0 else _MARGIN
        y = _MARGIN if self._largura_rail > 0 else _MARGIN + _TAM_BOTAO + 8
        return QRect(x, y, _LARGURA_PAINEL, h)

    def toggle(self):
        self.fechar() if self._aberto else self.abrir()

    def abrir(self):
        if self._aberto:
            return
        self._aberto = True

        # Blur do fundo: grab em coords DA JANELA (overlay deslocado após a rail)
        rel = self._rect_aberto()
        rect_janela = QRect(rel.x() + self._x0(), rel.y(), rel.width(), rel.height())
        bruto = _regiao_desfocada(self._janela, rect_janela)
        self._fundo.setPixmap(_arredondar_pixmap(bruto))
        self._fundo.setGeometry(rel)
        self._fundo.show()
        self._fundo.raise_()

        self.show()  # overlay aparece só agora - fechado não bloqueia cliques
        self._painel.show()
        self._painel.setGeometry(self._rect_fechado())
        self._animar(self._rect_fechado(), self._rect_aberto(), 230,
                     QEasingCurve.Type.OutCubic, None)

        self._botao.setText("✕")
        self._scrim.show()
        self._scrim.raise_()
        self._botao.raise_()
        self._painel.raise_()

    def fechar(self):
        if not self._aberto:
            return
        self._aberto = False
        self._animar(self._rect_aberto(), self._rect_fechado(), 170,
                     QEasingCurve.Type.InCubic, self._ao_terminar_fechamento)
        self._fundo.hide()
        self._scrim.hide()
        self._botao.setText("☰")

    def _ao_terminar_fechamento(self):
        self._painel.hide()
        self.hide()  # overlay some de vez - cliques voltam ao conteudo

    def _animar(self, inicio, fim, duracao, easing, ao_terminar):
        if self._anim is not None:
            self._anim.stop()
        anim = QPropertyAnimation(self._painel, b"geometry", self)
        anim.setDuration(duracao)
        anim.setStartValue(inicio)
        anim.setEndValue(fim)
        anim.setEasingCurve(easing)
        anim.valueChanged.connect(lambda v: self._fundo.setGeometry(v))
        if ao_terminar is not None:
            anim.finished.connect(ao_terminar)
        anim.start()
        self._anim = anim

    def _navegar(self, indice):
        self.definir_indice(indice)
        self.fechar()
        if self._ao_navegar is not None:
            self._ao_navegar(indice)

    def definir_indice(self, indice):
        self._indice_ativo = indice
        for i, btn in self._botoes_itens.items():
            btn.setChecked(i == indice)

    def eventFilter(self, origem, evento):
        if origem is self._janela and evento.type() == QEvent.Type.Resize:
            x0 = self._largura_rail if self._largura_rail > 0 else 0
            self.setGeometry(x0, 0, max(1, origem.width() - x0), origem.height())
            self._posicionar()
        return super().eventFilter(origem, evento)