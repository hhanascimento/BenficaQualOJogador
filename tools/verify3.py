#!/usr/bin/env python3
"""Final accuracy gate on raw wikitext (returns every page in one request).
KEEP only if the article text mentions Benfica AND a football term,
and is not a disambiguation/name page. Wrong entities (butterfly 'Alcides',
'Lima' the city, 'Diamantino' the town, 'Eliseu' the prophet) fail this."""
import json, sys
from photos import wapi

FOOT = ("futebol", "football", "jogador", "player", "soccer")
BADPAGE = ("{{disambiguation", "may refer to", "{{given name", "{{surname", "{{hndis",
           "{{desambiguação", "{{nome", "{{antroponímia")

def fetch(lang, titles):
    out = {}
    titles = [t for t in dict.fromkeys(titles) if t]
    for i in range(0, len(titles), 20):
        d = wapi(lang, {"action":"query","titles":"|".join(titles[i:i+20]),"prop":"revisions",
                        "rvprop":"content","rvslots":"main","redirects":"1","format":"json",
                        "formatversion":"2"})
        q = d.get("query", {})
        pages = q.get("pages", [])
        if isinstance(pages, dict): pages = list(pages.values())
        for pg in pages:
            t = pg.get("title")
            if not t: continue
            try: txt = pg["revisions"][0]["slots"]["main"]["content"]
            except Exception: txt = ""
            out[t] = {"exists": not pg.get("missing"), "text": txt}
        for r in q.get("redirects", []):
            if r["to"] in out: out.setdefault(r["from"], out[r["to"]])
        for n in q.get("normalized", []):
            if n["to"] in out: out.setdefault(n["from"], out[n["to"]])
    return out

def good(rec):
    if not rec or not rec["exists"]: return False
    t = rec["text"].lower()
    if any(b in t for b in BADPAGE): return False
    return "benfica" in t and any(f in t for f in FOOT)

def main():
    d = json.load(open("players_wiki.json")); res, src = d["res"], d["src"]
    bylang = {}
    for slug, r in res.items():
        if r and r.get("title"): bylang.setdefault(r["lang"], []).append(r["title"])
        if r and r.get("lang") == "wd" and r.get("title"):
            bylang.setdefault("pt", []).append(r["title"]); bylang.setdefault("en", []).append(r["title"])
    cache = {}
    for lang, titles in bylang.items():
        if lang == "wd": continue
        cache[lang] = fetch(lang, titles)
        print(f"  {lang}: {len(cache[lang])} pages fetched", flush=True)
    keep, drop, unsure = [], [], []
    for slug, r in res.items():
        if not r: continue
        rec = cache.get(r["lang"], {}).get(r["title"])
        if rec is None and r.get("lang") == "wd":
            for L in ("pt", "en"):
                rec = cache.get(L, {}).get(r["title"])
                if rec: break
        if rec is None: unsure.append(slug); continue
        (keep if good(rec) else drop).append(slug)
    print(f"KEEP {len(keep)}  DROP {len(drop)}  UNSURE {len(unsure)}")
    print("dropped:", ", ".join(sorted(drop)))
    if unsure: print("UNSURE:", ", ".join(sorted(unsure)))
    print("\nspot-check:")
    for s in ("eusebio","mario-coluna","alejandro-grimaldo","angel-di-maria","darwin-nunez",
              "ramires","alcides","diamantino","edgar","lima","eliseu","nelson-oliveira",
              "leandro-barreiro","raul-machado","luis-filipe","jonas","isaías","isaias"):
        if s in res and res[s]: print(f"   {s:18s} {'KEEP' if s in keep else 'DROP'}")
    json.dump(cache, open("verify_wikitext.json","w"), ensure_ascii=False)
    if "--apply" in sys.argv:
        for s in drop: res[s] = None; src[s] = "rejected"
        json.dump({"res":res,"src":src}, open("players_wiki.json","w"), ensure_ascii=False)
        print("applied")

main()
