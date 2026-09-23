"""Build data/ from the Better Kanji Dictionary translation run.

    python scripts/build.py [--source ../BetterRTK]

Reads, from the BetterRTK checkout:

  pipeline/translate/in/*.json    what each translator was shown (English
                                  glosses, part of speech, usage notes)
  pipeline/translate/out/*.json   what it wrote back (the Bulgarian)
  pipeline/data/JMdict_e.gz       for each entry's spellings and which reading
                                  goes with which spelling

and writes data/words.jsonl, data/kanji.jsonl and their .tsv flattenings.
Only chunks with an output are included; the rest of JMdict is not translated
yet. The build refuses to write anything if an output does not line up with
its input, entry for entry and sense for sense.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"
SEP = " | "  # joins glosses in the TSV files; glosses contain ";" but never "|" (checked below)


def load_chunks(src: Path, kind: str) -> list[tuple[dict, dict]]:
    pairs = []
    for out_path in sorted((src / "pipeline/translate/out").glob(f"{kind}-*.json")):
        in_path = src / "pipeline/translate/in" / out_path.name
        if not in_path.exists():
            raise SystemExit(f"{out_path.name}: no input chunk at {in_path}")
        pairs.append((
            json.loads(in_path.read_text(encoding="utf-8")),
            json.loads(out_path.read_text(encoding="utf-8")),
        ))
    return pairs


def jmdict_forms(path: Path, wanted: set[int]) -> tuple[dict[int, dict], str]:
    """Spellings of the wanted entries, with JMdict's codes kept as codes."""
    raw = gzip.open(path, "rt", encoding="utf-8").read()
    created = re.search(r"<!-- JMdict created: ([\d-]+) -->", raw)
    declared = set(re.findall(r'<!ENTITY\s+([\w-]+)\s+"', raw))
    raw = re.sub(r"<!DOCTYPE.*?\]>", "", raw, count=1, flags=re.DOTALL)
    raw = re.sub(r"&([\w-]+);", lambda m: m.group(1) if m.group(1) in declared else m.group(0), raw)

    NF = re.compile(r"^nf(\d+)$")
    forms: dict[int, dict] = {}
    for entry in ET.fromstring(raw).iter("entry"):
        wid = int(entry.findtext("ent_seq"))
        if wid not in wanted:
            continue
        nf = None
        kanji, kana = [], []
        for el in entry.findall("k_ele"):
            f = {"text": el.findtext("keb")}
            info = [i.text for i in el.findall("ke_inf") if i.text]
            pri = [p.text for p in el.findall("ke_pri") if p.text]
            if info:
                f["info"] = info
            if pri:
                f["pri"] = pri
            kanji.append(f)
        for el in entry.findall("r_ele"):
            f = {"text": el.findtext("reb")}
            info = [i.text for i in el.findall("re_inf") if i.text]
            pri = [p.text for p in el.findall("re_pri") if p.text]
            only = [r.text for r in el.findall("re_restr") if r.text]
            if info:
                f["info"] = info
            if pri:
                f["pri"] = pri
            if only:
                f["only"] = only
            if el.find("re_nokanji") is not None:
                f["nokanji"] = True
            kana.append(f)
        for f in kanji + kana:
            for p in f.get("pri", []):
                if m := NF.match(p):
                    nf = int(m.group(1)) if nf is None else min(nf, int(m.group(1)))
        forms[wid] = {"kanji": kanji, "kana": kana, "nf": nf}
    return forms, created.group(1) if created else "unknown"


