"""Gera o icone SisMed (PNG 512 + ICO multi-resolucao) sem dependencias externas."""
from PIL import Image, ImageDraw, ImageFont

SIZE = 512
BG = (15, 23, 42, 255)        # slate-900 (#0f172a)
ACCENT = (59, 130, 246, 255)  # azul (#6d5dd3)
ACCENT_DARK = (37, 99, 235, 255)
WHITE = (248, 250, 252, 255)
SUBTLE = (148, 163, 184, 255)

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Fundo arredondado
radius = 120
d.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=radius, fill=BG)
# Borda sutil
d.rounded_rectangle([4, 4, SIZE - 5, SIZE - 5], radius=radius - 6, outline=(30, 41, 59, 255), width=3)

# Barra de grafico (3 barras azuis)
bars = [(150, 300, 200, 390), (226, 240, 276, 390), (302, 180, 352, 390)]
for x0, y0, x1, y1 in bars:
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=ACCENT)
d.rounded_rectangle([302, 180, 352, 230], radius=14, fill=(96, 165, 250, 255))

# Linha de tendencia branca sobre as barras
trend = [(120, 330), (225, 275), (300, 235), (392, 160)]
d.line(trend, fill=WHITE, width=16, joint="curve")
for x, y in trend:
    d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=WHITE)
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=ACCENT_DARK)

# Texto "SisMed"
try:
    font = ImageFont.truetype("arialbd.ttf", 64)
except OSError:
    font = ImageFont.load_default()
d.text((SIZE // 2, 440), "SisMed", font=font, fill=WHITE, anchor="mm")

img.save("sismed_icon.png", "PNG")
img.save("sismed_icon.ico", "ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("Icone gerado: sismed_icon.png + sismed_icon.ico")
