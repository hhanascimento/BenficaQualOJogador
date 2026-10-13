#!/usr/bin/env python3
"""Point the dataset at the player photos that now exist on disk.

Every lineup entry carries a `photo` path. A player the scraper could not find a
free image for was written with an empty string, and the app then draws their
initials instead. When a photo is added later (fetched by hand, say) only the
file lands in public/assets/players - nothing rewrites the dataset - so the image
would sit there unused. This links those up:

    assets/players/<slug>.jpg  ->  the entry's `photo`, if the file exists

and reports any entry that still has no photo, so a missing image stays visible
instead of turning into a silent blank.

    python3 tools/link_photos.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data", "matches.json")
PHOTO_DIR = os.path.join(ROOT, "public", "assets", "players")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    matches = json.load(open(DATA, encoding="utf-8"))

    linked: dict[str, int] = {}
    still_missing: dict[str, int] = {}
    broken: dict[str, int] = {}
    for match in matches:
        for player in match.get("lineup", []):
            slug, photo = player.get("slug", ""), player.get("photo", "")
            if photo:
                if not os.path.exists(os.path.join(ROOT, "public", photo)):
                    broken[photo] = broken.get(photo, 0) + 1
                continue
            candidate = f"assets/players/{slug}.jpg"
            if slug and os.path.exists(os.path.join(ROOT, "public", candidate)):
                player["photo"] = candidate
                linked[candidate] = linked.get(candidate, 0) + 1
            else:
                still_missing[slug] = still_missing.get(slug, 0) + 1

    if linked and not args.dry_run:
        # the dataset is written exactly the way tools/merge_matches.py writes it
        with open(DATA, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(matches, ensure_ascii=False, indent=1))

    print(f"{sum(linked.values())} slots linked to {len(linked)} photos"
          f"{' (dry run)' if args.dry_run else ''}")
    for photo, n in sorted(linked.items()):
        print(f"  + {photo}  ({n} slot{'s' if n > 1 else ''})")
    print(f"{sum(still_missing.values())} slots ({len(still_missing)} players) without a photo")
    for slug, n in sorted(still_missing.items()):
        print(f"  - {slug}  ({n} slot{'s' if n > 1 else ''})")
    if broken:
        print(f"{sum(broken.values())} slots point at a file that does not exist:")
        for photo, n in sorted(broken.items()):
            print(f"  ! {photo}  ({n} slot{'s' if n > 1 else ''})")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