def build_words(src: Path) -> tuple[list[dict], str]:
    chunks = load_chunks(src, "words")
    ids = {e["id"] for inp, _ in chunks for e in inp["entries"]}
    forms, jmdict_date = jmdict_forms(src / "pipeline/data/JMdict_e.gz", ids)

    words = []
    for inp, out in chunks:
        by = out.get("by") or "claude"
        got = {e["id"]: {s["i"]: s["bg"] for s in e["senses"]} for e in out["entries"]}
        for e in inp["entries"]:
            bg = got.get(e["id"])
            if bg is None:
                raise SystemExit(f"{inp['chunk']}: entry {e['id']} has no translation")
            if e["id"] not in forms:
                raise SystemExit(f"{inp['chunk']}: entry {e['id']} is not in this JMdict_e.gz")
            senses = []
            for s in e["senses"]:
                if s["i"] not in bg:
                    raise SystemExit(f"{inp['chunk']}: entry {e['id']} sense {s['i']} has no translation")
                row = {"i": s["i"]}
                if s.get("pos"):
                    row["pos"] = s["pos"]
                if s.get("misc"):
                    row["misc"] = s["misc"]
                row["en"] = s["en"]
                row["bg"] = bg[s["i"]]
                senses.append(row)
            if len(bg) != len(senses):
                raise SystemExit(f"{inp['chunk']}: entry {e['id']} has senses the input does not")
            f = forms[e["id"]]
            words.append({
                "id": e["id"],
                "kanji": f["kanji"],
                "kana": f["kana"],
                "nf": f["nf"],
                "senses": senses,
                "source": f"mt:{by}",
            })
    return words, jmdict_date


def build_kanji(src: Path) -> list[dict]:
    kanji = []
    for inp, out in load_chunks(src, "kanji"):
        by = out.get("by") or "claude"
        got = {k["char"]: k["bg"] for k in out["kanji"]}
        if len(got) != len(inp["kanji"]):
            raise SystemExit(f"{inp['chunk']}: {len(got)} kanji out, {len(inp['kanji'])} in")
        for k in inp["kanji"]:
            if k["char"] not in got:
                raise SystemExit(f"{inp['chunk']}: {k['char']} has no translation")
            kanji.append({
                "char": k["char"],
                "on": k["on"],
                "kun": k["kun"],
                "en": k["meanings"],
                "bg": got[k["char"]],
                "source": f"mt:{by}",
            })
    return kanji


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")


def joined(items: list[str]) -> str:
    for g in items:
        if SEP.strip() in g or "\t" in g or "\n" in g:
            raise SystemExit(f"gloss {g!r} contains a separator; the TSV cannot hold it")
    return SEP.join(items)


def write_tsv(path: Path, header: list[str], rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE, quotechar=None)
        w.writerow(header)
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, default=ROOT.parent / "BetterRTK", help="BetterRTK checkout")
    args = ap.parse_args()

    words, jmdict_date = build_words(args.source)
    kanji = build_kanji(args.source)

    OUT.mkdir(exist_ok=True)
    write_jsonl(OUT / "words.jsonl", words)
    write_jsonl(OUT / "kanji.jsonl", kanji)

    def headword(w: dict) -> str:
        return (w["kanji"] or w["kana"])[0]["text"]

    write_tsv(
        OUT / "words.tsv",
        ["jmdict_id", "sense", "headword", "reading", "pos", "en", "bg"],
        (
            [w["id"], s["i"], headword(w), w["kana"][0]["text"], ",".join(s.get("pos", [])),
             joined(s["en"]), joined(s["bg"])]
            for w in words for s in w["senses"]
        ),
    )
    write_tsv(
        OUT / "kanji.tsv",
        ["kanji", "on", "kun", "en", "bg"],
        ([k["char"], " ".join(k["on"]), " ".join(k["kun"]), joined(k["en"]), joined(k["bg"])] for k in kanji),
    )

    senses = sum(len(w["senses"]) for w in words)
    unsure = sum(g.endswith("?") for w in words for s in w["senses"] for g in s["bg"])
    unsure += sum(g.endswith("?") for k in kanji for g in k["bg"])
    stats = {
        "jmdict": jmdict_date,
        "words": len(words),
        "senses": senses,
        "kanji": len(kanji),
        "unsure_glosses": unsure,
        "models": sorted({w["source"] for w in words} | {k["source"] for k in kanji}),
    }
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
