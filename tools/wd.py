#!/usr/bin/env python3
"""Resolve remaining players via Wikidata search (accent/nickname tolerant) + P18 images."""
import json, os, sys, time, urllib.parse
from photos import get, humanize, toks, norm, strip_tags

FOOT = ("futebolista","footballer","soccer player","jogador de futebol","futebol","soccer",
        "association football","goalkeeper","guarda-redes","defender","midfielder","forward")

def wd_search(name, lang="pt"):
    return get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
        "action":"wbsearchentities","search":name,"language":lang,"uselang":lang,
        "type":"item","limit":"7","format":"json"}), min_gap=1.2)

def pick(name, hits):
    tk = set(norm(name).split())
    scored = []
    for h in hits:
        lab = h.get("label","") or ""; desc = (h.get("description","") or "").lower()
        lt = set(norm(lab).split())
        if not tk <= lt:   # all query tokens must appear in the label
            continue
        bonus = 3 if lab.lower() == name.lower() else 1 if lt == tk else 0
        foot = 2 if any(f in desc for f in FOOT) else 0
        scored.append((foot + bonus, h["id"], lab, desc))
    scored.sort(key=lambda t: -t[0])
    return scored[0] if scored and scored[0][0] >= 2 else None

def wd_entities(qids):
    out = {}
    qids = list(qids)
    for i in range(0, len(qids), 40):
        d = get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action":"wbgetentities","ids":"|".join(qids[i:i+40]),"props":"claims|labels|descriptions",
            "languages":"pt|en","format":"json"}), min_gap=1.2)
        out.update(d.get("entities", {}))
    return out

def p18(ent):
    try:
        return ent["claims"]["P18"][0]["mainsnak"]["datavalue"]["value"]
    except Exception:
        return None

def run(limit):
    d = json.load(open("players_wiki.json")); res, src = d["res"], d["src"]
    cache = json.load(open("wd_cache.json")) if os.path.exists("wd_cache.json") else {}
    todo = [s for s, v in res.items() if v is None and s not in cache][:limit]
    print(f"  wd search {len(todo)} (remaining {sum(1 for s,v in res.items() if v is None and s not in cache)-len(todo)})", flush=True)
    newq = {}
    for slug in todo:
        name = " ".join(w.capitalize() for w in slug.split("-"))
        best = None
        for lang in ("pt", "en"):
            hits = wd_search(name, lang).get("search", [])
            best = pick(name, hits)
            if best: break
        if best:
            cache[slug] = {"qid": best[1], "label": best[2], "desc": best[3]}
            newq[best[1]] = slug
        else:
            cache[slug] = None
        # incremental save so a sandbox timeout never loses work
        json.dump(cache, open("wd_cache.json","w"), ensure_ascii=False)
    ents = wd_entities(newq.keys()) if newq else {}
    added = 0
    for qid, slug in newq.items():
        f = p18(ents.get(qid, {}))
        if f:
            res[slug] = {"lang":"wd","title":cache[slug]["label"],"file":f.replace(" ","_"),
                         "img":f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(f.replace(' ','_'))}?width=320",
                         "page":f"https://www.wikidata.org/wiki/{qid}"}
            src[slug] = "wikidata"; added += 1
    json.dump({"res":res,"src":src}, open("players_wiki.json","w"), ensure_ascii=False)
    print(f"  +{added} via wikidata; total {sum(1 for v in res.values() if v)}/{len(res)}", flush=True)

if __name__ == "__main__":
    run(int(sys.argv[1]))
