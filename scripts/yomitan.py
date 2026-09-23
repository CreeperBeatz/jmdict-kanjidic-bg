"""Package data/ as a Yomitan dictionary (format 3).

    python scripts/yomitan.py      # -> dist/jmdict-kanjidic-bg-yomitan.zip

One term row per sense, sharing the JMdict id as the sequence, so Yomitan's
grouped and merged modes put a word's senses back together. Spellings follow
JMdict: a reading pairs with every written form unless it is restricted to
some of them (re_restr) or takes none (re_nokanji); search-only forms (sK/sk)
are left out, as JMdict asks. Words usually written in kana (uk) also get a
kana-only row, so they are found and shown as they are written.
"""

from __future__ import annotations

import json
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DIST = ROOT / "dist"
URL = "https://github.com/CreeperBeatz/jmdict-kanjidic-bg"
BANK = 10_000  # rows per bank file

POS = {
    "n": "съществително",
    "vt": "преходен глагол",
    "vi": "непреходен глагол",
    "vs": "съществително, което приема する",
    "vs-s": "глагол на する (особен клас)",
    "vs-i": "глагол на する",
    "vs-c": "глагол на す, предшественик на する",
    "adj-no": "съществително, което приема の",
    "adj-na": "на-прилагателно",
    "adj-i": "и-прилагателно",
    "adj-ix": "и-прилагателно (よい/いい)",
    "adj-f": "съществително или глагол като определение",
    "adj-t": "тару-прилагателно",
    "adj-pn": "предноименно определение (рентаиши)",
    "adj-ku": "ку-прилагателно (класическо)",
    "v1": "глагол ичидан",
    "v1-s": "глагол ичидан (くれる)",
    "v5aru": "глагол годан на -ある (особен клас)",
    "v5b": "глагол годан на -ぶ",
    "v5g": "глагол годан на -ぐ",
    "v5k": "глагол годан на -く",
    "v5k-s": "глагол годан (行く/いく)",
    "v5m": "глагол годан на -む",
    "v5n": "глагол годан на -ぬ",
    "v5r": "глагол годан на -る",
    "v5r-i": "глагол годан на -る (неправилен)",
    "v5s": "глагол годан на -す",
    "v5t": "глагол годан на -つ",
    "v5u": "глагол годан на -う",
    "v5u-s": "глагол годан на -う (особен клас)",
    "vz": "глагол ичидан на -ずる",
    "vk": "глагол くる (особен клас)",
    "vr": "неправилен глагол на -る (-り)",
    "v2a-s": "глагол нидан на -う (класически)",
    "v4b": "глагол йодан на -ぶ (класически)",
    "adv": "наречие",
    "adv-to": "наречие с と",
    "exp": "израз",
    "n-suf": "съществително като наставка",
    "n-pref": "съществително като представка",
    "suf": "наставка",
    "pref": "представка",
    "prt": "частица",
    "int": "междуметие",
    "ctr": "брояч",
    "conj": "съюз",
    "pn": "местоимение",
    "aux-v": "спомагателен глагол",
    "aux": "спомагателна дума",
    "aux-adj": "спомагателно прилагателно",
    "num": "числително",
    "cop": "свързка",
    "unc": "некласифицирано",
}

MISC = {
    "uk": "обикновено се пише с кана",
    "abbr": "съкращение",
    "on-mim": "звукоподражание",
    "arch": "архаично",
    "col": "разговорно",
    "hist": "исторически термин",
    "yoji": "четирийероглифен израз (йоджиджукуго)",
    "hon": "почтителна реч (сонкейго)",
    "pol": "учтива реч (тейнейго)",
    "hum": "скромна реч (кенджого)",
    "dated": "остаряващо",
    "obs": "остаряло",
    "sl": "жаргон",
    "net-sl": "интернет жаргон",
    "form": "официално",
    "fam": "фамилиарно",
    "derog": "пренебрежително",
    "rare": "рядко",
    "sens": "деликатна тема",
    "id": "идиом",
    "male": "мъжка реч",
    "fem": "женска реч",
    "poet": "поетично",
    "vulg": "вулгарно",
    "chn": "детска реч",
    "euph": "евфемизъм",
    "joc": "шеговито",
    "person": "име на човек",
    "place": "име на място",
    "work": "заглавие на творба",
    "quote": "цитат",
    "proverb": "пословица",
}

FORM = {
    "ateji": "атеджи (знаци, избрани за звученето им)",
    "gikun": "гикун (особено четене)",
    "iK": "неправилен запис",
    "ik": "неправилна кана",
    "io": "неправилна окуригана",
    "oK": "остарял запис",
    "ok": "остаряла кана",
    "rK": "рядък запис",
    "rk": "рядка кана",
}
SEARCH_ONLY = {"sK", "sk"}

