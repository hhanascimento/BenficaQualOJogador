#!/usr/bin/env python3
"""Data repairs for src/data/hints.json.

1. Positions are reduced to the four the game shows: **Guarda-Redes, Defesa,
   Médio, Avançado**. The build passes wrote the source wording ("lateral-direito",
   "extremo", "trinco", …), which is too fine-grained for the position clue.

2. Five players were matched to the wrong source page and ended up carrying a
   namesake's career, so each pair of records was identical:

       rui-bento   == paulo-bento        bento pair   (both born 1969, 35 caps)
       glenn-helder== helder-cristovao   helder pair  (both born 1971, 35 caps)
       fernando-aguiar == bruno-aguiar   aguiar pair  (both born 1981, 2 caps)
       gil-dias    == ruben-dias         dias pair    (both born 1997, 74 caps)
       caio-lucas  == lucas-verissimo    lucas pair   (both born 1995, 2 caps)

   The first name of each pair keeps the data it already had (it matches that
   player); the second is rebuilt here from Wikipedia — pt.wikipedia infoboxes
   except Glenn Helder (en.wikipedia), read on 2026-10-12. Benfica appearances
   and goals are the league figures the infoboxes carry.

3. The nationality clue is normalised: the build mixed country names into the
   adjective slot ("Tem nacionalidade Portugal."), misgendered a few
   ("A nacionalidade é russo.") and left four plainly broken
   ("border|20px União Soviética", "ês o", "o o"). Every clue is rewritten to
   "Tem nacionalidade <adjectivo>."

4. Paulo Bento kept the pair's identity (born 1969, 35 caps) but also its
   Benfica spell, which is not his: en.wikipedia has him at Benfica in
   1994-1996 with 49 league games and 2 goals, not 1988-1996 and 69.

    python3 tools/fix_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HINTS = ROOT / "src" / "data" / "hints.json"

# --- 1. positions -----------------------------------------------------------

BUCKET = {
    "guarda-redes": "Guarda-Redes",
    "defesa": "Defesa", "defesa central": "Defesa", "defesa esquerdo": "Defesa",
    "defesa direito central esquerdo": "Defesa",
    "lateral": "Defesa", "lateral-esquerdo": "Defesa", "lateral-direito": "Defesa",
    "lateral esquerdo": "Defesa", "lateral direito": "Defesa",
    "zagueiro ou lateral-esquerdo": "Defesa",
    "médio": "Médio", "médio defensivo": "Médio", "médio ofensivo": "Médio",
    "trinco": "Médio", "meia-atacante": "Médio", "meio-campo": "Médio",
    "meia-ofensivo": "Médio", "meia-direita": "Médio", "meio-armador": "Médio",
    "meio-campista ou ponta-direita": "Médio", "meio-campista e ponta-esquerda": "Médio",
    "avançado": "Avançado", "ex–avançado": "Avançado", "ponta-de-lança": "Avançado",
    "extremo": "Avançado", "extremo-esquerdo": "Avançado",
    "ponta-esquerda": "Avançado", "ponta-direita": "Avançado",
    # already-bucketed values, so rerunning the tool is a no-op
    "Guarda-Redes": "Guarda-Redes", "Defesa": "Defesa",
    "Médio": "Médio", "Avançado": "Avançado",
}


# Two records keep a "Perfil" clue describing the role they usually filled, which
# is not always the position the dataset lists; bucket each one on its own.
PERFIL = {"vitor-martins": "Avançado", "manuel-fernandes": "Médio"}


def bucketed(position: str) -> str:
    key = position.strip()
    if key in BUCKET:
        return BUCKET[key]
    raise SystemExit(f"unmapped position: {key!r}")


def clue(label: str, text: str) -> dict:
    return {"label": label, "text": text}


# --- 2. the five mismatched players ----------------------------------------

# Each entry keeps the same hint order the build produced:
# nacionalidade · posição · época · estreia · clubes · ligas · temporadas ·
# jogos · golos · internacionalizações · nascimento, with the career fallbacks
# the build uses ("Fim de carreira", "Clube onde terminou", "Altura") standing in
# for the stats a player does not have.
FIXED: dict[str, dict] = {
    # Netherlands, 11 caps/1 goal for Benfica in a 1996-97 loan spell.
    "glenn-helder": {
        "nationality": "neerlandesa",
        "position": "Avançado",
        "first": 1996, "last": 1997, "eras": ["1990s"],
        "benficaSeasons": 1, "benficaApps": 11, "benficaGoals": 1,
        "hints": [
            clue("Nacionalidade", "Tem nacionalidade neerlandesa."),
            clue("Posição", "Jogava na posição de avançado."),
            clue("Época", "No Benfica, jogou nos anos 90."),
            clue("Estreia", "Começou a carreira profissional em 1989."),
            clue("Clubes", "Passou por 10 clubes ao longo da carreira."),
            clue("Ligas", "Representou clubes de 5 ligas diferentes."),
            clue("Temporadas", "Fez 1 temporada no Benfica."),
            clue("Jogos", "Disputou 11 jogos pelo Benfica."),
            clue("Golos", "Marcou 1 golo pelo Benfica."),
            clue("Internacionalizações", "Somou 4 internacionalizações."),
            clue("Nascimento", "Nasceu em 1968."),
        ],
    },
    # Benfica 1991-92 only (24 games), then Boavista and Sporting CP.
    "rui-bento": {
        "fullName": "Rui Fernando da Silva Calapez Pereira Bento",
        "nationality": "portuguesa",
        "position": "Defesa",
        "first": 1991, "last": 1992, "eras": ["1990s"],
        "benficaSeasons": 1, "benficaApps": 24, "benficaGoals": 0,
        "hints": [
            clue("Nacionalidade", "Tem nacionalidade portuguesa."),
            clue("Posição", "Jogava na posição de defesa."),
            clue("Época", "No Benfica, jogou nos anos 90."),
            clue("Estreia", "Começou a carreira profissional em 1991."),
            clue("Clubes", "Passou por 3 clubes ao longo da carreira."),
            clue("Temporadas", "Fez 1 temporada no Benfica."),
            clue("Jogos", "Disputou 24 jogos pelo Benfica."),
            clue("Internacionalizações", "Somou 6 internacionalizações."),
            clue("Nascimento", "Nasceu em 1972."),
            clue("Fim de carreira", "Terminou a carreira em 2004."),
            clue("Clube onde terminou", "O último clube da carreira foi o Sporting Clube de Portugal."),
        ],
    },
    # Canadian-born defensive midfielder, 13 caps for Canada, at Benfica 2002-04.
    "fernando-aguiar": {
        "nationality": "canadiana e portuguesa",
        "position": "Médio",
        "first": 2002, "last": 2004, "eras": ["2000s"],
        "benficaSeasons": 2, "benficaApps": 38, "benficaGoals": 3,
        "hints": [
            clue("Nacionalidade", "Tem nacionalidade canadiana e portuguesa."),
            clue("Posição", "Jogava na posição de médio."),
            clue("Época", "No Benfica, jogou nos anos 2000."),
            clue("Estreia", "Começou a carreira profissional em 1991."),
            clue("Clubes", "Passou por 11 clubes ao longo da carreira."),
            clue("Ligas", "Representou clubes de 3 ligas diferentes."),
            clue("Temporadas", "Fez 2 temporadas no Benfica."),
            clue("Jogos", "Disputou 38 jogos pelo Benfica."),
            clue("Golos", "Marcou 3 golos pelo Benfica."),
            clue("Internacionalizações", "Somou 13 internacionalizações."),
            clue("Nascimento", "Nasceu em 1972."),
        ],
    },
    # Portuguese winger, at Benfica 2021-23 (12 games, 1 goal), many loans.
    "gil-dias": {
        "nationality": "portuguesa",
        "position": "Avançado",
        "first": 2021, "last": 2023, "eras": ["2020s"],
        "benficaSeasons": 2, "benficaApps": 12, "benficaGoals": 1,
        "hints": [
            clue("Nacionalidade", "Tem nacionalidade portuguesa."),
            clue("Posição", "Jogava na posição de avançado."),
            clue("Época", "No Benfica, jogou nos anos 2020."),
            clue("Estreia", "Começou a carreira profissional em 2014."),
            clue("Clubes", "Passou por 14 clubes ao longo da carreira."),
            clue("Ligas", "Representou clubes de 8 ligas diferentes."),
            clue("Temporadas", "Fez 2 temporadas no Benfica."),
            clue("Jogos", "Disputou 12 jogos pelo Benfica."),
            clue("Golos", "Marcou 1 golo pelo Benfica."),
            clue("Altura", "Mede 1,83 m de altura."),
            clue("Nascimento", "Nasceu em 1996."),
        ],
    },
    # Brazilian-born left winger, at Benfica 2019-21 (11 games, 1 goal), now a
    # United Arab Emirates international.
    "caio-lucas": {
        "nationality": "brasileira",
        "position": "Avançado",
        "first": 2019, "last": 2021, "eras": ["2010s", "2020s"],
        "benficaSeasons": 2, "benficaApps": 11, "benficaGoals": 1,
        "hints": [
            clue("Nacionalidade", "Tem nacionalidade brasileira."),
            clue("Posição", "Jogava na posição de avançado."),
            clue("Época", "No Benfica, jogou nos anos 2010 e 2020."),
            clue("Estreia", "Começou a carreira profissional em 2014."),
            clue("Clubes", "Passou por 4 clubes ao longo da carreira."),
            clue("Ligas", "Representou clubes de 3 ligas diferentes."),
            clue("Temporadas", "Fez 2 temporadas no Benfica."),
            clue("Jogos", "Disputou 11 jogos pelo Benfica."),
            clue("Golos", "Marcou 1 golo pelo Benfica."),
            clue("Internacionalizações", "Somou 4 internacionalizações."),
            clue("Nascimento", "Nasceu em 1994."),
        ],
    },
}


# Paulo Bento's own Benfica spell (en.wikipedia).
PAULO_BENTO = {
    "first": 1994, "last": 1996, "eras": ["1990s"],
    "benficaSeasons": 2, "benficaApps": 49, "benficaGoals": 2,
}
PAULO_BENTO_CLUES = {
    "Época": "No Benfica, jogou nos anos 90.",
    "Temporadas": "Fez 2 temporadas no Benfica.",
    "Jogos": "Disputou 49 jogos pelo Benfica.",
    "Golos": "Marcou 2 golos pelo Benfica.",
}


# Nationality clues to rewrite, keyed by the clue the build produced. Country
# names become adjectives ("Portugal" -> portuguesa), the two corrupted ones are
# filled in by hand (Alexander Bah is Danish, Leandro Barreiro Luxembourgish).
NATIONALITY_CLUES = {
    "Tem nacionalidade Alemanha Oriental.": "Tem nacionalidade alemã (Alemanha Oriental).",
    "Tem nacionalidade Alemanha.": "Tem nacionalidade alemã.",
    "Tem nacionalidade Argentina.": "Tem nacionalidade argentina.",
    "Tem nacionalidade Brasil.": "Tem nacionalidade brasileira.",
    "Tem nacionalidade Camarões.": "Tem nacionalidade camaronês.",
    "Tem nacionalidade Grécia.": "Tem nacionalidade grega.",
    "Tem nacionalidade Hungria.": "Tem nacionalidade húngara.",
    "Tem nacionalidade Iugoslávia.": "Tem nacionalidade jugoslava.",
    "Tem nacionalidade Portugal.": "Tem nacionalidade portuguesa.",
    "Tem nacionalidade República Tcheca (ex-Tchecoslováquia).": "Tem nacionalidade checa.",
    "Tem nacionalidade Suécia.": "Tem nacionalidade sueca.",
    "Tem nacionalidade Uruguai.": "Tem nacionalidade uruguaia.",
    "Tem nacionalidade África Oriental Portuguesa.": "Tem nacionalidade portuguesa.",
    "A nacionalidade é argentino.": "Tem nacionalidade argentina.",
    "A nacionalidade é esloveno.": "Tem nacionalidade eslovena.",
    "A nacionalidade é russo.": "Tem nacionalidade russa.",
    "A nacionalidade é português.": "Tem nacionalidade portuguesa.",
    "É de Bulgária.": "Tem nacionalidade búlgara.",
    "É de Eslovénia.": "Tem nacionalidade eslovena.",
    "É de Honduras.": "Tem nacionalidade hondurenha.",
    "É de Lituânia.": "Tem nacionalidade lituana.",
    "É de Reino Unido.": "Tem nacionalidade britânica.",
    "É de União Soviética.": "Tem nacionalidade soviética.",
    "Tem nacionalidade camaronense.": "Tem nacionalidade camaronês.",
    "A nacionalidade é portuguesa.": "Tem nacionalidade portuguesa.",
    "A nacionalidade é croata.": "Tem nacionalidade croata.",
    "Tem nacionalidade border|20px União Soviética.": "Tem nacionalidade soviética.",
    "A nacionalidade é ês o.": "Tem nacionalidade dinamarquesa.",
    "A nacionalidade é o o.": "Tem nacionalidade luxemburguesa.",
}


def set_clue(record: dict, label: str, text: str) -> None:
    for hint in record["hints"]:
        if hint["label"] == label:
            hint["text"] = text
            return
    raise SystemExit(f"missing {label!r} clue")


def main() -> None:
    book = json.loads(HINTS.read_text(encoding="utf-8"))

    touched = 0
    for slug, record in book.items():
        position = (record.get("position") or "").strip()
        if not position:
            # a couple of records only ever carried the clue, not the field
            clue_text = next((h["text"] for h in record["hints"] if h["label"] == "Posição"), "")
            position = clue_text.split("posição de ")[-1].rstrip(".").strip()
        if not position:
            continue
        bucket = bucketed(position)
        if bucket != position:
            touched += 1
        record["position"] = bucket
        for hint in record["hints"]:
            if hint["label"] == "Posição":
                hint["text"] = f"Jogava na posição de {bucket.lower()}."
    for slug, bucket in PERFIL.items():
        for hint in book[slug]["hints"]:
            if hint["label"] == "Perfil":
                hint["text"] = f"Alinhava habitualmente como {bucket.lower()}."

    for slug, fix in FIXED.items():
        record = book[slug]
        record.update({k: v for k, v in fix.items()})
        record["hints"] = fix["hints"]

    rewritten = 0
    for record in book.values():
        for hint in record["hints"]:
            if hint["label"] == "Nacionalidade" and hint["text"] in NATIONALITY_CLUES:
                hint["text"] = NATIONALITY_CLUES[hint["text"]]
                rewritten += 1

    paulo = book["paulo-bento"]
    paulo.update(PAULO_BENTO)
    for label, text in PAULO_BENTO_CLUES.items():
        set_clue(paulo, label, text)

    HINTS.write_text(json.dumps(book, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"positions bucketed: {touched}; records rebuilt: {len(FIXED)}; "
          f"nationality clues rewritten: {rewritten}")


if __name__ == "__main__":
    main()
