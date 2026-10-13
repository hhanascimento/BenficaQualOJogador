#!/usr/bin/env python3
"""Build the Home/Help logo lockup: the Benfica crest + the "QUAL O JOGADOR"
wordmark + the red-to-gold rule.

The proportions follow Benfica Onze Inicial's home lockup (measured from its
own home capture): the wordmark spans ~0.9 of the crest width, sits 0.075 of
the crest height below it, and carries a thin (0.011 of the crest height)
red-to-gold rule 0.05 of the crest height beneath it. Our wordmark is longer
than "ONZE INICIAL", so it fills slightly more of the crest width.

The wordmark is Roboto (Apache-2.0) converted to outlines, so the file is
font-independent and renders identically everywhere. The crest is reused
verbatim from `public/assets/benfica-logo.svg`.

    ROBOTO=/path/Roboto-Bold.ttf python3 tools/home_logo.py

Writes `public/assets/qual-o-jogador-logo.svg`.
"""
import os
import re
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.environ.get("ROBOTO", "/tmp/Roboto-Bold.ttf")
CREST = os.path.join(ROOT, "public/assets/benfica-logo.svg")
OUT = os.path.join(ROOT, "public/assets/qual-o-jogador-logo.svg")

TEXT = "QUAL O JOGADOR"
TRACKING = 3.0            # extra letter-spacing, crest units
RED = "#e31c2d"
GOLD = "#f4c430"

# proportions measured from the reference home lockup, as a fraction of crest size
WIDTH_FRAC = 0.95         # wordmark width / crest width  (ref 0.892; ours is longer)
GAP1_FRAC = 0.075         # crest bottom -> cap top      (ref 0.075)
GAP2_FRAC = 0.052         # cap baseline bottom -> rule  (ref 0.052)
RULE_W_FRAC = 0.283      # rule width / crest width     (ref 0.283)
RULE_H_FRAC = 0.011       # rule height / crest height   (ref 0.011)


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
        if pen.getCommands():
            parts.append(pen.getCommands())
        x += glyph.width * scale + tracking
    return " ".join(parts), (x - tracking if text else 0.0)


def crest_parts():
    svg = open(CREST, encoding="utf-8").read()
    vb = re.search(r'viewBox="([^"]+)"', svg).group(1)
    x0, y0, w, h = (float(v) for v in vb.split())
    inner = svg[svg.index(">", svg.index("<svg")) + 1 : svg.rindex("</svg>")]
    return inner.strip(), x0, y0, w, h


def build(font_path=FONT):
    font = TTFont(font_path)
    inner, x0, y0, cw, ch = crest_parts()

    # size the wordmark so it spans WIDTH_FRAC of the crest width
    target = cw * WIDTH_FRAC
    size = 120
    while size > 8:
        _, w = text_path(font, TEXT, size, TRACKING)
        if w <= target:
            break
        size -= 1
    d, text_w = text_path(font, TEXT, size, TRACKING)

    upem = font["head"].unitsPerEm
    cap = getattr(font["OS/2"], "sCapHeight", None) or int(upem * 0.71)
    cap_h = cap * size / upem

    text_top = (y0 + ch) + GAP1_FRAC * ch
    baseline = text_top + cap_h
    rule_h = RULE_H_FRAC * ch
    rule_top = baseline + GAP2_FRAC * ch
    rule_w = RULE_W_FRAC * cw
    total_h = rule_top + rule_h + 0.05 * ch

    cx = x0 + cw / 2
    tx = round(cx - text_w / 2, 1)
    rule_x = round(cx - rule_w / 2, 1)

    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {cw:g} {total_h:.1f}" width="100%" height="100%"',
        '     role="img" aria-label="Benfica \u2014 Qual o Jogador">',
        "  <title>Benfica \u2014 Qual o Jogador</title>",
        "  <!-- Club crest + the QUAL O JOGADOR wordmark (Roboto, Apache-2.0, converted",
        "       to outlines) + the red-to-gold rule. No font is needed to render it. -->",
        "  <defs>",
        '    <linearGradient id="ruleGrad" x1="0%" y1="0%" x2="100%" y2="0%">',
        f'      <stop offset="0%" stop-color="{RED}"/>',
        f'      <stop offset="100%" stop-color="{GOLD}"/>',
        "    </linearGradient>",
        "  </defs>",
        f'  <g transform="translate({-x0:g} {-y0:g})">',
        "    " + inner,
        "  </g>",
        f'  <path transform="translate({tx} {baseline:.1f})" fill="#ffffff" d="{d}"/>',
        f'  <rect x="{rule_x}" y="{rule_top:.1f}" width="{rule_w:.1f}" height="{rule_h:.1f}"'
        f' rx="{rule_h / 2:.1f}" fill="url(#ruleGrad)"/>',
        "</svg>",
        "",
    ])


if __name__ == "__main__":
    svg = build()
    open(OUT, "w", encoding="utf-8").write(svg)
    print(f"wrote {OUT}  ({len(svg)} bytes)")
