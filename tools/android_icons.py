#!/usr/bin/env python3
"""Regenerate the Android launcher icons for "Benfica - Qual o Jogador".

Same design as public/app-icon.svg (red plate + gold rule + BENFICA / QUAL O /
JOGADOR). Writes every density of the legacy, round and adaptive layers under
android/app/src/main/res/, matching the 108dp canvas / 72dp viewport rule the
platform uses for adaptive icons.

    python3 tools/android_icons.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.environ.get("ROBOTO", "/tmp/Roboto-Black.ttf")
RES = os.path.join(ROOT, "android/app/src/main/res")
DENSITIES = [("mdpi", 1), ("hdpi", 1.5), ("xhdpi", 2), ("xxhdpi", 3), ("xxxhdpi", 4)]
RED = (200, 22, 29, 255)
GOLD = (244, 196, 48, 255)
BASE = 512


def art(with_plate=True, round_=False):
    img = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if with_plate:
        radius = BASE if round_ else 96
        d.rounded_rectangle([0, 0, BASE - 1, BASE - 1], radius=radius, fill=RED)
    d.rounded_rectangle([20, 20, BASE - 21, BASE - 21], radius=76 if not round_ else 76,
                        outline=GOLD, width=6)
    font = ImageFont.truetype(FONT, 100)
    for text, sz, baseline, color in [("BENFICA", 62, 176, (255, 255, 255, 255)),
                                      ("QUAL O", 74, 288, GOLD), ("JOGADOR", 74, 398, GOLD)]:
        f = font.font_variant(size=sz)
        while d.textlength(text, font=f) > 420 and sz > 10:
            sz -= 2
            f = font.font_variant(size=sz)
        w = d.textlength(text, font=f)
        d.text(((BASE - w) / 2, baseline - sz), text, font=f, fill=color)
    return img


def scaled(img, px):
    return img.resize((px, px), Image.LANCZOS)


def main():
    legacy = art()
    round_art = art(round_=True)
    fg = art(with_plate=False)
    for name, density in DENSITIES:
        folder = os.path.join(RES, f"mipmap-{name}")
        os.makedirs(folder, exist_ok=True)
        # legacy + round icons: 48dp
        scaled(legacy, round(48 * density)).save(os.path.join(folder, "ic_launcher.png"))
        scaled(round_art, round(48 * density)).save(os.path.join(folder, "ic_launcher_round.png"))
        # adaptive layers: 108dp canvas, art in the central 72dp viewport
        canvas = round(108 * density)
        view = round(72 * density)
        bg = Image.new("RGBA", (canvas, canvas), RED)
        bg.save(os.path.join(folder, "ic_launcher_background.png"))
        layer = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
        layer.paste(scaled(fg, view), ((canvas - view) // 2, (canvas - view) // 2), scaled(fg, view))
        layer.save(os.path.join(folder, "ic_launcher_foreground.png"))
        print(f"  mipmap-{name}: {48*density:.0f}dp legacy, {canvas}px adaptive")
    # adaptive background colour
    with open(os.path.join(RES, "values/ic_launcher_background.xml"), "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
                 '    <color name="ic_launcher_background">#C8161D</color>\n</resources>\n')
    print("wrote values/ic_launcher_background.xml")


if __name__ == "__main__":
    main()
