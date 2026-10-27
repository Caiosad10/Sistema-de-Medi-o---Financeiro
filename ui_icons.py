"""
ui_icons.py — Ícones via Material Design Icons (qtawesome), com fallback vetorial.

Uso:
    from ui_icons import pixmap_icone, icone
    botao.setIcon(icone("lista", "#cbd5e1", 22))
    label.setPixmap(pixmap_icone("capacete", "#ffffff", 18))
"""
from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QPainterPath, QIcon

# Nome interno -> Material Design Icons (qtawesome mdi.*)
_MAPA_MDI = {
    "lista": "mdi.format-list-bulleted",
    "pessoa": "mdi.account",
    "documento": "mdi.file-document-outline",
    "grafico": "mdi.chart-bar",
    "mais": "mdi.plus",
    "x": "mdi.close",
    "download": "mdi.download",
    "cadeado": "mdi.lock-outline",
    "reiniciar": "mdi.refresh",
    "capacete": "mdi.hard-hat",
    "moeda": "mdi.currency-usd",
    "check": "mdi.check-circle-outline",
    "menu": "mdi.menu",
    "busca": "mdi.magnify",
    "pasta": "mdi.folder-outline",
    "seta_direita": "mdi.chevron-right",
    "calendario": "mdi.calendar-month",
    "dinheiro": "mdi.cash",
    "filtro": "mdi.filter-outline",
    "relogio": "mdi.clock-outline",
    "editar": "mdi.pencil-outline",
    "lixeira": "mdi.delete-outline",
    "casa": "mdi.home-outline",
}

_QTA_OK = None


def _qtawesome_disponivel():
    global _QTA_OK
    if _QTA_OK is None:
        try:
            import qtawesome  # noqa: F401
            _QTA_OK = True
        except Exception:
            _QTA_OK = False
    return _QTA_OK


def _nome_mdi(nome: str) -> str:
    return _MAPA_MDI.get(nome, "mdi.circle-outline")


def icone(nome: str, cor: str = "#cbd5e1", tam: int = 22, cor_ativo=None) -> QIcon:
    """QIcon nítido (Material Design). cor_ativo = estado selected/active."""
    if _qtawesome_disponivel():
        import qtawesome as qta
        kwargs = {"color": cor}
        if cor_ativo:
            kwargs["color_active"] = cor_ativo
            kwargs["color_selected"] = cor_ativo
        icon = qta.icon(_nome_mdi(nome), **kwargs)
        if not icon.isNull():
            return icon
    icon = QIcon()
    icon.addPixmap(_pixmap_fallback(nome, cor, tam))
    if cor_ativo:
        icon.addPixmap(
            _pixmap_fallback(nome, cor_ativo, tam),
            QIcon.Mode.Normal,
            QIcon.State.On,
        )
    return icon


def pixmap_icone(nome: str, cor: str = "#cbd5e1", tam: int = 22) -> QPixmap:
    """QPixmap do ícone (badges dos cards)."""
    tam = max(8, int(tam))
    if _qtawesome_disponivel():
        import qtawesome as qta
        icon = qta.icon(_nome_mdi(nome), color=cor)
        pm = icon.pixmap(QSize(tam, tam))
        if not pm.isNull():
            return pm
    return _pixmap_fallback(nome, cor, tam)


def _pixmap_fallback(nome: str, cor: str, tam: int) -> QPixmap:
    pm = QPixmap(tam, tam)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(cor))
    pen.setWidthF(max(1.6, tam * 0.09))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.scale(tam / 24.0, tam / 24.0)

    def line(x1, y1, x2, y2):
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    if nome == "capacete":
        path = QPainterPath()
        path.moveTo(5, 14.5)
        path.cubicTo(5.3, 8.2, 8.2, 5, 12, 5)
        path.cubicTo(15.8, 5, 18.7, 8.2, 19, 14.5)
        p.drawPath(path)
        line(3.5, 14.5, 20.5, 14.5)
        line(12, 5.5, 12, 14.2)
    elif nome == "moeda":
        p.drawEllipse(QRectF(4, 4, 16, 16))
        line(12, 7.5, 12, 16.5)
    elif nome == "reiniciar":
        path = QPainterPath()
        path.arcMoveTo(QRectF(4.5, 4.5, 15, 15), 45)
        path.arcTo(QRectF(4.5, 4.5, 15, 15), 45, 285)
        p.drawPath(path)
        line(17.5, 4.5, 17.5, 8.5)
        line(17.5, 8.5, 21, 8.5)
    elif nome == "check":
        line(5, 12.5, 10, 17)
        line(10, 17, 19, 7)
    elif nome == "cadeado":
        path = QPainterPath()
        path.moveTo(7.5, 10.5)
        path.lineTo(7.5, 8.5)
        path.cubicTo(7.5, 2.8, 16.5, 2.8, 16.5, 8.5)
        path.lineTo(16.5, 10.5)
        p.drawPath(path)
        p.drawRoundedRect(QRectF(5.5, 10, 13, 10.5), 2, 2)
    elif nome == "download":
        line(12, 3.5, 12, 14)
        line(7.8, 10.5, 12, 14.7)
        line(16.2, 10.5, 12, 14.7)
        line(5, 19.5, 19, 19.5)
    elif nome == "mais":
        line(12, 5.5, 12, 18.5)
        line(5.5, 12, 18.5, 12)
    else:
        p.drawEllipse(QRectF(5, 5, 14, 14))

    p.end()
    return pm
