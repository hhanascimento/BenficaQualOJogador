"""Resolve photos for players that have none yet (exact -> search -> wikidata)."""
import json, os, sys
import photos, wd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src/data/matches.json")
PHOTOS = os.path.join(ROOT, "public/assets/players")


def missing():
    data = json.load(open(SRC, encoding="utf-8"))
    seen, out = set(), []
    for m in data:
        for p in m["lineup"]:
            if p["slug"] in seen or p.get("photo"):
                continue
            if os.path.exists(os.path.join(PHOTOS, p["slug"] + ".jpg")):
                continue
            seen.add(p["slug"])
            out.append((p["slug"], p.get("name")))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    players = missing()
    print(f"{len(players)} players without a photo")
    if cmd == "exact":
        photos.stage_exact(players)
    elif cmd == "search":
        photos.stage_search(int(sys.argv[2]) if len(sys.argv) > 2 else 60)
    elif cmd == "wd":
        wd.run(int(sys.argv[2]) if len(sys.argv) > 2 else 60)
    elif cmd == "status":
        d = json.load(open("players_wiki.json"))
        res = d["res"]
        print(f"resolved {sum(1 for v in res.values() if v)}/{len(res)}")
        for s, v in sorted(res.items()):
            print(f"  {s:28} {'OK ' + v['title'][:45] if v else '--'}")
