#!/usr/bin/env python3
"""Turn text into SVG outlines, so a mark never depends on an installed font.

The app's marks are Roboto (Apache-2.0) converted to paths: the on-screen logo
lockup (Bold) and the favicon (Black) then render identically on every device,
including Android, which has no Impact/Arial Black.

    python3 tools/wordmark.py            # regenerate public/app-icon.svg
"""
import os, sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Roboto Black: the icon design asks for weight 900, and the extra weight
# survives being scaled down to a 16 px tab icon better than Bold does.
FONT = os.environ.get(
    "ROBOTO",
    "/tmp/roboto/root/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Black.ttf",
)
OUT = os.path.join(ROOT, "public/app-icon.svg")


def text_path(font, text, size, tracking=0.0):
    """Outline `text` at `size` px, origin at the first glyph's baseline start."""
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
        d = pen.getCommands()
        if d:
            parts.append(d)
        x += glyph.width * scale + tracking
    return " ".join(parts), (x - tracking if text else 0.0)


def line(font, text, size, tracking, center_x, baseline, **attrs):
    d, width = text_path(font, text, size, tracking)
    tx = round(center_x - width / 2, 1)
    attr = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    return f'    <path transform="translate({tx} {baseline})" {attr} d="{d}"/>'


def build(font_path=FONT):
    font = TTFont(font_path)
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%"',
        '     role="img" aria-label="Benfica Onze Inicial">',
        "  <title>Benfica Onze Inicial</title>",
        "  <!-- Red plate + gold rule + BENFICA / ONZE / INICIAL, Roboto (Apache-2.0)",
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
        line(font, "BENFICA", 62, 4, 256, 176, fill="#ffffff"),
        line(font, "ONZE", 72, 2, 256, 286, fill="url(#goldGrad)"),
        line(font, "INICIAL", 72, 2, 256, 394, fill="url(#goldGrad)"),
        "  </g>",
        "</svg>",
        "",
    ])


if __name__ == "__main__":
    svg = build(sys.argv[1] if len(sys.argv) > 1 else FONT)
    open(OUT, "w", encoding="utf-8").write(svg)
    print(f"wrote {OUT}  ({len(svg)} bytes, {svg.count('<path')} outlined lines)")
