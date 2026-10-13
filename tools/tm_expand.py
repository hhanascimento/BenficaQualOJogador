"""Select and scrape more Benfica matches (per decade) from Transfermarkt.

Reuses `tm` for fetching/parsing and `build_dataset` for the record shape, and
writes the not-yet-localized records to /tmp/bf/new_matches.json. Resumable:
every page fetch goes through tm.get's on-disk cache.
"""
import json, os, sys, time
import tm, build_dataset as bd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = "/tmp/bf/season_scan.json"
# the single dataset the app ships (src/data/matches.json)
RAW = os.path.join(ROOT, "src/data/matches.json")
OUT = "/tmp/bf/new_matches.json"
PROGRESS = "/tmp/bf/expand_done.json"

TARGET = 100          # matches wanted per decade
FRIENDLY = "friendl"


def decade(y):
    return (y // 10) * 10


def candidates():
    """Every fixture with lineup data, excluding friendlies, from cached season pages."""
    scan = json.load(open(SCAN))
    out = []
    for sid in sorted(scan):
        if scan[sid]["lineups"] == 0:
            continue
        html = tm.get(tm.season_url(sid))
        for f in tm.parse_fixtures(html):
            if not f["formation"]:
                continue
            if FRIENDLY in (f["competition"] or "").lower():
                continue
            f["saison"] = sid          # build_one records it; we drop it after
            out.append(f)
    return out


def plan():
    raw = json.load(open(RAW))
    have = {m["id"] for m in raw}
    used = {}
    for m in raw:
        d = decade(int(m["date"][:4]))
        used[d] = used.get(d, 0) + 1
    byd = {}
    for f in candidates():
        if f["id"] in have:
            continue
        byd.setdefault(decade(int(f["date"][:4])), []).append(f)
    plan = {}
    for d, fx in sorted(byd.items()):
        want = max(0, TARGET - used.get(d, 0))
        fx.sort(key=lambda f: (f["date"], f["id"]))
        if want <= 0:
            pick = []
        elif want >= len(fx):
            pick = list(fx)
        else:
            pick = [fx[int(i * len(fx) / want)] for i in range(want)]
        # de-duplicate (the even spread can land on the same index twice)
        seen, uniq = set(), []
        for f in pick:
            if f["id"] not in seen:
                seen.add(f["id"]); uniq.append(f)
        plan[d] = {"have": used.get(d, 0), "available": len(fx), "want": want, "pick": uniq}
    return plan


def fetch(sel, budget):
    """Fetch the match pages of `sel` (skipping what is already done) and merge."""
    done = set(json.load(open(PROGRESS))) if os.path.exists(PROGRESS) else set()
    built = json.load(open(OUT)) if os.path.exists(OUT) else []
    known = {m["id"] for m in built}
    todo = [f for f in sel if f["id"] not in done and f["id"] not in known]
    t0 = time.time()
    fetched = 0
    for f in todo:
        if time.time() - t0 > budget:
            break
        m = bd.build_one(f)
        done.add(f["id"])
        fetched += 1
        if m:
            m.pop("season", None)
            built.append(m)
    json.dump(sorted(done), open(PROGRESS, "w"))
    built.sort(key=lambda m: (m["date"], m["id"]))
    json.dump(built, open(OUT, "w"), ensure_ascii=False, indent=1)
    return len(built), len(todo) - fetched


def scrape(budget):
    plan_ = plan()
    sel = [f for d in sorted(plan_) for f in plan_[d]["pick"]]
    total_built, left = fetch(sel, budget)
    print(f"scraped {total_built}/{len(sel)} selected  ({left} left this run)")
    for d in sorted(plan_):
        p = plan_[d]
        print(f"  {d}s: have {p['have']}  avail {p['available']}  want {p['want']}  picked {len(p['pick'])}")


def topup(budget):
    """Pick replacements for pages that produced no lineup, to reach TARGET."""
    raw = json.load(open(RAW))
    built = json.load(open(OUT)) if os.path.exists(OUT) else []
    done = set(json.load(open(PROGRESS))) if os.path.exists(PROGRESS) else set()
    taken = {m["id"] for m in raw} | {m["id"] for m in built} | done
    have = {}
    for m in raw + built:
        d = decade(int(m["date"][:4]))
        have[d] = have.get(d, 0) + 1
    cands = candidates()
    byd = {}
    for f in cands:
        if f["id"] in taken:
            continue
        byd.setdefault(decade(int(f["date"][:4])), []).append(f)
    sel = []
    for d, fx in sorted(byd.items()):
        need = max(0, TARGET - have.get(d, 0))
        if need == 0:
            continue
        want = min(len(fx), need + max(2, need // 4))     # margin for parse failures
        fx.sort(key=lambda f: (f["date"], f["id"]))
        pick = fx if want >= len(fx) else [fx[int(i * len(fx) / want)] for i in range(want)]
        seen, uniq = set(), []
        for f in pick:
            if f["id"] not in seen:
                seen.add(f["id"]); uniq.append(f)
        sel += uniq
        print(f"  {d}s: have {have.get(d, 0)}  need {need}  trying {len(uniq)}")
    print("total top-up candidates:", len(sel))
    if sel:
        total_built, left = fetch(sel, budget)
        print(f"after top-up: {total_built} new matches ({left} unfetched)")


def url_of(f):
    return f"https://www.transfermarkt.com/spielbericht/index/spielbericht/{f['id']}"


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if mode == "plan":
        plan_ = plan()
        for d in sorted(plan_):
            p = plan_[d]
            print(f"{d}s  have {p['have']:3}  available {p['available']:4}  want {p['want']:3}  picked {len(p['pick']):3}")
        print("total to add:", sum(len(p["pick"]) for p in plan_.values()))
    elif mode == "topup":
        topup(float(sys.argv[2]) if len(sys.argv) > 2 else 240)
    else:
        scrape(float(sys.argv[2]) if len(sys.argv) > 2 else 240)
