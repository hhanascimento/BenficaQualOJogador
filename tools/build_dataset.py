import json, re, os, time, sys
import tm

OUT = "/tmp/bf/matches.json"
SEL = "/tmp/bf/selection.json"

COMP_MAP = [
    ("European Champion Clubs' Cup", "European Cup"),
    ("UEFA Champions League", "Champions League"),
    ("Liga Portugal", "Primeira Liga"),
    ("UEFA Europa League", "Europa League"),
    ("UEFA-Cup (- 2009)", "UEFA Cup"),
    ("UEFA Cup Winners' Cup (-1999)", "Cup Winners' Cup"),
    ("Supercup Candido de Oliveira", "Supertaça"),
    ("Intercontinental Cup", "Intercontinental Cup"),
    ("Taça de Portugal", "Taça de Portugal"),
    ("Taca de Portugal", "Taça de Portugal"),
    ("Taça da Liga", "Taça da Liga"),
    ("Taca da Liga", "Taça da Liga"),
]

def comp_name(raw):
    if not raw:
        return "Unknown"
    for k, v in COMP_MAP:
        if k.lower() in raw.lower():
            return v
    return raw

def slug_to_name(slug):
    parts = [p for p in slug.split("-") if p]
    return " ".join(p.capitalize() for p in parts)

def display_name(p):
    n = p["tmName"]
    if (not n) or "." in n or len(n) < 4:
        return slug_to_name(p["slug"])
    return n

def ypos(top):
    return round(100 - top, 1)

def code_for(x, y):
    if y < 30:
        return "GK"
    if y < 52:
        return "LB" if x < 35 else "RB" if x > 65 else "CB"
    if y < 72:
        return "CM" if 35 <= x <= 65 else "DM"
    return "LW" if x < 32 else "RW" if x > 68 else "ST"

def select():
    fx = json.load(open("/tmp/bf/tm_fixtures.json"))
    old = [f for f in fx if f["saison"] < "1996-1997" and f["formation"]]
    new = [f for f in fx if f["saison"] >= "1996-1997" and f["formation"]]
    new = sorted(new, key=lambda f: f["date"])
    want_new = max(0, 300 - len(old))
    step = len(new) / want_new
    picked_new = [new[int(i * step)] for i in range(want_new)]
    sel = old + picked_new
    sel.sort(key=lambda f: f["date"])
    json.dump(sel, open(SEL, "w"), ensure_ascii=False)
    return sel

def build_one(f):
    try:
        html = tm.get(f"https://www.transfermarkt.com/spielbericht/index/spielbericht/{f['id']}")
    except Exception as e:
        return None
    lu = tm.parse_lineups(html)
    ben = None
    for team, players in lu.items():
        if "benfica" in team.lower():
            ben = players
            break
    if not ben or len(ben) != 11:
        return None
    lineup = []
    for p in ben:
        x = round(p["left"], 1)
        y = ypos(p["top"])
        lineup.append({
            "name": display_name(p),
            "slug": p["slug"],
            "tmId": p["tmId"],
            "number": p["number"],
            "position": code_for(x, y),
            "x": x, "y": y,
        })
    home = "benfica" in f["home"].lower()
    opp = f["away"] if home else f["home"]
    score = (f["score"] or "").replace(":", "-") or None
    return {
        "id": f["id"],
        "date": f["date"],
        "home": home,
        "opponent": opp,
        "competition": comp_name(f["competition"]),
        "stage": f["round"],
        "score": score,
        "season": f["saison"],
        "lineup": lineup,
    }

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "select":
        sel = select()
        print("selected", len(sel))
    else:
        sel = json.load(open(SEL))
        budget = float(sys.argv[2]) if len(sys.argv) > 2 else 200
        t0 = time.time()
        matches = []
        done = set()
        if os.path.exists("/tmp/bf/_progress.json"):
            done = set(json.load(open("/tmp/bf/_progress.json")))
        url_of = lambda f: f"https://www.transfermarkt.com/spielbericht/index/spielbericht/{f['id']}"
        for f in sel:
            if not tm.is_cached(url_of(f)) and time.time() - t0 > budget:
                print("time budget reached; cached:", sum(1 for g in sel if tm.is_cached(url_of(g))), "of", len(sel))
                break
            m = build_one(f)
            done.add(f["id"])
            if m:
                matches.append(m)
        json.dump(sorted(done), open("/tmp/bf/_progress.json", "w"))
        json.dump(matches, open(OUT, "w"), ensure_ascii=False, indent=1)
        print("built", len(matches), "matches from", len(sel), "selected")
