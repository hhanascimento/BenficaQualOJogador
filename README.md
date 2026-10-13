# Benfica — Qual o Jogador

A little football-history guessing game: the app hides one **Sport Lisboa e Benfica**
player and reveals clues about his career, one at a time. Type his name to guess.
The fewer clues you use and the faster you are, the higher you score.

Built with **Ionic + React 19 + TypeScript + Vite**, reusing the player photos and the
overall look & feel of the *Benfica Onze Inicial* app.

## Run it

```bash
npm ci         # or: npm install
npm run dev    # http://localhost:3000
npm run build  # typecheck (tsc -b) + production build
npm run lint   # oxlint
npm test       # data + rules checks (node tools/verify.ts)
npm run icons  # regenerate public/app-icon.svg + PNG icons (needs /tmp/Roboto-Black.ttf)
```

## Screens

One screen is mounted at a time (`src/App.tsx`):

| Screen | Component | What it does |
| --- | --- | --- |
| **Home** | `src/components/Home.tsx` | The app icon and two ways in: **Jogar** and **Instruções**. Repeats your saved career stats once you have played. |
| **Era picker** | `src/components/EraSelect.tsx` | Shown before every game: which decade should the player come from? A player who was at Benfica in two decades can be drawn in either. Each option shows how many players it holds. |
| **Game** | `src/components/Game.tsx` | One hidden player per round: revealed clues, the guess box with suggestions, **Mostrar Dica**, and **Resolve** once the last clue is out. |
| **Instructions** | `src/components/Help.tsx` | "Como jogar": the rules, how names match and how the score is worked out. |

Everything is in Portuguese (pt-PT).

## How a round works

- Each player carries up to **11 clues**, ordered from vaguest to most revealing:
  nationality, position, the decades at Benfica, debut year, number of clubs, number
  of leagues, seasons / games / goals for Benfica, international caps and birth year.
- **Mostrar Dica** uncovers the next clue. Once they are all out, a **Resolve** button
  appears — it reveals the player but scores nothing.
- Wrong guesses are free and unlimited.
- When the round ends the player's **photo** is shown, with the season and career totals.

### Scoring (`src/lib/game.ts`)

A perfect round (no clues, instantly) is **1000 points**:

```
points = max(0, 1000 − 50 × dicas usadas − segundos)
```

| | |
| --- | --- |
| base | 1000 |
| each clue | −50 |
| each second | −1 |
| **Resolve** | 0 (not solved) |

## Data

`src/data/hints.json` — one record per player, keyed by the same slug the photos use:

```jsonc
"fernando-cruz": {
  "name": "Cruz",                        // the name the game asks for
  "fullName": "Fernando da Conceição Cruz",  // first + last name, shown on the reveal
  "photo": "assets/players/fernando-cruz.jpg",
  "position": "defesa",
  "nationality": "Portugal",
  "first": 1959, "last": 1970,
  "eras": ["1950s", "1960s", "1970s"],
  "benficaSeasons": 11, "benficaApps": 227, "benficaGoals": 3,
  "hints": [ { "label": "Nacionalidade", "text": "Tem nacionalidade portuguesa." }, … ]
}
```

`name` is the short name the player was known by, which is what the round asks
for; `fullName` is the first + last name the round summary reveals (259 of the
414 players carry one — the rest are already known by a full name). `position`
is always one of the four the game shows — **Guarda-Redes, Defesa, Médio,
Avançado** (`tools/fix_data.py` folds the source wording, e.g. "lateral-direito"
and "extremo", into those).

The dataset covers **414 players** — every player who appears in the *Onze Inicial*
match dataset and for whom career data could be found (most carry 9–11 clues).

### How the clues were built

Two passes, merged (`tools/`):

1. `tools/build_hints_wd.py` — pulls every Wikidata item that lists *S.L. Benfica*
   (Q131499) as a `P54` "member of sports team", together with each item's full
   `P54` career (`P580`/`P582` dates, `P1350` matches, `P1351` goals), `P27`
   nationality, `P413` position and `P569` date of birth, and matches them to the
   dataset by name.
2. `tools/build_hints.py` — the Wikipedia infobox pass (`{{Info/Futebolista}}` /
   `{{Infobox football biography}}`), fetched in batches and cached under `/tmp/qj`.
3. `tools/merge_hints.py` — for each player, keeps whichever record's Benfica spell
   best matches the seasons in `src/data/matches.json`, then writes `src/data/hints.json`.

> zerozero.pt was the suggested reference but blocks scripted access; the clues come
> from public Wikipedia/Wikidata infoboxes instead. Numbers are official-career best
> efforts and should be spot-checked before any serious use.

## The mark

The mark keeps the *Onze Inicial* identity — an outlined **Roboto** (Apache-2.0)
wordmark and the club crest — but the words read **QUAL O JOGADOR**:

| File | What it is |
| --- | --- |
| `public/assets/qual-o-jogador-logo.svg` | The Home/Help logo lockup: the club crest, the **QUAL O JOGADOR** wordmark and the red-to-gold rule. |
| `public/assets/benfica-logo.svg` | The club crest on its own (the source art for the lockup). |
| `public/app-icon.svg` | The browser/app icon: a red rounded plate, a gold rule and **BENFICA / QUAL O / JOGADOR**, wordmark converted to outlines (no font needed). |
| `public/icon-192.png`, `store/app-icon-512.png` | Raster versions of the app-icon plate. |
| `tools/build_full_names.py` | Resolves each player's accented first + last name for the reveal. |
| `tools/fix_data.py` | Folds positions into the four the game shows and repairs mismatched records. |
| `tools/home_logo.py` | Rebuilds the lockup from the crest and a Roboto Bold TTF. |
| `tools/icon.py` | Regenerates the app icon from a Roboto Black TTF. |
| `tools/android_icons.py` | Regenerates every Android launcher density (legacy, round, adaptive). |

## Photos

The player photos under `public/assets/players/` are the same public Wikimedia
Commons files the *Onze Inicial* project uses; they are shown only to identify the
players.
