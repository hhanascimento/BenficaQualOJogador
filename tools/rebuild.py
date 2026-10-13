#!/usr/bin/env python3
"""Rebuild players_wiki.json from local caches (no search requests)."""
import json
import photos, wd

d = json.load(open("matches.json"))
players, seen = [], set()
for m in d:
    for p in m.get("lineup", []):
        if p["slug"] not in seen:
            seen.add(p["slug"]); players.append((p["slug"], p.get("name")))

photos.stage_exact(players)                      # replay exact lookups (cached urls)
data = json.load(open("players_wiki.json")); res, src = data["res"], data["src"]
cache = json.load(open("wd_cache.json")) if __import__("os").path.exists("wd_cache.json") else {}
q2s = {}
for slug, hit in cache.items():
    if hit and res.get(slug) is None: q2s[hit["qid"]] = slug
ents = wd.wd_entities(list(q2s)) if q2s else {}
added = 0
for qid, slug in q2s.items():
    f = wd.p18(ents.get(qid, {}))
    if f:
        res[slug] = {"lang":"wd","title":cache[slug]["label"],"file":f.replace(" ","_"),
                     "img":f"https://commons.wikimedia.org/wiki/Special:FilePath/{f.replace(' ','_')}?width=320",
                     "page":f"https://www.wikidata.org/wiki/{qid}"}
        src[slug] = "wikidata"; added += 1
json.dump({"res":res,"src":src}, open("players_wiki.json","w"), ensure_ascii=False)
print(f"rebuilt: {sum(1 for v in res.values() if v)}/{len(res)} resolved (+{added} from wikidata cache)")
