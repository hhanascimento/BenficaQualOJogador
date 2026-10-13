#!/usr/bin/env python3
"""Build src/data/hints.json for "Benfica - Qual o Jogador" from Wikidata.

Streaming + memory-safe: items that list Sport Lisboa e Benfica (Q131499) as a
P54 "member of sports team" are fetched in batches of 50 through the plain
Wikidata API (WDQS is rate-limited), reduced to compact records and cached under
/tmp/qj so the run is resumable. Each dataset player is matched to an item by
name and its career is turned into up to 11 ordered hints.

    python3 tools/build_hints_wd.py
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hints import ROOT, norm, tokens, join_pt, decades_of, decade_label, COUNTRY  # noqa: E402

CACHE = "/tmp/qj"
os.makedirs(CACHE, exist_ok=True)
UA = "BenficaQualJogador-fan-game/1.0 (personal hobby project)"
BENFICA = "Q131499"
_last = [0.0]


def _load(p, d=None):
    fp = os.path.join(CACHE, p)
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as fh:
            return json.load(fh)
    return d


def _save(p, v):
    tmp = os.path.join(CACHE, p + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(v, fh, ensure_ascii=False)
    os.replace(tmp, os.path.join(CACHE, p))


def api(params):
    params = dict(params)
    params["format"] = "json"
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        gap = 0.35 - (time.time() - _last[0])
        if gap > 0:
            time.sleep(gap)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.load(r)
            _last[0] = time.time()
            return data
        except urllib.error.HTTPError as e:
            time.sleep(int(e.headers.get("Retry-After") or 0) or 3 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return {}


def all_benfica_qids():
    cached = _load("wd_qids.json")
    if cached:
        return cached
    qids, offset = [], 0
    while True:
        d = api({"action": "query", "list": "search", "srsearch": f"haswbstatement:P54={BENFICA}",
                 "srlimit": 50, "srnamespace": 0, "sroffset": offset})
        hits = (d.get("query") or {}).get("search") or []
        qids += [h["title"] for h in hits]
        total = (d.get("query") or {}).get("searchinfo", {}).get("totalhits", 0)
        offset += 50
        if len(hits) < 50 or offset >= total:
            break
    _save("wd_qids.json", qids)
    return qids


def qval(st, prop):
    q = (st.get("qualifiers") or {}).get(prop)
    return q[0].get("datavalue", {}).get("value") if q else None


def year_of(v):
    if isinstance(v, dict):
        m = re.match(r"[+-](\d{4})", v.get("time") or "")
        return int(m.group(1)) if m else None
    return None


def num_of(v):
    if isinstance(v, dict) and v.get("amount") is not None:
        try:
            return int(float(v["amount"]))
        except (TypeError, ValueError):
            return None
    if isinstance(v, (int, float)):
        return int(v)
    return None


def compact_entity(ent):
    claims = ent.get("claims") or {}
    labels = ent.get("labels") or {}
    aliases = ent.get("aliases") or {}
    rows = []
    for st in claims.get("P54", []):
        v = st.get("mainsnak", {}).get("datavalue", {}).get("value")
        if not (isinstance(v, dict) and v.get("id")):
            continue
        rows.append([v["id"], year_of(qval(st, "P580")), year_of(qval(st, "P582")),
                     num_of(qval(st, "P1350")), num_of(qval(st, "P1351"))])
    nat = claims.get("P27", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
    pos = claims.get("P413", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
    dob = year_of(claims.get("P569", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value"))
    return {
        "label": (labels.get("pt") or labels.get("en") or {}).get("value"),
        "aliases": [a["value"] for lang in ("pt", "en") for a in (aliases.get(lang) or [])][:12],
        "nat": nat.get("id") if isinstance(nat, dict) else None,
        "pos": pos.get("id") if isinstance(pos, dict) else None,
        "dob": dob, "rows": rows,
    }


def build_entities(qids):
    cache = _load("wd_compact.json", {}) or {}
    todo = [q for q in qids if q not in cache]
    print(f"entities: {len(cache)} cached, {len(todo)} to fetch", flush=True)
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        d = api({"action": "wbgetentities", "ids": "|".join(chunk),
                 "props": "claims|labels|aliases", "languages": "pt|en"})
        for qid, ent in (d.get("entities") or {}).items():
            if not qid.startswith("-"):
                cache[qid] = compact_entity(ent)
        _save("wd_compact.json", cache)
        print(f"  entities {min(i+50, len(todo))}/{len(todo)}", flush=True)
    return cache


def build_teams(team_qids):
    cache = _load("wd_teams.json", {}) or {}
    todo = [q for q in team_qids if q not in cache]
    print(f"teams: {len(cache)} cached, {len(todo)} to fetch", flush=True)
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        d = api({"action": "wbgetentities", "ids": "|".join(chunk),
                 "props": "labels|claims", "languages": "pt|en"})
        for qid, ent in (d.get("entities") or {}).items():
            if qid.startswith("-"):
                continue
            labels = ent.get("labels") or {}
            cq = (ent.get("claims", {}).get("P17") or [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
            cache[qid] = {"label": (labels.get("pt") or labels.get("en") or {}).get("value"),
                          "country": cq.get("id") if isinstance(cq, dict) else None}
        _save("wd_teams.json", cache)
        print(f"  teams {min(i+50, len(todo))}/{len(todo)}", flush=True)


def build_labels(qids):
    cache = _load("wd_labels.json", {}) or {}
    todo = [q for q in qids if q and q not in cache]
    for i in range(0, len(todo), 50):
        d = api({"action": "wbgetentities", "ids": "|".join(todo[i:i + 50]),
                 "props": "labels", "languages": "pt|en"})
        for qid, ent in (d.get("entities") or {}).items():
            labels = ent.get("labels") or {}
            cache[qid] = (labels.get("pt") or labels.get("en") or {}).get("value")
        _save("wd_labels.json", cache)
    print(f"  country labels: {len(cache)}", flush=True)
    return cache


COUNTRY_ADJ = {}
for _c, _a in COUNTRY.values():
    COUNTRY_ADJ.setdefault(_c.lower(), _a)

POS_FIX = {"zagueiro": "defesa", "defesa central": "defesa central", "meio-campista": "médio",
           "meia": "médio", "goleiro": "guarda-redes", "atacante": "avançado", "volante": "médio defensivo",
           "lateral-esquerdo": "lateral-esquerdo", "lateral-direito": "lateral-direito",
           "ponta": "extremo", "ala": "extremo", "centroavante": "avançado", "meio-campo": "médio"}


def fix_position(p):
    p = (p or "").strip().lower()
    return POS_FIX.get(p, p)


NATIONAL = re.compile(r"(national|sele[çc]|olympic|ol[íi]mpic|under-?\s?\d|sub-?\s?\d|\bU\s?\d\d\b|women|feminin|B team)", re.I)
ADJ = {}
for _, adj in COUNTRY.values():
    ADJ.setdefault(adj, adj)


def facts_for(ent, teams, country_labels):
    clubs, nat = [], []
    for team, s, e, apps, goals in ent["rows"]:
        tinfo = teams.get(team, {})
        name = tinfo.get("label") or ""
        rec = {"team": team, "name": name, "country": country_labels.get(tinfo.get("country"), ""),
               "start": s, "end": e or s, "apps": apps, "goals": goals}
        (nat if NATIONAL.search(name) else clubs).append(rec)
    benfica = [c for c in clubs if c["team"] == BENFICA or "benfica" in norm(c["name"])]
    senior = [n for n in nat if not re.search(r"(under|sub|U\s?\d\d|olympic|ol[íi]mpic|B team|women|feminin)", n["name"], re.I)]
    starts = [c["start"] for c in clubs if c["start"]]
    return {
        "position": "",
        "nationality": country_labels.get(ent.get("nat")),
        "pos_qid": ent.get("pos"),
        "birthYear": ent.get("dob"),
        "startYear": min(starts) if starts else None,
        "clubsCount": len({c["team"] for c in clubs}) or None,
        "leagues": len({c["country"] for c in clubs if c["country"]}) or None,
        "first": min((b["start"] for b in benfica if b["start"]), default=None),
        "last": max((b["end"] for b in benfica if b["end"]), default=None),
        "benficaSeasons": sum(max(1, (b["end"] - b["start"])) if b["start"] and b["end"] else 1 for b in benfica) or None,
        "benficaApps": sum(b["apps"] for b in benfica if b["apps"]) or None,
        "benficaGoals": sum(b["goals"] for b in benfica if b["goals"]) or None,
        "intlCaps": sum(n["apps"] for n in senior if n["apps"]) or None,
    }


def hints_from(f):
    h = []
    if f.get("nationality"):
        adj = COUNTRY_ADJ.get(f["nationality"].lower())
        h.append(("Nacionalidade", f"Tem nacionalidade {adj}." if adj else f"É de {f['nationality']}."))
    if f.get("position"):
        h.append(("Posição", f"Jogava na posição de {f['position']}."))
    if f.get("first"):
        ds = decades_of(f["first"], f["last"] or f["first"])
        h.append(("Época", f"No Benfica, jogou nos anos {join_pt([decade_label(d) for d in ds])}."))
    if f.get("startYear"):
        h.append(("Estreia", f"Começou a carreira profissional em {f['startYear']}."))
    if f.get("clubsCount"):
        h.append(("Clubes", f"Passou por {f['clubsCount']} clubes ao longo da carreira."))
    if f.get("leagues") and f["leagues"] > 1:
        h.append(("Ligas", f"Representou clubes de {f['leagues']} ligas diferentes."))
    if f.get("benficaSeasons"):
        h.append(("Temporadas", f"Fez {f['benficaSeasons']} temporadas no Benfica."))
    if f.get("benficaApps"):
        h.append(("Jogos", f"Disputou {f['benficaApps']} jogos pelo Benfica."))
    if f.get("benficaGoals"):
        h.append(("Golos", f"Marcou {f['benficaGoals']} golos pelo Benfica."))
    if f.get("intlCaps"):
        h.append(("Internacionalizações", f"Somou {f['intlCaps']} internacionalizações."))
    if f.get("birthYear"):
        h.append(("Nascimento", f"Nasceu em {f['birthYear']}."))
    return h


def main():
    matches = json.load(open(os.path.join(ROOT, "src/data/matches.json"), encoding="utf-8"))
    players = {}
    for m in matches:
        y = int(m["date"][:4])
        for p in m["lineup"]:
            rec = players.setdefault(p["slug"], {"name": p["name"], "photo": p.get("photo"), "years": set()})
            rec["years"].add(y)

    qids = all_benfica_qids()
    print(f"{len(qids)} Benfica items", flush=True)
    ents = build_entities(qids)
    team_qids = sorted({r[0] for e in ents.values() for r in e["rows"]})
    build_teams(team_qids)
    teams = _load("wd_teams.json", {}) or {}
    country_labels = build_labels({t.get("country") for t in teams.values() if t.get("country")})
    pos_labels = build_labels({e.get("pos") for e in ents.values() if e.get("pos")})

    index = {}
    for qid, e in ents.items():
        for nm in [e.get("label")] + e.get("aliases", []):
            if nm:
                index.setdefault(norm(nm), set()).add(qid)

    fact_cache = {}
    out, matched = {}, 0
    for slug, rec in players.items():
        keys = [norm(rec["name"]), norm(slug.replace("-", " "))]
        cand = set()
        for k in keys:
            cand |= index.get(k, set())
        if not cand:
            for k in keys:
                want = set(tokens(k))
                if not want:
                    continue
                for nm, qs in index.items():
                    if want <= set(nm.split()):
                        cand |= qs
        best, best_score = None, 0
        for qid in cand:
            if qid not in fact_cache:
                f = facts_for(ents[qid], teams, country_labels)
                f["position"] = fix_position(pos_labels.get(ents[qid].get("pos")) or "")
                fact_cache[qid] = f
            f = fact_cache[qid]
            score = sum(1 for y in rec["years"] if f["first"] and f["first"] - 4 <= y <= (f["last"] or f["first"]) + 4)
            score += 2 if norm(rec["name"]) == norm(ents[qid].get("label") or "") else 0
            if score > best_score:
                best, best_score = qid, score
        if best and best_score > 0:
            f = fact_cache[best]
            out[slug] = {
                "name": rec["name"], "photo": rec["photo"],
                "position": f["position"], "nationality": f["nationality"],
                "first": f["first"], "last": f["last"],
                "benficaSeasons": f["benficaSeasons"], "benficaApps": f["benficaApps"],
                "benficaGoals": f["benficaGoals"], "wiki": f"wd:{best}",
                "hints": [{"label": l, "text": t} for l, t in hints_from(f)],
            }
            matched += 1
    _save("wd_hints_out.json", out)
    good = sum(1 for v in out.values() if len(v["hints"]) >= 6)
    print(f"matched {matched}/{len(players)}; {good} with >=6 hints; {sum(1 for v in out.values() if len(v['hints'])>0)} with hints")
    miss = [players[s]["name"] for s in players if s not in out]
    print(f"unmatched ({len(miss)}): " + ", ".join(miss[:60]))
    for slug in list(players)[:2] + ["eusebio", "rui-costa"]:
        if slug in out:
            print(slug, "->", json.dumps(out[slug]["hints"], ensure_ascii=False)[:300])


if __name__ == "__main__":
    main()