# Yomitan's deinflector keys off these rule names.
RULES = {"v1": "v1", "v1-s": "v1", "vs": "vs", "vs-s": "vs", "vs-i": "vs", "vz": "vz",
         "vk": "vk", "adj-i": "adj-i", "adj-ix": "adj-i"}


def rules(pos: list[str]) -> str:
    out = []
    for p in pos:
        r = RULES.get(p) or ("v5" if p.startswith("v5") else None)
        if r and r not in out:
            out.append(r)
    return " ".join(out)


def bg_number(n: int) -> str:
    return f"{n:,}".replace(",", "\N{NO-BREAK SPACE}")  # 30 200, as Bulgarian writes it


def katakana(s: str) -> str:
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def pairs(w: dict) -> list[tuple[str, str, list[str]]]:
    """(expression, reading, form tags) for every spelling Yomitan should index."""
    kanji = [k for k in w["kanji"] if not SEARCH_ONLY & set(k.get("info", []))]
    kana = [r for r in w["kana"] if not SEARCH_ONLY & set(r.get("info", []))]
    uk = any("uk" in s.get("misc", []) for s in w["senses"])
    out = []
    for r in kana:
        r_tags = [i for i in r.get("info", []) if i in FORM]
        if not kanji or r.get("nokanji") or uk:
            out.append((r["text"], "", r_tags))
        if r.get("nokanji"):
            continue
        for k in kanji:
            if r.get("only") and k["text"] not in r["only"]:
                continue
            k_tags = [i for i in k.get("info", []) if i in FORM]
            out.append((k["text"], r["text"], k_tags + [t for t in r_tags if t not in k_tags]))
    return out


def main() -> int:
    words = [json.loads(l) for l in (DATA / "words.jsonl").open(encoding="utf-8")]
    kanji = [json.loads(l) for l in (DATA / "kanji.jsonl").open(encoding="utf-8")]
    stats = json.loads((DATA / "stats.json").read_text(encoding="utf-8"))

    terms = []
    for w in words:
        # nf01 (the top 500) scores 48 .. nf48 scores 1; other common words 1
        common = any(f.get("pri") for f in w["kanji"] + w["kana"])
        score = 49 - w["nf"] if w["nf"] else int(common)
        for expr, reading, form_tags in pairs(w):
            for s in w["senses"]:
                pos, misc = s.get("pos", []), s.get("misc", [])
                terms.append([expr, reading, " ".join(pos + misc), rules(pos), score, s["bg"], w["id"],
                              " ".join(form_tags)])

    kanji_rows = [
        [k["char"], " ".join(katakana(o) for o in k["on"]), " ".join(k["kun"]), "", k["bg"], {}]
        for k in kanji
    ]

    tags = (
        [[t, "partOfSpeech", 0, n, 0] for t, n in POS.items()]
        + [[t, "misc", 0, n, 0] for t, n in MISC.items()]
        + [[t, "form", 0, n, 0] for t, n in FORM.items()]
    )

    index = {
        "title": "JMdict/KANJIDIC BG (машинен превод)",
        "revision": f"jmdict-{stats['jmdict']}.{date.today().isoformat()}",
        "format": 3,
        "sequenced": True,
        "author": "CreeperBeatz",
        "url": URL,
        "sourceLanguage": "ja",
        "targetLanguage": "bg",
        "description": (
            f"Японско-български речник: {bg_number(stats['words'])} често срещани думи от JMdict и "
            f"{bg_number(stats['kanji'])} йероглифа от KANJIDIC, машинно преведени от английски "
            "(Claude Sonnet 5). Преводът не е проверен от човек; значенията, завършващи "
            "на „?“, са несигурни."
        ),
        "attribution": (
            "Machine translation of JMdict and KANJIDIC, (c) the Electronic Dictionary Research "
            "and Development Group (EDRDG), used under CC BY-SA 4.0. This dictionary: CC BY-SA 4.0. "
            + URL
        ),
    }

    DIST.mkdir(exist_ok=True)
    path = DIST / "jmdict-kanjidic-bg-yomitan.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        def put(name: str, obj) -> None:
            z.writestr(name, json.dumps(obj, ensure_ascii=False, separators=(",", ":")))

        put("index.json", index)
        put("tag_bank_1.json", tags)
        for n, start in enumerate(range(0, len(terms), BANK), 1):
            put(f"term_bank_{n}.json", terms[start:start + BANK])
        for n, start in enumerate(range(0, len(kanji_rows), BANK), 1):
            put(f"kanji_bank_{n}.json", kanji_rows[start:start + BANK])
    print(f"{path.relative_to(ROOT)}: {len(terms):,} term rows, {len(kanji_rows):,} kanji, "
          f"{path.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
