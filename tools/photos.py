#!/usr/bin/env python3
"""Resolve player photos via Wikipedia (pageimages) + Wikimedia Commons metadata.
Stages: exact (batched), search (throttled, resumable), meta, download (resumable)."""
import json, re, os, sys, time, html, hashlib, urllib.parse, urllib.request, urllib.error

UA = "BenficaXI-fan-game/1.0 (personal hobby project; contact: local)"
CACHE = "/tmp/bf/wcache"; os.makedirs(CACHE, exist_ok=True)
_last = [0.0]

def _fp(url): return os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest())

def get(url, min_gap=1.6, tries=6):
    fp = _fp(url)
    if os.path.exists(fp):
        return json.load(open(fp))
    for a in range(tries):
        gap = min_gap - (time.time() - _last[0])
        if gap > 0: time.sleep(gap)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.load(r)
            _last[0] = time.time()
            json.dump(data, open(fp, "w"))
            return data
        except urllib.error.HTTPError as e:
            wait = int(e.headers.get("Retry-After") or 0) or 10 * (a + 1)
            print(f"    HTTP {e.code}; backoff {wait}s", flush=True)
            time.sleep(wait)
        except Exception as e:
            print(f"    err {type(e).__name__}; backoff {5*(a+1)}s", flush=True)
            time.sleep(5 * (a + 1))
    return {}

def wapi(lang, params):
    return get(f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params))

def capi(params):
    return get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))

ACCENT = [("á","a"),("à","a"),("ã","a"),("â","a"),("ä","a"),("é","e"),("ê","e"),("è","e"),("í","i"),
          ("ó","o"),("ô","o"),("õ","o"),("ö","o"),("ú","u"),("ü","u"),("ç","c"),("ñ","n"),("'"," ")]
GENERIC = {"de","da","do","dos","das","e","footballer","futebolista","jogador","portuguese","player"}

def norm(s):
    s = s.lower()
    for a,b in ACCENT: s = s.replace(a,b)
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()

def toks(slug): return [t for t in norm(slug.replace("-", " ")).split() if t]
def humanize(slug): return " ".join(w.capitalize() for w in slug.split("-") if w)

def valid(title, tk):
    if not title or "disambiguation" in title.lower(): return False
    tt = set(norm(title).split())
    need = tk or [t for t in tk]
    return all(t in tt for t in need)

def batch_images(lang, titles):
    out = {}
    titles = [t for t in dict.fromkeys(titles) if t]
    for i in range(0, len(titles), 40):
        d = wapi(lang, {"action":"query","titles":"|".join(titles[i:i+40]),"prop":"pageimages",
                        "piprop":"thumbnail|pageimage","pithumbsize":"320","redirects":1,"format":"json"})
        q = d.get("query", {})
        for pg in q.get("pages", {}).values():
            if "thumbnail" not in pg or pg.get("missing"): continue
            rec = {"lang":lang, "title":pg["title"], "file":pg.get("pageimage"),
                   "img":pg["thumbnail"]["source"],
                   "page":f"https://{lang}.wikipedia.org/wiki/"+urllib.parse.quote(pg["title"].replace(" ","_"))}
            out[pg["title"]] = rec
        for r in q.get("redirects", []):
            if r["to"] in out: out[r["from"]] = out[r["to"]]
        for n in q.get("normalized", []):
            if n["to"] in out: out[n["from"]] = out[n["to"]]
    return out

def stage_exact(players):
    res = {s: None for s, _ in players}
    src = {s: None for s, _ in players}
    for lang in ("pt", "en"):
        cand = {}
        for slug, tmname in players:
            for name in (humanize(slug), tmname or ""):
                if name: cand.setdefault(name, []).append(slug)
        imgs = batch_images(lang, list(cand))
        for title, rec in imgs.items():
            for slug in cand.get(title, []):
                if res[slug] is None and valid(rec["title"], toks(slug)):
                    res[slug] = rec; src[slug] = f"{lang}-exact"
        print(f"  {lang}: {sum(1 for v in res.values() if v)}/{len(players)} resolved", flush=True)
    json.dump({"res":res,"src":src}, open("players_wiki.json","w"), ensure_ascii=False)

def stage_search(limit):
    d = json.load(open("players_wiki.json"))
    res, src = d["res"], d["src"]
    todo = [s for s, v in res.items() if v is None][:limit]
    print(f"  searching {len(todo)}", flush=True)
    for slug in todo:
        h = humanize(slug); tk = toks(slug)
        for lang in ("pt", "en"):
            for q in (f"{h} futebolista", f"{h} footballer", h):
                dd = wapi(lang, {"action":"query","generator":"search","gsrsearch":q,"gsrnamespace":"0",
                                 "gsrlimit":"5","prop":"pageimages","piprop":"thumbnail|pageimage",
                                 "pithumbsize":"320","format":"json"})
                pages = sorted(dd.get("query",{}).get("pages",{}).values(), key=lambda p: p.get("index",99))
                hit = None
                for pg in pages:
                    if "thumbnail" in pg and valid(pg.get("title",""), tk):
                        hit = {"lang":lang,"title":pg["title"],"file":pg.get("pageimage"),
                               "img":pg["thumbnail"]["source"],
                               "page":f"https://{lang}.wikipedia.org/wiki/"+urllib.parse.quote(pg["title"].replace(" ","_"))}
                        break
                if hit:
                    res[slug] = hit; src[slug] = f"{lang}-search"; break
            if res[slug]: break
    json.dump({"res":res,"src":src}, open("players_wiki.json","w"), ensure_ascii=False)
    print(f"  total resolved {sum(1 for v in res.values() if v)}/{len(res)}", flush=True)

def strip_tags(s): return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()

def stage_meta():
    d = json.load(open("players_wiki.json")); res = d["res"]
    files = sorted({v["file"] for v in res.values() if v and v.get("file")})
    meta = {}
    for i in range(0, len(files), 25):
        chunk = files[i:i+25]
        dd = capi({"action":"query","titles":"|".join("File:"+f for f in chunk),"prop":"imageinfo",
                   "iiprop":"extmetadata|url","format":"json"})
        for pg in dd.get("query",{}).get("pages",{}).values():
            t = pg.get("title","")
            name = t[5:] if t.startswith("File:") else t
            ii = (pg.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata", {})
            meta[name] = {"license": strip_tags(em.get("LicenseShortName",{}).get("value")),
                          "artist": strip_tags(em.get("Artist",{}).get("value"))[:120],
                          "page": ii.get("descriptionurl","")}
        print(f"  meta {min(i+25,len(files))}/{len(files)}", flush=True)
    json.dump(meta, open("file_meta.json","w"), ensure_ascii=False)

if __name__ == "__main__":
    d = json.load(open("matches.json"))
    players, seen = [], set()
    for m in d:
        for p in m.get("lineup", []):
            if p["slug"] not in seen:
                seen.add(p["slug"]); players.append((p["slug"], p.get("name")))
    cmd = sys.argv[1]
    if cmd == "exact": stage_exact(players)
    elif cmd == "search": stage_search(int(sys.argv[2]))
    elif cmd == "meta": stage_meta()
