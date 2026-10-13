#!/usr/bin/env python3
import json, os, sys, time, urllib.request, urllib.error
UA = "BenficaXI-fan-game/1.0 (personal hobby project)"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/workspace/chats/6dbdcfe4fa6f3bde802a3e7b/public/assets/players"
os.makedirs(OUT, exist_ok=True)
d = json.load(open("players_wiki.json")); res = d["res"]
done, fail, skip = 0, 0, 0
for slug, rec in sorted(res.items()):
    if not rec or not rec.get("img"): skip += 1; continue
    path = os.path.join(OUT, slug + ".jpg")
    if os.path.exists(path) and os.path.getsize(path) > 1500: skip += 1; continue
    for a in range(3):
        try:
            req = urllib.request.Request(rec["img"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) < 1500: raise ValueError("tiny")
            open(path, "wb").write(data); done += 1; time.sleep(0.12); break
        except Exception as e:
            if a == 2: fail += 1; print("  FAIL", slug, type(e).__name__, getattr(e,'code',''), flush=True)
            else: time.sleep(2*(a+1))
print(f"downloaded {done}, skipped {skip}, failed {fail}")
