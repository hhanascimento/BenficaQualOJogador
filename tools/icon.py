#!/usr/bin/env python3
"""Generate the "Qual o Jogador" app icon.

Same identity as Benfica Onze Inicial's mark — a red rounded plate, a gold rule
and an outlined Roboto (Apache-2.0) wordmark — but the wordmark reads
BENFICA / QUAL O / JOGADOR. Writes:
    public/app-icon.svg           (outlined SVG, the browser/app icon)
    store/app-icon-512.png        (512px, for store listings)
    public/icon-192.png           (192px, apple-touch/Android)

    ROBOTO=/path/Roboto-Black.ttf python3 tools/icon.py
"""
import os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.environ.get("ROBOTO", "/tmp/Roboto-Black.ttf")
LINES = [("BENFICA", "#ffffff"), ("QUAL O", "gold"), ("JOGADOR", "gold")]
SIZE = 512


def text_path(font, text, size, tracking=0.0):
    upem = font["head"].unitsPerEm
    scale = size / upem
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    parts, x = [], 0.0
    for ch in text:
        name = cmap.get(ord(ch))
        if name is None:
            continue
        glyph = glyphs[name]
        pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.1f}")
        glyph.draw(TransformPen(pen, Transform(scale, 0, 0, -scale, x, 0)))
        if pen.getCommands():
            parts.append(pen.getCommands())
        x += glyph.width * scale + tracking
    return " ".join(parts), (x - tracking if text else 0.0)


def fit(font, text, maxsize, maxwidth, tracking):
    size = maxsize
    while size > 10:
        _, w = text_path(font, text, size, tracking)
        if w <= maxwidth:
            return size, w
        size -= 2
    return 10, 0


def build_svg():
    font = TTFont(FONT)
    paths = []
    for (text, fill), baseline, maxsize in zip(LINES, (176, 288, 398), (62, 76, 76)):
        size, width = fit(font, text, maxsize, 408, 4 if text == "BENFICA" else 2)
        d, _ = text_path(font, text, size, 4 if text == "BENFICA" else 2)
        tx = round((SIZE - width) / 2, 1)
        color = fill if fill != "gold" else "url(#goldGrad)"
        paths.append(f'    <path transform="translate({tx} {baseline})" fill="{color}" d="{d}"/>')
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%"',
        '     role="img" aria-label="Benfica - Qual o Jogador">',
        "  <title>Benfica - Qual o Jogador</title>",
        "  <!-- Red plate + gold rule + BENFICA / QUAL O / JOGADOR, Roboto (Apache-2.0)",
        "       converted to outlines: no font is needed to render it. -->",
        "  <defs>",
        '    <radialGradient id="bgGrad" cx="50%" cy="50%" r="60%">',
        '      <stop offset="0%" stop-color="#e31c2d"/>',
        '      <stop offset="100%" stop-color="#99000a"/>',
        "    </radialGradient>",
        '    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">',
        '      <stop offset="0%" stop-color="#fff4b8"/>',
        '      <stop offset="50%" stop-color="#f4c430"/>',
        '      <stop offset="100%" stop-color="#b8860b"/>',
        "    </linearGradient>",
        '    <filter id="dropShadow" x="-10%" y="-10%" width="120%" height="120%">',
        '      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000000" flood-opacity="0.5"/>',
        "    </filter>",
        "  </defs>",
        '  <rect width="512" height="512" rx="96" fill="url(#bgGrad)"/>',
        '  <rect x="20" y="20" width="472" height="472" rx="76" fill="none"',
        '        stroke="url(#goldGrad)" stroke-width="6" opacity="0.8"/>',
        '  <g filter="url(#dropShadow)">',
        *paths,
        "  </g>",
        "</svg>",
        "",
    ])


def build_png(size):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # plate (solid approximation of the radial gradient)
    d.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=96, fill=(200, 22, 29, 255))
    d.rounded_rectangle([20, 20, SIZE - 21, SIZE - 21], radius=76, outline=(244, 196, 48, 255), width=6)
    font = ImageFont.truetype(FONT, 100)
    specs = [("BENFICA", 62, 176, (255, 255, 255, 255)),
             ("QUAL O", 74, 288, (244, 196, 48, 255)),
             ("JOGADOR", 74, 398, (244, 196, 48, 255))]
    for text, sz, baseline, color in specs:
        f = font.font_variant(size=sz)
        while d.textlength(text, font=f) > 420 and sz > 10:
            sz -= 2
            f = font.font_variant(size=sz)
        w = d.textlength(text, font=f)
        d.text(((SIZE - w) / 2, baseline - sz), text, font=f, fill=color)
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    svg = build_svg()
    open(os.path.join(ROOT, "public/app-icon.svg"), "w", encoding="utf-8").write(svg)
    print(f"app-icon.svg  {len(svg)} bytes, {svg.count('<path')} outlined lines")
    os.makedirs(os.path.join(ROOT, "store"), exist_ok=True)
    build_png(512).save(os.path.join(ROOT, "store/app-icon-512.png"))
    build_png(192).save(os.path.join(ROOT, "public/icon-192.png"))
    print("store/app-icon-512.png + public/icon-192.png written")
