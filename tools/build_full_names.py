#!/usr/bin/env python3
"""Give every player a fuller (accented) name for the round summary.

The dataset names a player by the short name he was known by ("Cruz"), while
the source slug spells the first name too but without accents ("fernando-cruz"
-> "Fernando Cruz"). The summary shows both, so this tool resolves the full,
correctly accented name:

1. Ask Wikidata for the people who played for Benfica (P54 = Q131499), with
   their Portuguese labels. A label is accepted for a player when its words
   match the name we know exactly, or - for a two-word name - describe one
   unique person whose surname (last word) matches too.
2. Otherwise rebuild the name from the slug, putting the accented spelling of
   the first name (ACCENTS) in front of the display name we already have, and
   falling back to plain capitalisation for names we cannot confirm.

Writes `fullName` into src/data/hints.json. Run with --refresh to re-query the
label cache (tools/wd_benfica_labels.json).

    python3 tools/build_full_names.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HINTS = ROOT / "src" / "data" / "hints.json"
LABELS = Path(__file__).resolve().parent / "wd_benfica_labels.json"

BENFICA = "Q131499"
SPARQL = f"""SELECT ?p ?pLabel WHERE {{
  ?p wdt:P54 wd:{BENFICA} .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}}"""

# Words the slug spells without accents. Only first names that actually appear
# in front of a display name are listed; the surname keeps the accented
# spelling the dataset already has.
ACCENTS = {
    "andre": "André", "angel": "Ángel", "antonio": "António", "cristian": "Cristián",
    "german": "Germán", "goncalo": "Gonçalo", "joao": "João", "jose": "José",
    "luis": "Luís", "nelson": "Nélson", "nicolas": "Nicolás", "raul": "Raúl",
    "ruben": "Rúben", "tomas": "Tomás", "ze": "Zé",
}
# Particles stay lower-case inside a name ("Manuel dos Santos").
LOWER = {"de", "da", "do", "dos", "das", "di", "del", "van", "von", "y", "el"}
# Names the slug-and-map route cannot rebuild on its own.
OVERRIDES = {
    "jean-clair-todibo": "Jean-Clair Todibo",
}

PARTICLES = {"de", "da", "do", "dos", "das", "e", "di", "del", "la", "le", "van", "von", "el", "y"}


def fold(value: str) -> str:
    """Lower-case, unaccented, punctuation-free (matching-shaped)."""
    value = unicodedata.normalize("NFD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def tight(value: str) -> str:
    """Like fold() but with the spaces removed, so O'Brien == OBrien."""
    return fold(value).replace(" ", "")


def words(value: str) -> list[str]:
    return [w for w in fold(value).split() if w and w not in PARTICLES]


def read_words(slug: str) -> list[str]:
    """The name a slug spells out, capitalised ("fernando-cruz" -> Fernando Cruz)."""
    return [w[:1].upper() + w[1:] for w in slug.split("-") if w]


def fetch_labels(refresh: bool) -> list[str]:
    if LABELS.exists() and not refresh:
        return [r["pLabel"]["value"] for r in json.loads(LABELS.read_text(encoding="utf-8"))]
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": SPARQL, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": "qualojogador/1.0 (personal fan project)",
        "Accept": "application/sparql-results+json",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                rows = json.load(r)["results"]["bindings"]
            LABELS.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            return [row["pLabel"]["value"] for row in rows]
        except Exception as exc:  # noqa: BLE001 - WDQS throttles, back off and retry
            print(f"  labels fetch failed ({exc}), retrying")
            time.sleep(5 * (attempt + 1))
    raise SystemExit("could not read the Wikidata label cache or the SPARQL endpoint")


def wikidata_names(labels: list[str], hints: dict) -> dict[str, str]:
    """Players whose Wikidata label spells out more name words than the dataset."""
    exact: dict[tuple, list[str]] = defaultdict(list)
    for label in sorted(set(labels)):
        exact[tuple(sorted(set(words(label))))].append(label)

    def subsequence(target: list[str], label: list[str]) -> bool:
        stream = iter(label)
        return all(any(w == want for w in stream) for want in target)

    out: dict[str, str] = {}
    for slug, record in hints.items():
        spelled = read_words(slug)
        target = words(" ".join(spelled)) if len(spelled) > 1 else words(record["name"])
        if not target:
            continue
        found = exact.get(tuple(sorted(set(target))))
        if not found and len(spelled) > 1:
            # one unique person carrying the same words, ending in the same surname
            candidates = [l for l in exact_surnames(exact, target[-1])
                          if words(l)[-1] == target[-1] and subsequence(target, words(l))]
            found = candidates if len(candidates) == 1 else None
        if not found:
            continue
        best = min(set(found), key=lambda l: (len(words(l)), len(l)))
        if len(set(words(best))) > len(set(words(record["name"]))):
            out[slug] = best
    return out


def exact_surnames(exact: dict[tuple, list[str]], surname: str) -> list[str]:
    """Every cached label carrying `surname` in its words (caller checks it is last)."""
    return [label for key, labels in exact.items() if surname in key for label in labels]


def spelled_name(slug: str, display: str) -> str | None:
    """Rebuild the full name from the slug, keeping the accented display name."""
    spelled = read_words(slug)
    if len(spelled) < 2:
        return None
    if tight(" ".join(spelled)) == tight(display):
        return None                                  # display already spells it out
    folded = tight(display)
    for size in range(len(spelled), 0, -1):          # longest suffix that is the display
        if tight(" ".join(spelled[len(spelled) - size:])) != folded:
            continue
        prefix = spelled[:len(spelled) - size]
        if not prefix:
            return None
        rebuilt = [ACCENTS.get(w.lower(), w) for w in prefix]
        while rebuilt and rebuilt[-1].lower() in LOWER and fold(rebuilt[-1]) == fold(display.split()[0]):
            rebuilt.pop()                            # "Manuel Dos" + "dos Santos"
        rebuilt = [w.lower() if w.lower() in LOWER else w for w in rebuilt]
        if not rebuilt:
            return None
        return " ".join(rebuilt) + " " + display
    return None


def main() -> None:
    refresh = "--refresh" in sys.argv
    hints = json.loads(HINTS.read_text(encoding="utf-8"))
    labels = fetch_labels(refresh)
    confirmed = wikidata_names(labels, hints)

    counts = {"wikidata": 0, "slug": 0, "none": 0}
    for slug, record in hints.items():
        name = OVERRIDES.get(slug) or confirmed.get(slug) or spelled_name(slug, record["name"])
        if not name:
            record.pop("fullName", None)
            counts["none"] += 1
        else:
            record["fullName"] = name
            counts["wikidata" if slug in confirmed else "slug"] += 1

    HINTS.write_text(json.dumps(hints, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(hints)} players: {counts['wikidata']} from Wikidata, "
          f"{counts['slug']} from the slug, {counts['none']} already complete")


if __name__ == "__main__":
    main()
