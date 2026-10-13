#!/usr/bin/env python3
"""Top up src/data/hints.json so every player has exactly 11 hints.

The base hints come from tools/build_hints_wd.py + tools/merge_hints.py. A chunk
of the roster is missing one or two of them (goals/caps are often absent for
defenders; "ligas" only fits well-travelled players). This pass keeps those
hints and appends the next best *real* career facts until everyone reaches 11:

    Clube de estreia · Fim de carreira · Clube onde terminou · Altura ·
    Idade de estreia pelo Benfica

A handful of players slipped through the original name-matching entirely (their
pages use the manager infobox, or an inline {{Infobox football biography}} the
first pass could not parse, or they were matched to a namesake on Wikidata).
For those this pass re-reads the same Wikipedia page with a stricter parser and
re-checks the Wikidata match.

Everything is served from the /tmp/qj cache (no network):

    python3 tools/build_hints_final.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_hints as B  # noqa: E402
from build_hints_wd import facts_for, fix_position, BENFICA, NATIONAL  # noqa: E402

# The Wikipedia pass must stay offline: page cache only.
B.resolve_club_countries = lambda titles: {}
B.search_titles = lambda *a, **k: []

ROOT = B.ROOT
TARGET = 11

POS_FIXES = {
    "right-back": "lateral-direito", "right back": "lateral-direito",
    "left-back": "lateral-esquerdo", "left back": "lateral-esquerdo",
    "full-back": "lateral", "full back": "lateral",
    "centre-back": "defesa central", "centre back": "defesa central",
    "defensor": "defesa", "defender": "defesa", "zagueiro": "defesa",
    "goalkeeper": "guarda-redes", "goleiro": "guarda-redes",
    "midfielder": "médio", "wing half": "médio", "meio-campista": "médio", "meia": "médio",
    "winger": "extremo", "ponta": "extremo", "ala": "extremo",
    "forward": "avançado", "striker": "avançado", "attacker": "avançado",
    "atacante": "avançado", "centroavante": "avançado", "ponta de lança": "avançado",
    "defensive midfielder": "médio defensivo", "volante": "médio defensivo",
    "attacking midfielder": "médio ofensivo",
}

CODE_POS = {"GR": "guarda-redes", "DF": "defesa", "MC": "médio", "AV": "avançado"}

INFOBOXES = ["Info/Futebolista", "Info/futebolista", "Info/Treinador de futebol",
             "Info/Treinador", "Infobox football biography", "Infobox football manager",
             "Infobox footballer"]


# English / historical country names seen on the pages -> pt country name.
COUNTRY_ALIAS = {
    "uruguay": "Uruguai", "brazil": "Brasil", "serbia": "Sérvia", "portugal": "Portugal",
    "argentina": "Argentina", "spain": "Espanha", "france": "França", "italy": "Itália",
    "england": "Inglaterra", "netherlands": "Países Baixos", "germany": "Alemanha",
    "belgium": "Bélgica", "croatia": "Croácia", "chile": "Chile", "colombia": "Colômbia",
    "mexico": "México", "paraguay": "Paraguai", "peru": "Peru", "nigeria": "Nigéria",
    "morocco": "Marrocos", "algeria": "Argélia", "russia": "Rússia", "ukraine": "Ucrânia",
    "sweden": "Suécia", "denmark": "Dinamarca", "norway": "Noruega", "poland": "Polónia",
    "greece": "Grécia", "turkey": "Turquia", "japan": "Japão", "south korea": "Coreia do Sul",
    "australia": "Austrália", "canada": "Canadá", "usa": "Estados Unidos",
    "united states": "Estados Unidos", "yugoslavia": "Sérvia",
    "socialist federal republic of yugoslavia": "Sérvia", "serbia and montenegro": "Sérvia",
    "mozambique": "Moçambique", "angola": "Angola", "cape verde": "Cabo Verde",
    "guinea-bissau": "Guiné-Bissau", "ivory coast": "Costa do Marfim", "senegal": "Senegal",
    "ghana": "Gana", "cameroon": "Camarões", "tunisia": "Tunísia", "egypt": "Egito",
    "israel": "Israel", "scotland": "Escócia", "wales": "País de Gales", "ireland": "Irlanda",
    "republic of ireland": "Irlanda", "romania": "Roménia", "austria": "Áustria",
    "switzerland": "Suíça", "venezuela": "Venezuela", "bolivia": "Bolívia",
    "ecuador": "Equador", "costa rica": "Costa Rica", "cuba": "Cuba", "honduras": "Honduras",
}

NAME_TO_ADJ = {}
for _code, (_country, _adj) in B.COUNTRY.items():
    NAME_TO_ADJ.setdefault(B.norm(_country), _adj)


def tidy_position(p):
    p = re.sub(r"\s*\([^)]*\)", "", (p or "").strip().lower())
    p = re.sub(r"^ex[- ]", "", p)
    return POS_FIXES.get(p, p)


def clean_club(name):
    name = re.sub(r"\s*\([^)]*\)\s*$", "", (name or "").strip())
    return name.strip(" .,;·")


def plural(n, one, many):
    return one if n == 1 else many


def find_infobox(txt):
    for name in INFOBOXES:
        tpl = B.find_template(txt, [name])
        if tpl:
            return tpl
    return None


def split_top(body):
    """Split an infobox body on top-level '|' (ignoring [[ ]] and {{ }})."""
    parts, cur, sq, cu, i = [], "", 0, 0, 0
    while i < len(body):
        if body.startswith("[[", i):
            sq += 1; cur += "[["; i += 2; continue
        if body.startswith("]]", i):
            sq = max(0, sq - 1); cur += "]]"; i += 2; continue
        if body.startswith("{{", i):
            cu += 1; cur += "{{"; i += 2; continue
        if body.startswith("}}", i):
            cu = max(0, cu - 1); cur += "}}"; i += 2; continue
        if body[i] == "|" and sq == 0 and cu == 0:
            parts.append(cur); cur = ""; i += 1; continue
        cur += body[i]; i += 1
    parts.append(cur)
    return parts


def parse_fields(tpl):
    out = {}
    for part in split_top(tpl[2:-2]):
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip().lower()
        if k and k not in out:
            out[k] = v.strip()
    return out


def year_of(v):
    m = re.search(r"\b(1[89]\d\d|20\d\d)\b", v or "")
    return int(m.group(1)) if m else None


def country_in(text):
    plain = B.clean_value(text)
    plain = re.sub(r"\s*(national|olympic|under[-\s]?\d+|U\d\d+|B team|women).*$", "", plain, flags=re.I)
    norm = B.norm(plain)
    best = ""
    for code, (country, adj) in B.COUNTRY.items():
        if B.norm(country) and re.search(r"\b" + re.escape(B.norm(country)) + r"\b", norm):
            if len(country) > len(best):
                best = country
    if not best:
        for en, country in sorted(COUNTRY_ALIAS.items(), key=lambda kv: -len(kv[0])):
            if re.search(r"\b" + re.escape(en) + r"\b", norm):
                best = country
                break
    if best:
        return best, NAME_TO_ADJ.get(B.norm(best))
    return (plain or None), None


def parse_page(txt):
    """Career facts from a Wikipedia page (inline + manager infoboxes)."""
    tpl = find_infobox(txt)
    if not tpl:
        return None
    f = parse_fields(tpl)
    pos = tidy_position(B.first_position(f.get("posição") or f.get("posicao") or f.get("position") or ""))
    birth = None
    for key in ("datadenascimento", "nascimento_data", "datanascimento", "birth_date", "nascimento"):
        if f.get(key):
            birth = year_of(f[key])
            if birth:
                break
    country, adj = country_in(f.get("paisnatal") or f.get("birth_country") or f.get("country") or "")
    if not country:
        country, adj = country_in(f.get("nationalteam1") or f.get("nationalteam") or "")
    height = None
    hm = re.search(r"(\d)[.,](\d\d)", B.clean_value(f.get("altura") or f.get("height") or ""))
    if hm:
        height = f"{hm.group(1)},{hm.group(2)} m"
    clubs = []
    if f.get("clubes"):
        years = B.split_list(f.get("ano") or f.get("anos") or f.get("anoclubes") or "")
        for i, seg in enumerate(B.split_list(f["clubes"])):
            nm, _ = B.club_of(seg)
            s, e = B.years_of(years[i] if i < len(years) else "")
            if nm:
                clubs.append({"name": clean_club(B.clean_value(nm)), "start": s, "end": e})
    else:
        for i in range(1, 26):
            if f.get(f"clubs{i}"):
                nm, _ = B.club_of(f[f"clubs{i}"])
                s, e = B.years_of(f.get(f"years{i}") or "")
                if nm:
                    clubs.append({"name": clean_club(B.clean_value(nm)), "start": s, "end": e})
    return {"position": pos, "country": country, "adj": adj, "birthYear": birth,
            "clubs": [c for c in clubs if c["name"]], "height": height}


def benfica_overlap(clubs, years):
    hit = 0
    for c in clubs:
        if "benfica" in B.norm(c.get("name") or "") and c.get("start"):
            end = c.get("end") or c["start"]
            hit += sum(1 for y in years if (c["start"] - 1) <= y <= end + 1)
    return hit


def match_wd(rec, wd_compact):
    """The Wikidata item whose name contains every word of the player's name,
    with a Benfica spell overlapping the dataset years. Exact names win."""
    toks = set(B.tokens(rec["name"]))
    if not toks:
        return None
    best, best_score = None, (0, 0)
    for qid, ent in wd_compact.items():
        names = [n for n in [ent.get("label")] + ent.get("aliases", []) if n]
        if not any(toks <= set(B.tokens(n)) for n in names):
            continue
        ov = sum(1 for y in rec["years"]
                 for team, s, e, a, g in ent["rows"]
                 if team == BENFICA and (s or e) and (s or e) - 1 <= y <= (e or s) + 1)
        if ov <= 0:
            continue
        exact = any(B.norm(n) == B.norm(rec["name"]) for n in names)
        if (1 if exact else 0, ov) > best_score:
            best, best_score = qid, (1 if exact else 0, ov)
    return best


def clubs_from_teams(rows, teams):
    out = []
    for team, s, e, a, g in rows:
        name = (teams.get(team) or {}).get("label") or ""
        if name and not NATIONAL.search(name):
            out.append({"name": clean_club(name), "start": s, "end": e})
    return out


def extra_hints(clubs, birth, height, bf_first):
    """The padding facts, most useful first, deduped by club name."""
    seen, dated = set(), []
    for c in clubs:
        key = B.norm(c.get("name") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        dated.append(c)
    timed = sorted([c for c in dated if c.get("start")], key=lambda c: c["start"])
    ends = [c["end"] for c in dated if c.get("end")]
    out = []
    if timed:
        out.append(("Clube de estreia", f"O primeiro clube da carreira foi o {timed[0]['name']}."))
    if ends:
        out.append(("Fim de carreira", f"Terminou a carreira em {max(ends)}."))
    if timed:
        last = max(timed, key=lambda c: (c.get("end") or c["start"], c["start"]))
        if last["name"] != timed[0]["name"]:
            out.append(("Clube onde terminou", f"O último clube da carreira foi o {last['name']}."))
    if height:
        out.append(("Altura", f"Mede {height} de altura."))
    if birth and bf_first and 15 <= bf_first - birth <= 40:
        out.append(("Idade de estreia", f"Estreou-se pelo Benfica com {bf_first - birth} anos."))
    return out


def top_up(entry, additions):
    used = {h["label"] for h in entry["hints"]}
    for label, text in additions:
        if len(entry["hints"]) >= TARGET:
            break
        if label in used:
            continue
        used.add(label)
        entry["hints"].append({"label": label, "text": text})


def full_facts(source, clubs, rec):
    """The full ordered hint set from a trusted source (Wikidata or page)."""
    out = []
    if source.get("adj"):
        out.append(("Nacionalidade", f"Tem nacionalidade {source['adj']}."))
    elif source.get("country"):
        out.append(("Nacionalidade", f"É de {source['country']}."))
    if source.get("position"):
        out.append(("Posição", f"Jogava na posição de {source['position']}."))
    if source.get("birthYear"):
        out.append(("Nascimento", f"Nasceu em {source['birthYear']}."))
    distinct = {B.norm(c["name"]) for c in clubs if c.get("name")}
    if len(distinct) > 1:
        out.append(("Clubes", f"Passou por {len(distinct)} clubes ao longo da carreira."))
    if source.get("caps"):
        out.append(("Internacionalizações", f"Somou {source['caps']} internacionalizações."))
    return out


def dataset_hints(rec):
    out = []
    codes = rec.get("codes") or {}
    if codes:
        code = max(codes, key=codes.get)
        if code in CODE_POS:
            out.append(("Perfil", f"Alinhava habitualmente como {CODE_POS[code]}."))
    seasons = len(rec.get("years") or [])
    if seasons:
        out.append(("Temporadas", f"Fez {seasons} {plural(seasons, 'temporada', 'temporadas')} no Benfica."))
    return out


def main():
    matches = json.load(open(os.path.join(ROOT, "src/data/matches.json"), encoding="utf-8"))
    recs = {}
    for m in matches:
        y = int(m["date"][:4])
        for p in m["lineup"]:
            rec = recs.setdefault(p["slug"], {"name": p["name"], "years": set(), "codes": {}})
            rec["years"].add(y)
            if p.get("position"):
                rec["codes"][p["position"]] = rec["codes"].get(p["position"], 0) + 1

    known = {}
    for slug, v in (json.load(open(os.path.join(ROOT, "tools/players_wiki.json"), encoding="utf-8")).get("res") or {}).items():
        if v:
            known[slug] = {"lang": v.get("lang", "pt"), "title": v.get("title")}
    B.prefetch_all(recs, known)

    wd_compact = B._load("wd_compact.json", {}) or {}
    wd_teams = B._load("wd_teams.json", {}) or {}
    wd_labels = B._load("wd_labels.json", {}) or {}
    wd_out = B._load("wd_hints_out.json", {}) or {}

    book = json.load(open(os.path.join(ROOT, "src/data/hints.json"), encoding="utf-8"))
    fixed_positions = fixed_counts = 0

    for slug, entry in book.items():
        rec = recs.get(slug) or {"name": entry["name"], "years": set(), "codes": {}}
        rec["first"] = entry.get("first")
        rec["last"] = entry.get("last")
        years = rec["years"]

        # tidy the wording of the existing hints
        for h in entry.get("hints", []):
            if h["label"] == "Posição":
                pos = tidy_position(entry.get("position") or "")
                if pos:
                    entry["position"] = pos
                    if h["text"] != f"Jogava na posição de {pos}.":
                        h["text"] = f"Jogava na posição de {pos}."
                        fixed_positions += 1
            m = re.match(r"^(Passou por|Fez|Disputou|Marcou|Somou) (\d+) (\w+)", h["text"])
            if m and m.group(2) == "1":
                sing = {"clubes": "clube", "temporadas": "temporada", "jogos": "jogo",
                        "golos": "golo", "internacionalizações": "internacionalização"}.get(m.group(3))
                if sing:
                    h["text"] = h["text"].replace(f"1 {m.group(3)}", f"1 {sing}", 1)
                    fixed_counts += 1

        page = B.resolve_page(slug, rec["name"], None, known, years)
        text = page.get("text") or ""
        page_facts = parse_page(text) if text else None
        page_trusted = bool(page_facts) and benfica_overlap(page_facts["clubs"], years) > 0

        qid = match_wd(rec, wd_compact)
        wf = None
        if qid:
            wf = facts_for(wd_compact[qid], wd_teams, wd_labels)
            wf["position"] = tidy_position(wd_labels.get(wd_compact[qid].get("pos")) or "")
            wf["country"], wf["adj"] = country_in(wf.get("nationality") or "")

        # Trust the page when it clearly is the right person, else Wikidata.
        if page_trusted:
            clubs = page_facts["clubs"]
            birth = page_facts["birthYear"] or (wf or {}).get("birthYear")
            height = page_facts["height"]
        else:
            clubs = clubs_from_teams(wd_compact[qid]["rows"], wd_teams) if qid else []
            birth = (wf or {}).get("birthYear")
            height = None

        top_up(entry, extra_hints(clubs, birth, height, rec.get("first")))

        # Players the first (name-matching) pass under-filled: re-read the page
        # with the stricter parser and fall back to the dataset for the rest.
        if len(entry["hints"]) < TARGET:
            source = wf if wf else (page_facts if page_trusted else None)
            if source:
                top_up(entry, full_facts(source, clubs, rec))
            if len(entry["hints"]) < TARGET and page_facts and not page_trusted:
                top_up(entry, [("Nacionalidade", f"Tem nacionalidade {page_facts['adj']}.")
                               for _ in [0] if page_facts.get("adj")])
                top_up(entry, [("Nascimento", f"Nasceu em {page_facts['birthYear']}.")
                               for _ in [0] if page_facts.get("birthYear")])
            top_up(entry, dataset_hints(rec))

    B._save("hints_final.json", book)  # cache copy
    out_path = os.path.join(ROOT, "src/data/hints.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(book, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote", out_path)
    import collections
    dist = collections.Counter(len(v["hints"]) for v in book.values())
    print("players:", len(book))
    print("hint counts:", dict(sorted(dist.items())))
    print(f"position wording fixed: {fixed_positions}, singular counts fixed: {fixed_counts}")
    short = [(s, v["name"], len(v["hints"])) for s, v in book.items() if len(v["hints"]) < TARGET]
    print(f"still short ({len(short)}):", short)


if __name__ == "__main__":
    main()
