import os, re, time, hashlib, urllib.request, http.cookiejar

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CACHE = "/tmp/bf/tmcache"
os.makedirs(CACHE, exist_ok=True)
_cj = http.cookiejar.CookieJar()
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cj))

def is_cached(url):
    key = hashlib.sha1(url.encode()).hexdigest()
    return os.path.exists(os.path.join(CACHE, key))

def get(url, delay=1.6):
    key = hashlib.sha1(url.encode()).hexdigest()
    fp = os.path.join(CACHE, key)
    if os.path.exists(fp):
        return open(fp, encoding="utf-8").read()
    last = None
    for k in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            })
            with _op.open(req, timeout=30) as r:
                data = r.read().decode("utf-8", "ignore")
            open(fp, "w", encoding="utf-8").write(data)
            time.sleep(delay)
            return data
        except Exception as e:
            last = e
            time.sleep(2 * (k + 1))
    raise last

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s).replace("&nbsp;", " ").replace("&#039;", "'").replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip()

def season_url(sid):
    return f"https://www.transfermarkt.com/sl-benfica/spielplan/verein/294/saison_id/{sid}/plus/1"

DOW = "Mon|Tue|Wed|Thu|Fri|Sat|Sun"
_TRO = re.compile(r'<tr\b', re.I)
_TRC = re.compile(r'</tr>', re.I)

def enclosing_row(html, pos):
    """Find the outer <tr>...</tr> that contains position `pos` (handles nested tables)."""
    starts = [m.start() for m in _TRO.finditer(html, 0, pos)]
    if not starts:
        return None
    for s in reversed(starts):
        depth = 0
        for m in re.finditer(r'<tr\b|</tr>', html[s:], re.I):
            if m.group(0).lower().startswith('</'):
                depth -= 1
                if depth == 0:
                    return html[s:s + m.end()]
            else:
                depth += 1
    return None

def parse_fixtures(html):
    headers = [(m.start(), clean(m.group(1))) for m in re.finditer(r'<h2[^>]*>(.*?)</h2>', html, re.S)]
    out = []
    for m in re.finditer(r'spielbericht/(\d+)', html):
        mid, pos = m.group(1), m.start()
        row = enclosing_row(html, pos)
        if not row:
            continue
        dt = re.search(rf'({DOW})\s+(\d{{2}})/(\d{{2}})/(\d{{4}})', row)
        if not dt:
            continue
        date = f"{dt.group(4)}-{dt.group(3)}-{dt.group(2)}"
        teams = [t.strip() for t in re.findall(
            r'<a[^>]*href="[^"]*/startseite/verein/\d+[^"]*"[^>]*>([^<]+)</a>', row) if t.strip()]
        seen = []
        for t in teams:
            if t not in seen:
                seen.append(t)
        if len(seen) < 2:
            continue
        # round is the first cell
        rnd = None
        cm = re.findall(r'<td\b[^>]*>(.*?)</td>', row, re.S)
        if cm:
            rnd = clean(cm[0])
            if re.fullmatch(r'\d{1,3}', rnd):
                rnd = f"Matchday {rnd}"
        sm = re.search(r'class="[^"]*ergebnis[^"]*"[^>]*>(.*?)</a>', row, re.S)
        if sm:
            score = clean(sm.group(1))
        else:
            sm2 = re.search(r'(\d+:\d+)', row)
            score = sm2.group(1) if sm2 else None
        fh = re.search(r'\b(\d(?:-\d){1,4})\b', row)
        comp = None
        for hp, ct in headers:
            if hp < pos:
                comp = ct
            else:
                break
        out.append({"id": mid, "competition": comp, "round": rnd, "date": date,
                    "home": seen[0], "away": seen[1], "score": score,
                    "formation": fh.group(1) if fh else None})
    return out

TEAMHDR = re.compile(r'aufstellung-unterueberschrift-mannschaft.*?title="([^"]+)"', re.S)
CONT = re.compile(r'<div class="formation-player-container" style="top: ([0-9.]+)%; left: ([0-9.]+)%;">')

def parse_lineups(html):
    """Return {team_name: [ {slug, name, number, top, left}, ... ]} for the 11 starters."""
    headers = [(m.start(), m.group(1)) for m in TEAMHDR.finditer(html)]
    teams = {name: [] for _, name in headers}
    for m in CONT.finditer(html):
        blob = html[m.end(): m.end() + 1400]
        nm = re.search(r'formation-number-name">\s*<a href="/([^/]+)/profil/spieler/(\d+)">([^<]+)</a>', blob, re.S)
        if not nm:
            continue
        num = re.search(r'tm-shirt-number[^>]*>\s*(\d+)\s*<', blob, re.S)
        top = float(m.group(1)); left = float(m.group(2))
        team = None
        for hp, hn in headers:
            if hp < m.start():
                team = hn
            else:
                break
        if team is None:
            continue
        teams[team].append({"slug": nm.group(1), "tmId": nm.group(2),
                            "tmName": nm.group(3).strip(),
                            "number": int(num.group(1)) if num else None,
                            "top": top, "left": left})
    return teams
