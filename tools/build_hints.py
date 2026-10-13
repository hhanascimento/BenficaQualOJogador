#!/usr/bin/env python3
"""Build src/data/hints.json for "Benfica - Qual o Jogador".

For every player in src/data/matches.json the script fetches the career facts
from Wikipedia (pt, with an en fallback) plus Wikidata and renders up to 11
ordered hints per player.

    python3 tools/build_hints.py             # all players
    python3 tools/build_hints.py --limit 25  # only the first 25 (smoke test)
    python3 tools/build_hints.py --slugs eusebio,rui-costa

Everything is cached under /tmp/qj so the run is resumable.

Sources: pt/en.wikipedia.org infoboxes ({{Info/Futebolista}} /
{{Infobox football biography}}) and www.wikidata.org (P17 country of each club
for the "different leagues" count).
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = "/tmp/qj"
os.makedirs(CACHE, exist_ok=True)
UA = "BenficaQualJogador-fan-game/1.0 (personal hobby project; contact: local)"

_last = [0.0]


def _load(path, default=None):
    fp = os.path.join(CACHE, path)
    if os.path.exists(fp):
        return json.load(open(fp, encoding="utf-8"))
    return default


def _save(path, value):
    json.dump(value, open(os.path.join(CACHE, path), "w", encoding="utf-8"), ensure_ascii=False)


def _get(url, tries=5, gap=0.3):
    for attempt in range(tries):
        wait = gap - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.load(r)
            _last[0] = time.time()
            return data
        except urllib.error.HTTPError as e:
            time.sleep(int(e.headers.get("Retry-After") or 0) or 5 * (attempt + 1))
        except Exception:
            time.sleep(3 * (attempt + 1))
    return {}


def wiki_api(lang, params):
    p = dict(params)
    p["format"] = "json"
    p["formatversion"] = "2"
    return _get(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(p))


def wd_api(params):
    p = dict(params)
    p["format"] = "json"
    return _get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(p))


# ------------------------------------------------------------------ text utils

ACCENTS = str.maketrans(
    "áàãâäéèêëíìîïóòõôöúùûüçñÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇÑ",
    "aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN")


def norm(s):
    s = (s or "").translate(ACCENTS).lower()
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()


def tokens(s):
    return [t for t in norm(s).split() if t]


def strip_markup(s):
    s = re.sub(r"<ref[^>]*/>", "", s or "", flags=re.I)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.I | re.S)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    return s


def clean_value(v):
    v = strip_markup(v or "")
    v = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", v)
    v = re.sub(r"\[\[([^\]]+)\]\]", r"\1", v)
    v = re.sub(r"\{\{[^{}]*\|([^}|]+)\}\}", r"\1", v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v = re.sub(r"<[^>]+>", " ", v)
    v = re.sub(r"''+", "", v)
    return re.sub(r"\s+", " ", v).strip(" ,;")


# ------------------------------------------------------------ infobox parsing

def find_template(txt, names):
    low = txt.lower()
    for name in names:
        i = low.find("{{" + name.lower())
        if i == -1:
            continue
        depth, j = 0, i
        while j < len(txt):
            if txt.startswith("{{", j):
                depth += 1
                j += 2
                continue
            if txt.startswith("}}", j):
                depth -= 1
                j += 2
                if depth == 0:
                    return txt[i:j]
                continue
            j += 1
        return txt[i:]
    return None


def parse_fields(tpl):
    body = tpl[2:-2]
    fields = {}
    for part in re.split(r"\n\s*\|", body):
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip().lower()
        if k and k not in fields:
            fields[k] = v.strip()
    return fields


def split_list(value):
    return [p.strip() for p in re.split(r"<br\s*/?>", value or "") if p.strip()]


def club_of(seg):
    seg = strip_markup(seg)
    seg = re.sub(r"\{\{\s*0\|[^}]*\}\}", "", seg)
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", seg)
    if m:
        return (m.group(2) or m.group(1)).strip(), m.group(1).strip()
    m = re.search(r"\{\{\s*[Ff]utebol\s*\|?\s*([^}|]+)\}\}", seg)
    if m:
        return m.group(1).strip(), ""
    m = re.findall(r"\{\{[^{}]*\|([^}|]+)\}\}", seg)
    if m:
        return m[-1].strip(), ""
    return re.sub(r"[\[\]{}]", "", seg).strip(), ""


def years_of(seg):
    ys = re.findall(r"(1[89]\d\d|20\d\d)", seg or "")
    return (int(ys[0]), int(ys[-1])) if ys else (None, None)


def stats_of(seg):
    seg = strip_markup(seg)
    seg = re.sub(r"\{\{\s*0\|[^}]*\}\}", "", seg)
    apps = re.search(r"(\d[\d\s]*)", seg)
    goals = re.search(r"\((\d[\d\s]*)\)", seg)
    a = int(re.sub(r"\D", "", apps.group(1))) if apps else None
    g = int(re.sub(r"\D", "", goals.group(1))) if goals else None
    return a, g


EN_POS = {
    "goalkeeper": "guarda-redes", "defender": "defesa", "centre back": "defesa central",
    "centre-back": "defesa central", "midfielder": "médio", "winger": "extremo",
    "forward": "avançado", "striker": "avançado", "attacker": "avançado",
    "left back": "lateral-esquerdo", "right back": "lateral-direito",
    "full back": "lateral", "full-back": "lateral", "defensive midfielder": "médio defensivo",
    "attacking midfielder": "médio ofensivo", "centre forward": "avançado",
}


def first_position(v):
    v = clean_value(v).lower()
    for sep in ("/", ","):
        v = v.split(sep)[0]
    v = v.strip()
    for en, pt in EN_POS.items():
        if en in v:
            return pt
    return v


# ------------------------------------------------------------ club -> country

COUNTRY_TITLE = {}


def resolve_club_countries(titles):
    """Map pt.wikipedia club titles -> country name, through Wikidata P17."""
    titles = sorted({t for t in titles if t})
    key = "cc_" + hashlib.sha1("\n".join(titles).encode()).hexdigest()[:14]
    cached = _load(key)
    if cached is not None:
        return cached

    canon = {}
    for i in range(0, len(titles), 45):
        d = wiki_api("pt", {"action": "query", "titles": "|".join(titles[i:i + 45]),
                            "redirects": 1, "prop": "info"})
        q = d.get("query") or {}
        for n in q.get("normalized", []):
            canon[n["from"]] = n["to"]
        for r in q.get("redirects", []):
            canon[r["from"]] = r["to"]
    resolved = sorted({canon.get(t, t) for t in titles})

    title_qid, qid_country = {}, {}
    for i in range(0, len(resolved), 45):
        d = wd_api({"action": "wbgetentities", "sites": "ptwiki",
                    "titles": "|".join(resolved[i:i + 45]), "props": "claims"})
        for qid, e in (d.get("entities") or {}).items():
            if qid.startswith("-"):
                continue
            t = ((e.get("sitelinks") or {}).get("ptwiki") or {}).get("title")
            if t:
                title_qid[t] = qid
            for st in (e.get("claims", {}).get("P17") or [])[:1]:
                qid_country[qid] = st.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")

    countries = {}
    cqids = sorted({q for q in qid_country.values() if q})
    for i in range(0, len(cqids), 45):
        d = wd_api({"action": "wbgetentities", "ids": "|".join(cqids[i:i + 45]),
                    "props": "labels", "languages": "pt|en"})
        for qid, e in (d.get("entities") or {}).items():
            labels = e.get("labels") or {}
            lbl = labels.get("pt") or labels.get("en") or {}
            if lbl.get("value"):
                countries[qid] = lbl["value"]

    out = {}
    for t in titles:
        r = canon.get(t, t)
        qid = title_qid.get(r)
        out[t] = countries.get(qid_country.get(qid, ""), "") if qid else ""
    _save(key, out)
    return out


# ------------------------------------------------------------ page resolution

FOOT_WORDS = ("futebol", "football", "soccer", "jogador", "futebolista",
              "guarda-redes", "defesa", "medio", "médio", "avancado", "avançado")


def search_titles(lang, query, extra=""):
    """Ranked candidate page titles for a search query (best first)."""
    ck = "s_" + hashlib.sha1(f"{lang}|{query}|{extra}".encode()).hexdigest()[:16]
    cached = _load(ck)
    if cached is not None:
        return cached
    q = (query + " " + extra).strip()
    d = wiki_api(lang, {"action": "query", "list": "search", "srsearch": q,
                        "srlimit": 8, "srnamespace": 0})
    hits = (d.get("query") or {}).get("search") or []
    qn = set(tokens(query))
    if not qn:
        return []
    scored = []
    for h in hits:
        title = h.get("title", "")
        snip = norm(h.get("snippet", ""))
        tt = set(tokens(title))
        if not qn <= tt:
            continue
        score = 4 if norm(title) == norm(query) else 2 if qn <= tt else 1
        if any(w in snip for w in ("futebol", "football", "soccer", "jogador", "footballer")):
            score += 2
        if "list" in title.lower() or "selecao" in title.lower() or "lista" in title.lower():
            score -= 3
        scored.append((score, title))
    scored.sort(key=lambda t: -t[0])
    out = [t for _, t in scored]
    _save(ck, out)
    return out


def name_from_slug(slug):
    return " ".join(w.capitalize() for w in slug.split("-") if w)


PREFETCH = {}


def _batch_contents(lang, titles):
    """Fetch many pages' wikitext in batches of 45. Returns {requested: (final, text)}."""
    out = {}
    titles = sorted({t for t in titles if t})
    for i in range(0, len(titles), 45):
        chunk = titles[i:i + 45]
        ck = "ch_" + hashlib.sha1((lang + "|" + "|".join(chunk)).encode()).hexdigest()[:16]
        cached = _load(ck)
        if cached is None:
            d = wiki_api(lang, {"action": "query", "prop": "revisions", "rvprop": "content",
                                "rvslots": "main", "titles": "|".join(chunk), "redirects": 1})
            q = d.get("query") or {}
            norm_map = {n["from"]: n["to"] for n in q.get("normalized", [])}
            redir = {r["from"]: r["to"] for r in q.get("redirects", [])}
            by_title = {}
            for pg in q.get("pages", []):
                if pg.get("missing"):
                    continue
                txt = (pg.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("content", "")
                by_title[pg["title"]] = txt
            cached = {}
            for t in chunk:
                nt = norm_map.get(t, t)
                ft = redir.get(nt, nt)
                cached[t] = [ft, by_title.get(ft)]
            _save(ck, cached)
        out.update({t: tuple(v) for t, v in cached.items()})
    return out


def variants_for(slug, name, fullname, known):
    out = []
    if slug in known and known[slug] and known[slug].get("title"):
        out.append((known[slug].get("lang", "pt"), known[slug]["title"]))
    bases = []
    for b in (name_from_slug(slug), name, fullname):
        if b and b not in bases:
            bases.append(b)
    for base in bases:
        out += [("pt", base), ("pt", base + " (futebolista)"),
                ("en", base), ("en", base + " (footballer)")]
    seen, uniq = set(), []
    for lang, t in out:
        if (lang, t) not in seen:
            seen.add((lang, t))
            uniq.append((lang, t))
    return uniq


def prefetch_all(players, known):
    pt, en = [], []
    for slug, rec in players.items():
        for lang, t in variants_for(slug, rec["name"], None, known):
            (pt if lang == "pt" else en).append(t)
    print(f"prefetching {len(set(pt))} pt + {len(set(en))} en candidate titles…", flush=True)
    for lang, titles in (("pt", pt), ("en", en)):
        PREFETCH.update({(lang, t): v for t, v in _batch_contents(lang, titles).items()})


def _fetch_text(lang, title):
    if (lang, title) in PREFETCH:
        ft, txt = PREFETCH[(lang, title)]
        return ft, txt
    d = wiki_api(lang, {"action": "query", "prop": "revisions", "rvprop": "content",
                        "rvslots": "main", "titles": title, "redirects": 1})
    pages = (d.get("query") or {}).get("pages") or []
    if not pages or pages[0].get("missing"):
        return None, None
    txt = (pages[0].get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("content", "")
    return pages[0].get("title", title), txt


def _plausible(text):
    head = text[:6000].lower()
    if any(k in head for k in ("{{desambiguação", "{{disambiguation", "{{desambig",
                               "may refer to", "pode referir-se a")):
        return False
    return any(w in head for w in FOOT_WORDS) or "infobox football" in head


def _benfica_overlap(text, years):
    """How many of the dataset's Benfica years fall inside the page's Benfica spell(s)."""
    facts = extract(text)
    ranges = [(c["start"], c["end"]) for c in facts.get("clubs", [])
              if "benfica" in norm(c["name"]) and c["start"]]
    if not ranges:
        return -1
    hit = 0
    for y in years:
        if any((a - 4) <= y <= (b + 4 if b else a + 4) for a, b in ranges):
            hit += 1
    return hit


def _consider(lang, title, years, state):
    ft, txt = _fetch_text(lang, title)
    if not txt or not _plausible(txt) or "benfica" not in txt.lower():
        return None
    ov = _benfica_overlap(txt, years)
    cand = {"lang": lang, "title": ft, "text": txt}
    if ov > 0:
        return cand
    if state["fallback"] is None or ov > state["fallback"][0]:
        state["fallback"] = (ov, cand)
    return None


def resolve_page(slug, name, fullname, known, years):
    key = "pg_" + slug
    cached = _load(key)
    if cached is not None:
        return cached
    state = {"fallback": None}
    for lang, t in variants_for(slug, name, fullname, known):
        hit = _consider(lang, t, years, state)
        if hit:
            _save(key, hit)
            return hit
    for lang, extra in (("pt", "futebolista"), ("en", "footballer")):
        for q in (name_from_slug(slug), name):
            if not q:
                continue
            for title in search_titles(lang, q, extra)[:3]:
                hit = _consider(lang, title, years, state)
                if hit:
                    _save(key, hit)
                    return hit
    result = state["fallback"][1] if state["fallback"] else {"lang": None, "title": None, "text": None}
    _save(key, result)
    return result


# ------------------------------------------------------------ nationality

COUNTRY = {
    "POR": ("Portugal", "portuguesa"), "PRT": ("Portugal", "portuguesa"),
    "BRA": ("Brasil", "brasileira"), "BRZ": ("Brasil", "brasileira"),
    "ARG": ("Argentina", "argentina"), "ESP": ("Espanha", "espanhola"),
    "FRA": ("França", "francesa"), "ENG": ("Inglaterra", "inglesa"),
    "ITA": ("Itália", "italiana"), "HOL": ("Países Baixos", "neerlandesa"),
    "NED": ("Países Baixos", "neerlandesa"), "ALE": ("Alemanha", "alemã"),
    "GER": ("Alemanha", "alemã"), "URU": ("Uruguai", "uruguaia"),
    "SRB": ("Sérvia", "sérvia"), "CRO": ("Croácia", "croata"),
    "MEX": ("México", "mexicana"), "COL": ("Colômbia", "colombiana"),
    "CHI": ("Chile", "chilena"), "CHL": ("Chile", "chilena"),
    "PAR": ("Paraguai", "paraguaia"), "PER": ("Peru", "peruana"),
    "MOZ": ("Moçambique", "moçambicana"), "MOC": ("Moçambique", "moçambicana"),
    "ANG": ("Angola", "angolana"), "GNB": ("Guiné-Bissau", "guineense"),
    "GBS": ("Guiné-Bissau", "guineense"), "CPV": ("Cabo Verde", "cabo-verdiana"),
    "STP": ("São Tomé e Príncipe", "santomense"), "NGA": ("Nigéria", "nigeriana"),
    "GHA": ("Gana", "ganesa"), "SEN": ("Senegal", "senegalesa"),
    "CMR": ("Camarões", "camaronesa"), "MAR": ("Marrocos", "marroquina"),
    "ALG": ("Argélia", "argelina"), "TUN": ("Tunísia", "tunisina"),
    "SUE": ("Suécia", "sueca"), "SWE": ("Suécia", "sueca"),
    "DIN": ("Dinamarca", "dinamarquesa"), "DEN": ("Dinamarca", "dinamarquesa"),
    "NOR": ("Noruega", "norueguesa"), "POL": ("Polónia", "polaca"),
    "ROM": ("Roménia", "romena"), "ROU": ("Roménia", "romena"),
    "RUS": ("Rússia", "russa"), "UKR": ("Ucrânia", "ucraniana"),
    "EUA": ("Estados Unidos", "norte-americana"), "USA": ("Estados Unidos", "norte-americana"),
    "JAP": ("Japão", "japonesa"), "JPN": ("Japão", "japonesa"),
    "COR": ("Coreia do Sul", "sul-coreana"), "KOR": ("Coreia do Sul", "sul-coreana"),
    "CHN": ("China", "chinesa"), "VEN": ("Venezuela", "venezuelana"),
    "BOL": ("Bolívia", "boliviana"), "EQU": ("Equador", "equatoriana"),
    "CRC": ("Costa Rica", "costa-riquenha"), "GRE": ("Grécia", "grega"),
    "TUR": ("Turquia", "turca"), "BEL": ("Bélgica", "belga"),
    "AUT": ("Áustria", "austríaca"), "SUI": ("Suíça", "suíça"),
    "SCO": ("Escócia", "escocesa"), "WAL": ("País de Gales", "galesa"),
    "IRL": ("Irlanda", "irlandesa"), "CAN": ("Canadá", "canadiana"),
    "AUS": ("Austrália", "australiana"), "ISR": ("Israel", "israelita"),
    "GUI": ("Guiné", "guineense"), "CIV": ("Costa do Marfim", "marfinense"),
    "MLI": ("Mali", "maliana"), "TOG": ("Togo", "togolesa"),
    "GAB": ("Gabão", "gabonesa"), "CGO": ("Congo", "congolesa"),
    "EGI": ("Egito", "egípcia"), "EGY": ("Egito", "egípcia"),
}


def nationality_of(f):
    v = f.get("nacionalidade") or f.get("nationality") or ""
    for m in re.finditer(r"\{\{\s*([A-Za-z]{2,3})", v):
        code = m.group(1).upper()
        if code in COUNTRY:
            return COUNTRY[code]
    txt = clean_value(v).lower()
    if txt and len(txt) > 2 and txt not in ("o", "a", "os", "as", "de"):
        return (None, txt)
    c = clean_value(f.get("paisnatal") or f.get("country") or f.get("birth_country") or "")
    return (c or None, None)


# ------------------------------------------------------------ fact extraction

def extract(text):
    """Return the raw career facts from a player wikitext."""
    facts = {}
    tpl = find_template(text, ["Info/Futebolista", "Infobox football biography",
                               "Infobox footballer", "Info/futebolista"])
    if not tpl:
        return facts
    f = parse_fields(tpl)

    positions = first_position(f.get("posição") or f.get("posicao") or f.get("position"))
    if positions in ("", "futebolista"):
        positions = ""
    facts["position"] = positions

    country, adjective = nationality_of(f)
    facts["nationality"] = adjective or country
    facts["nationalityCountry"] = country

    for field in ("datadenascimento", "nascimento_data", "birth_date", "datanascimento"):
        if f.get(field):
            ys = years_of(f[field])
            if ys[0]:
                facts["birthYear"] = ys[0]
            break

    # senior clubs: pt uses ano/clubes/jogos(golos); en uses yearsN/clubsN/capsN/goalsN
    clubs = []  # (start, end, club, link, apps, goals)
    if "clubes" in f:
        years = split_list(f.get("ano") or f.get("anos") or f.get("anoclubes") or "")
        names = split_list(f.get("clubes"))
        stats = split_list(f.get("jogos(golos)") or f.get("jogos") or "")
        for idx, seg in enumerate(names):
            name_c, link = club_of(seg)
            if not name_c:
                continue
            y = years[idx] if idx < len(years) else ""
            start, end = years_of(y)
            a, g = stats_of(stats[idx]) if idx < len(stats) else (None, None)
            clubs.append({"start": start, "end": end, "name": name_c, "link": link,
                          "apps": a, "goals": g})
    else:
        for i in range(1, 26):
            if f.get(f"clubs{i}"):
                name_c, link = club_of(f[f"clubs{i}"])
                start, end = years_of(f.get(f"years{i}") or f.get(f"years{i}") or "")
                stat_caps = re.search(r"\d+", strip_markup(f.get(f"caps{i}") or ""))
                stat_goals = re.search(r"\d+", strip_markup(f.get(f"goals{i}") or ""))
                clubs.append({"start": start, "end": end, "name": name_c, "link": link,
                              "apps": int(stat_caps.group()) if stat_caps else None,
                              "goals": int(stat_goals.group()) if stat_goals else None})

    facts["clubs"] = clubs

    # national team caps
    caps = None
    for field in ("partidasselecao", "nationalcaps1", "nationalcaps", "caps"):
        if f.get(field):
            a, _ = stats_of(f[field])
            if a is not None:
                caps = a
                break
    if caps is None:
        for i in range(1, 8):
            if f.get(f"nationalcaps{i}"):
                m = re.search(r"\d+", strip_markup(f[f"nationalcaps{i}"]))
                if m:
                    caps = int(m.group())
                    break
    facts["intlCaps"] = caps

    if facts.get("nationality"):
        facts["nationality"] = facts["nationality"]
    return facts


# ------------------------------------------------------------ hint rendering

def decade_label(start):
    return str(start) if start >= 2000 else str(start % 100).zfill(2)


def decades_of(first, last):
    ds = []
    for y in range(first, last + 1):
        d = y // 10 * 10
        if d < 1960:
            d = 1960
        if d > 2020:
            d = 2020
        if d not in ds:
            ds.append(d)
    return ds


def join_pt(items):
    items = [str(x) for x in items]
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " e " + items[-1]


def build_hints(facts, dataset_years):
    clubs = [c for c in facts.get("clubs", []) if c["name"]]
    benfica = [c for c in clubs if "benfica" in norm(c["name"])]
    all_years = [s for c in clubs for s in (c["start"], c["end"]) if s]
    start_year = min(all_years) if all_years else min(dataset_years) if dataset_years else None
    bf_first = min((c["start"] for c in benfica if c["start"]), default=None)
    bf_last = max((c["end"] for c in benfica if c["end"]), default=None)
    if not bf_first and dataset_years:
        bf_first, bf_last = min(dataset_years), max(dataset_years)

    bf_apps = sum(c["apps"] for c in benfica if c["apps"]) or None
    bf_goals = sum(c["goals"] for c in benfica if c["goals"]) or None
    bf_seasons = sum(max(1, (c["end"] - c["start"])) if c["start"] and c["end"] else 1
                     for c in benfica) or None

    distinct = {}
    for c in clubs:
        distinct.setdefault(norm(c["name"]), c)
    clubs_count = len(distinct)
    country_of = resolve_club_countries([c["link"] or c["name"] for c in clubs])
    leagues = set()
    for c in clubs:
        label = country_of.get(c["link"] or c["name"], "")
        leagues.add(label if label else norm(c["name"]))
    leagues_count = len(leagues) if leagues else None

    hints = []
    if facts.get("nationality"):
        if facts.get("nationalityCountry"):
            hints.append(("Nacionalidade", f"Tem nacionalidade {facts['nationality']}."))
        else:
            hints.append(("Nacionalidade", f"A nacionalidade é {facts['nationality']}."))
    if facts.get("position"):
        hints.append(("Posição", f"Jogava na posição de {facts['position']}."))
    if bf_first:
        ds = decades_of(bf_first, bf_last or bf_first)
        hints.append(("Época", f"No Benfica, jogou nos anos {join_pt([decade_label(d) for d in ds])}."))
    if start_year:
        hints.append(("Estreia", f"Começou a carreira profissional em {start_year}."))
    if clubs_count:
        hints.append(("Clubes", f"Passou por {clubs_count} clubes ao longo da carreira."))
    if leagues_count and leagues_count > 1:
        hints.append(("Ligas", f"Representou clubes de {leagues_count} ligas diferentes."))
    if bf_seasons:
        hints.append(("Temporadas", f"Fez {bf_seasons} temporadas no Benfica."))
    if bf_apps:
        hints.append(("Jogos", f"Disputou {bf_apps} jogos pelo Benfica."))
    if bf_goals:
        hints.append(("Golos", f"Marcou {bf_goals} golos pelo Benfica."))
    if facts.get("intlCaps"):
        hints.append(("Internacionalizações", f"Somou {facts['intlCaps']} internacionalizações."))
    if facts.get("birthYear"):
        hints.append(("Nascimento", f"Nasceu em {facts['birthYear']}."))

    meta = {
        "first": bf_first, "last": bf_last or bf_first,
        "benficaSeasons": bf_seasons, "benficaApps": bf_apps, "benficaGoals": bf_goals,
    }
    return hints, meta


# ------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--slugs", default="")
    args = ap.parse_args()

    matches = json.load(open(os.path.join(ROOT, "src/data/matches.json"), encoding="utf-8"))
    players = {}
    for m in matches:
        y = int(m["date"][:4])
        for p in m["lineup"]:
            rec = players.setdefault(p["slug"], {"name": p["name"], "photo": p.get("photo"),
                                                 "years": set()})
            rec["years"].add(y)

    known = {}
    pw_path = os.path.join(ROOT, "tools/players_wiki.json")
    pw = json.load(open(pw_path, encoding="utf-8")) if os.path.exists(pw_path) else None
    if pw:
        for slug, v in (pw.get("res") or {}).items():
            if v:
                known[slug] = {"lang": v.get("lang", "pt"), "title": v.get("title")}

    slugs = list(players)
    if args.slugs:
        want = {s.strip() for s in args.slugs.split(",")}
        slugs = [s for s in slugs if s in want]
    if args.limit:
        slugs = slugs[:args.limit]

    prefetch_all({sl: players[sl] for sl in slugs}, known)

    out = _load("hints_out.json", {}) or {}
    ok = 0
    for i, slug in enumerate(slugs):
        rec = players[slug]
        page = resolve_page(slug, rec["name"], None, known, rec["years"])
        facts = extract(page["text"]) if page.get("text") else {}
        hints, meta = build_hints(facts, rec["years"])
        entry = {
            "name": rec["name"],
            "photo": rec["photo"],
            "position": facts.get("position", ""),
            "nationality": facts.get("nationality", ""),
            "first": meta["first"], "last": meta["last"],
            "benficaSeasons": meta["benficaSeasons"],
            "benficaApps": meta["benficaApps"], "benficaGoals": meta["benficaGoals"],
            "wiki": (f"{page['lang']}:{page['title']}" if page.get("title") else None),
            "hints": [{"label": l, "text": t} for l, t in hints],
        }
        out[slug] = entry
        if hints:
            ok += 1
        if (i + 1) % 20 == 0 or args.slugs or args.limit:
            print(f"  {i+1}/{len(slugs)} {slug}: {len(hints)} hints "
                  f"[{entry['first']}-{entry['last']}] {entry['wiki']}", flush=True)
    _save("hints_out.json", out)
    print(f"\ndone: {ok}/{len(slugs)} players with hints; {len(out)} cached")
    print(json.dumps(out.get(slugs[0], {}), ensure_ascii=False, indent=1)[:1400])


if __name__ == "__main__":
    main()
