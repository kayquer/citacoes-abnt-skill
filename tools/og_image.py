"""Gera docs/og.png (1200x630) para Open Graph. Requer Pillow; roda só quando o visual muda.

    py -3 tools/og_image.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTES = Path("C:/Windows/Fonts")


def fonte(nome, tam):
    for cand in (FONTES / nome, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")):
        if cand.exists():
            return ImageFont.truetype(str(cand), tam)
    return ImageFont.load_default()


def main():
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), "#fbfaf7")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 24, h], fill="#1f5f4a")
    d.text((80, 70), "“", font=fonte("georgiab.ttf", 160), fill="#1f5f4a")
    d.text((80, 230), "Citações ABNT para Claude", font=fonte("georgiab.ttf", 68), fill="#1d1c1a")
    d.text((80, 330), "Biblioteca de citações · checador de referências", font=fonte("arial.ttf", 38), fill="#5f5b53")
    d.text((80, 380), "ABNT vigente com regras de 50 instituições de ensino", font=fonte("arial.ttf", 38), fill="#5f5b53")
    selos = ["NBR 6023:2025", "NBR 10520:2023", "NBR 14724:2024"]
    x = 80
    for s in selos:
        f = fonte("arialbd.ttf", 28)
        lw = d.textlength(s, font=f)
        d.rounded_rectangle([x, 480, x + lw + 36, 532], radius=26, outline="#1f5f4a", width=3)
        d.text((x + 18, 489), s, font=f, fill="#1f5f4a")
        x += lw + 56
    d.text((80, 565), "kayquer.github.io/citacoes-abnt-skill", font=fonte("arial.ttf", 26), fill="#5f5b53")
    img.save(RAIZ / "docs" / "og.png", optimize=True)
    print("docs/og.png")


if __name__ == "__main__":
    main()
