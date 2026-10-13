#!/usr/bin/env python3
"""Merge the Wikidata pass and the cached-Wikipedia pass into src/data/hints.json.

The Wikipedia pass reads the page cache written by build_hints.py's prefetch
(/tmp/qj/ch_*.json), so it needs no network. For every player the richer of the
two records wins; the dataset supplies name/photo/era fallbacks.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_hints as B  # noqa: E402

# leagues/"ligas" come from Wikidata; the Wikipedia pass must not hit the network
B.resolve_club_countries = lambda titles: {}
B.search_titles = lambda *a, **k: []

ROOT = B.ROOT


POS_MAP = {
    "goalkeeper": "guarda-redes", "defender": "defesa", "centre back": "defesa central",
    "centre-back": "defesa central", "midfielder": "médio", "wing half": "médio",
    "defensive midfielder": "médio defensivo", "attacking midfielder": "médio ofensivo",
    "winger": "extremo", "forward": "avançado", "striker": "avançado", "attacker": "avançado",
    "full-back": "lateral", "full back": "lateral", "left back": "lateral-esquerdo",
    "right back": "lateral-direito", "meio-campista": "médio", "médio-ofensivo": "médio ofensivo",
    "zagueiro": "defesa", "goleiro": "guarda-redes", "atacante": "avançado", "meia": "médio",
}


def norm_position(p):
    p = (p or "").strip().lower()
    return POS_MAP.get(p, p)


def overlap(entry, years):
    if not entry or not entry.get("first"):
        return 0
    lo, hi = entry["first"] - 2, (entry.get("last") or entry["first"]) + 2
    return sum(1 for y in years if lo <= y <= hi)


def decade_bucket(year):
    d = max(1960, min(2020, year // 10 * 10))
    return f"{d}s"


def main():
    matches = json.load(open(os.path.join(ROOT, "src/data/matches.json"), encoding="utf-8"))
    players = {}
    for m in matches:
        y = int(m["date"][:4])
        for p in m["lineup"]:
            rec = players.setdefault(p["slug"], {"name": p["name"], "photo": p.get("photo"), "years": set()})
            rec["years"].add(y)

    known = {}
    pw = os.path.join(ROOT, "tools/players_wiki.json")
    if os.path.exists(pw):
        for slug, v in (json.load(open(pw, encoding="utf-8")).get("res") or {}).items():
            if v:
                known[slug] = {"lang": v.get("lang", "pt"), "title": v.get("title")}

    B.prefetch_all(players, known)

    wd = B._load("wd_hints_out.json", {}) or {}
    out = {}
    wp_count = 0
    for slug, rec in players.items():
        wp = None
        page = B.resolve_page(slug, rec["name"], None, known, rec["years"])
        if page.get("text"):
            facts = B.extract(page["text"])
            hints, meta = B.build_hints(facts, rec["years"])
            if hints:
                wp = {"name": rec["name"], "photo": rec["photo"],
                      "position": facts.get("position", ""), "nationality": facts.get("nationality", ""),
                      "first": meta["first"], "last": meta["last"],
                      "benficaSeasons": meta["benficaSeasons"], "benficaApps": meta["benficaApps"],
                      "benficaGoals": meta["benficaGoals"], "wiki": f"{page['lang']}:{page['title']}",
                      "hints": [{"label": l, "text": t} for l, t in hints]}
                wp_count += 1
        wdv = wd.get(slug)
        cands = [c for c in (wp, wdv) if c]
        if not cands:
            continue
        # prefer the record whose Benfica spell best matches the dataset years,
        # then the one with more hints, then the Wikipedia (name-resolved) entry
        entry = max(cands, key=lambda c: (overlap(c, rec["years"]), len(c["hints"]),
                                          1 if c is wp else 0))
        entry["position"] = norm_position(entry.get("position"))
        for h in entry["hints"]:
            if h["label"] == "Posição":
                h["text"] = f"Jogava na posição de {entry['position']}." if entry["position"] else h["text"]
        first = entry.get("first") or (min(rec["years"]) if rec["years"] else None)
        last = entry.get("last") or (max(rec["years"]) if rec["years"] else None)
        eras = sorted({decade_bucket(y) for y in range(first, (last or first) + 1)}) if first else []
        entry.update({"name": rec["name"], "photo": rec["photo"], "first": first, "last": last, "eras": eras})
        out[slug] = entry

    B._save("merged_hints.json", out)
    cov = len(out)
    rich = sum(1 for v in out.values() if len(v["hints"]) >= 8)
    print(f"wikipedia pass: {wp_count} players; merged: {cov}/{len(players)} "
          f"({rich} with >=8 hints)")
    missing = [players[s]["name"] for s in players if s not in out]
    print(f"still missing ({len(missing)}): " + ", ".join(missing))
    # how many eras each bucket
    from collections import Counter
    c = Counter(e for v in out.values() for e in v["eras"])
    print("eras:", dict(sorted(c.items())))


if __name__ == "__main__":
    main()
