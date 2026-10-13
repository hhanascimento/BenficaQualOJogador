#!/usr/bin/env python3
"""Normalise and compress the player photos in public/assets/players.

A face is only ever drawn inside a circle of at most 88 CSS px
(`PlayerSlot.css`), so every source is re-encoded as a progressive JPEG at
quality 85 with all metadata (EXIF/ICC/XMP) dropped, and anything longer than
MAX_SIDE is downscaled with LANCZOS - the aspect ratio is kept, so the
`object-fit: cover` crop on the pitch does not change.

  * a file that is already a JPEG is only replaced when the new encoding is
    strictly smaller, so the script can never make a photo bigger;
  * an upload that is not a JPEG (a few arrived as PNG or WebP renamed to .jpg,
    which the web server and the Android bundle then hand out with the wrong
    content type) is always converted, walking the quality down - never below
    QUALITY_FLOOR - until it fits inside the original file size.

    python3 tools/optimize_photos.py --dry-run     # report, change nothing
    python3 tools/optimize_photos.py               # rewrite the photos in place
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from glob import glob

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTO_DIR = os.path.join(ROOT, "public", "assets", "players")

MAX_SIDE = 400
QUALITY = 85
QUALITY_FLOOR = 65


def to_jpeg(im: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def encode(im: Image.Image, budget: int | None) -> tuple[bytes, bool, int]:
    """Return (jpeg bytes, was_resized, quality).

    `budget` is the file size the result must not exceed; None means "use
    QUALITY and let the caller decide" - it is only set for payloads that are
    not JPEGs and therefore have to be converted whatever happens.
    """
    im = im.convert("RGB")
    w, h = im.size
    resized = max(w, h) > MAX_SIDE
    if resized:
        s = MAX_SIDE / max(w, h)
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)

    quality = QUALITY
    data = to_jpeg(im, quality)
    while budget is not None and quality > QUALITY_FLOOR and len(data) > budget:
        quality = max(QUALITY_FLOOR, quality - 3)
        data = to_jpeg(im, quality)
    return data, resized, quality


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    args = ap.parse_args()

    paths = sorted(glob(os.path.join(PHOTO_DIR, "*.jpg")))
    if not paths:
        print(f"no photos in {PHOTO_DIR}", file=sys.stderr)
        return 1

    rewritten, kept, before_total = [], 0, 0
    for path in paths:
        name = os.path.basename(path)
        with open(path, "rb") as fh:
            original = fh.read()
        before_total += len(original)

        with Image.open(io.BytesIO(original)) as im:
            fmt, dims = im.format, im.size
            budget = None if fmt == "JPEG" else len(original)
            data, resized, quality = encode(im, budget)

        if fmt == "JPEG" and len(data) >= len(original):
            kept += 1
            continue

        notes = []
        if fmt != "JPEG":
            notes.append(f"{fmt} payload")
        if resized:
            notes.append(f"{dims[0]}x{dims[1]} -> {MAX_SIDE}px")
        if quality != QUALITY:
            notes.append(f"q{quality} to fit the original size")
        rewritten.append((name, len(original), len(data), ", ".join(notes)))
        if not args.dry_run:
            with open(path, "wb") as fh:
                fh.write(data)

    after_total = before_total - sum(b - a for _, b, a, _ in rewritten)
    print(f"{len(paths)} photos: {len(rewritten)} rewritten, {kept} left as-is"
          f"{' (dry run)' if args.dry_run else ''}")
    if rewritten:
        print(f"{before_total/1048576:.2f} MiB -> {after_total/1048576:.2f} MiB"
              f"  (-{(before_total-after_total)/1024:.0f} KiB)")
        print()
        for name, b, a, note in sorted(rewritten, key=lambda r: r[1] - r[2], reverse=True):
            extra = f"  [{note}]" if note else ""
            print(f"  {name:32s} {b:7d} -> {a:7d}  {(a-b)/b*100:+4.0f}%{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
