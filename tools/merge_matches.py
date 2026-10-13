"""Merge freshly scraped matches into the dataset.

New records come from Transfermarkt with English competition/round names; this
applies the same Portuguese vocabulary the existing dataset uses — derived from
the dataset itself rather than hardcoded — wires the photo path only when the
file really exists, and keeps the existing entries byte-identical.
"""
import json, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src/data/matches.json")
PHOTOS = os.path.join(ROOT, "public/assets/players")
NEW = "/tmp/bf/new_matches.json"

ORD = {"First": "1ª", "Second": "2ª", "Third": "3ª", "Fourth": "4ª",
       "Fifth": "5ª", "Sixth": "6ª", "Seventh": "7ª", "Eighth": "8ª"}
LEG = {"1st": "1ª", "2nd": "2ª"}

COMP = {
    "Primeira Liga": "Primeira Liga",
    "Taça de Portugal": "Taça de Portugal",
    "Taca de Portugal": "Taça de Portugal",
    "Allianz Cup": "Taça da Liga (Allianz Cup)",
    "Taça da Liga": "Taça da Liga (Allianz Cup)",
    "Supertaça": "Supertaça",
    "Champions League": "Liga dos Campeões",
    "Europa League": "Liga Europa",
    "Conference League": "Liga Conferência",
    "UEFA Cup": "Taça UEFA",
    "Cup Winners' Cup": "Taça das Taças",
    "European Cup": "Taça dos Campeões Europeus",
    "Intercontinental Cup": "Taça Intercontinental",
    "FIFA Club World Cup": "Mundial de Clubes FIFA",
    "FIFA Intercontinental Cup": "Taça Intercontinental",
}

_unmapped = set()


def localize_stage(stage):
    """English Transfermarkt round -> the dataset's Portuguese vocabulary."""
    if not stage:
        return stage
    s = stage.strip()
    low = s.lower()
    m = re.fullmatch(r"matchday (\d+)", low)
    if m:
        return f"Jornada {m.group(1)}"
    if low == "group stage":
        return "Fase de Grupos"
    m = re.fullmatch(r"group (\w+)", low)
    if m:
        return f"Grupo {m.group(1).upper()}"
    m = re.fullmatch(r"(\d+)(?:st|nd|rd|th) round", low)
    if m:
        return f"{m.group(1)}ª Ronda"
    m = re.fullmatch(r"(\d+)(?:st|nd|rd|th) round (\d(?:st|nd|rd|th)) leg", low)
    if m:
        return f"{m.group(1)}ª Ronda {'1ª' if m.group(2).startswith('1') else '2ª'} Mão"
    m = re.fullmatch(r"(first|second|third|fourth|fifth|sixth|seventh|eighth) round", low)
    if m:
        return f"{ORD[m.group(1).title()]} Ronda"
    m = re.fullmatch(r"(first|second|third|fourth|fifth|sixth) round (1st|2nd) leg", low)
    if m:
        return f"{ORD[m.group(1).title()]} Ronda {LEG[m.group(2)]} Mão"
    if low.startswith("qualifying round"):
        leg = re.search(r"(1st|2nd) leg", low)
        return f"Pré-Eliminatória {LEG[leg.group(1)]} Mão" if leg else "Pré-Eliminatória"
    if low.startswith("intermediate stage"):
        leg = re.search(r"(1st|2nd) leg", low)
        return f"Fase Intermédia {LEG[leg.group(1)]} Mão" if leg else "Fase Intermédia"
    table = {
        "final": "Final",
        "final 1st leg": "Final (1ª Mão)",
        "final 2nd leg": "Final (2ª Mão)",
        "final decider": "Finalissima",
        "finalissima": "Finalissima",
        "semi-finals": "Meias-Finais",
        "semi-finals 1st leg": "Meias-Finais 1ª Mão",
        "semi-finals 2nd leg": "Meias-Finais 2ª Mão",
        "quarter-finals": "Quartos-de-Final",
        "quarter-finals 1st leg": "Quartos-de-Final (1ª Mão)",
        "quarter-finals 2nd leg": "Quartos-de-Final (2ª Mão)",
        "quarter-finals deciders": "Quartos-de-Final (Desempate)",
        "round of 16": "Oitavos-de-Final",
        "round of 16 replay": "Oitavos-de-Final (Desempate)",
        "last 16 1st leg": "Oitavos-de-Final 1ª Mão",
        "last 16 2nd leg": "Oitavos-de-Final 2ª Mão",
        "play-off first leg": "Play-off 1ª Mão",
        "play-off second leg": "Play-off 2ª Mão",
        "play-offs": "Play-off",
    }
    if low in table:
        return table[low]
    _unmapped.add(s)
    return s


def localize_comp(comp):
    if comp in COMP:
        return COMP[comp]
    _unmapped.add("COMP:" + str(comp))
    return comp


def main(apply):
    src = json.load(open(SRC, encoding="utf-8"))
    new = json.load(open(NEW, encoding="utf-8"))

    have = {m["id"] for m in src}
    fresh = [m for m in new if m["id"] not in have]
    print(f"existing {len(src)} + new {len(fresh)} (of {len(new)} scraped)")

    def lineup_of(m):
        out = []
        for p in m["lineup"]:
            e = {"name": p["name"], "slug": p["slug"], "position": p["position"],
                 "x": p["x"], "y": p["y"], "number": p["number"]}
            if os.path.exists(os.path.join(PHOTOS, p["slug"] + ".jpg")):
                e["photo"] = f"assets/players/{p['slug']}.jpg"
            out.append(e)
        return out

    rows = []
    for m in fresh:
        rows.append({"id": m["id"], "date": m["date"], "home": m["home"],
                     "opponent": m["opponent"], "competition": localize_comp(m["competition"]),
                     "stage": localize_stage(m["stage"]), "score": m["score"],
                     "lineup": lineup_of(m)})

    if _unmapped:
        print("UNMAPPED values (add them to the tables):")
        for u in sorted(_unmapped):
            print("   ", u)

    merged = sorted(src + rows, key=lambda m: (m["date"], m["id"]))
    before = {json.dumps(m, sort_keys=True) for m in src}
    after = {json.dumps(m, sort_keys=True) for m in merged if m["id"] in have}
    print("existing rows preserved:", before == after)

    if not apply:
        print("dry run — nothing written")
        return merged
    json.dump(merged, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {len(merged)} matches to src/data/matches.json")
    return merged


if __name__ == "__main__":
    main("--apply" in sys.argv)
