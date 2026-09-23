# jmdict-kanjidic-bg

**Bulgarian glosses for JMdict and KANJIDIC: 30,200 common Japanese words and
10,350 kanji, machine-translated from English.**

As far as I know, this is the first open Japanese–Bulgarian dictionary data. It was made for
[Better Kanji Dictionary](https://betterkanjidictionary.org), where Bulgarian
speakers can search in Cyrillic (or шльокавица) and read the glosses under
each word, and it is published here so that anyone can use it.

**Японско-български речникови данни**, машинно преведени от английските
значения на JMdict и KANJIDIC: 30 200 често срещани думи и 10 350 йероглифа.
Преводът не е проверен от човек. Свободен лиценз CC BY-SA 4.0. Има и речник
за [Yomitan](https://yomitan.wiki) (виж [Releases](../../releases)).

| | count |
|---|---|
| JMdict entries | 30,200 |
| senses | 46,920 |
| kanji | 10,350 |
| glosses the translator marked unsure (`?`) | 1,595 |

**This is machine translation that no human has reviewed yet.** Treat it
as a good first draft. It is useful for search and for telling senses apart,
but it is not a checked dictionary. Every row says who wrote it
(`"source": "mt:claude-sonnet-5"`), so reviewed or human-made glosses can
replace it row by row later.

## Files

```
data/
  words.jsonl    one JMdict entry per line
  kanji.jsonl    one kanji per line
  words.tsv      the same words, one sense per row
  kanji.tsv      the same kanji, one per row
  stats.json     counts and the JMdict version used
method/
  TASK.md        the full brief the translator worked from
scripts/
  build.py       rebuilds data/ from the translation run
  yomitan.py     packages data/ as a Yomitan dictionary
```

### `words.jsonl`

```json
{"id": 1153930,
 "kanji": [{"text": "安全", "pri": ["ichi1", "news1", "nf01"]}],
 "kana":  [{"text": "あんぜん", "pri": ["ichi1", "news1", "nf01"]},
           {"text": "あんせん", "info": ["ok"]}],
 "nf": 1,
 "senses": [{"i": 0, "pos": ["n", "adj-na"],
             "en": ["safety", "security"],
             "bg": ["безопасност", "сигурност"]}],
 "source": "mt:claude-sonnet-5"}
```

- `id` is the JMdict entry number (`ent_seq`). `i` is the sense's position in the entry,
  counting every `<sense>` from 0. Together they point at one JMdict sense.
  Sense numbers can shift between JMdict releases. These match the JMdict of
  **2026-09-22**, and `en` holds the English each Bulgarian sense was
  translated from, so the rows can be re-aligned to a newer JMdict.
- `kanji` and `kana` are JMdict's spellings with its own codes: `info`
  (`ke_inf`/`re_inf`, e.g. `ateji`, `rK`, `sK`), `pri` (priority tags),
  `only` (`re_restr`: the reading belongs only to these spellings) and
  `nokanji`.
- `nf` is the entry's best JMdict frequency bucket (1 = the 500 commonest
  words), or `null` if it has none.
- `pos` and `misc` are JMdict's part-of-speech and usage codes, unchanged.
- `bg` holds one to eight Bulgarian glosses, most usual first.

### `kanji.jsonl`

```json
{"char": "日", "on": ["にち", "じつ"], "kun": ["ひ", "-び", "-か"],
 "en": ["Day", "Sun", "Japan", "Counter For Days"],
 "bg": ["ден", "слънце", "Япония", "брояч за дни"],
 "source": "mt:claude-sonnet-5"}
```

`on`, `kun` and `en` are KANJIDIC's (database version 2026-265). `bg` is not
a word-for-word translation of `en`: it gives the one to five core meanings, and
drops KANJIDIC noise such as units and rare senses.

### TSV

Tab-separated, UTF-8, with a header row. Glosses inside a cell are joined with
` | ` (glosses can contain `;` and `,`, so those are not used as separators).

```
jmdict_id  sense  headword  reading   pos       en                  bg
1153930    0      安全      あんぜん   n,adj-na  safety | security   безопасност | сигурност
```

## Yomitan

Download `jmdict-kanjidic-bg-yomitan.zip` from [Releases](../../releases) and
import it in Yomitan's settings (*Dictionaries → Import*). It holds the
Bulgarian words (one row per sense, grouped by JMdict entry), the kanji, and
Bulgarian names for JMdict's tags. You may want to keep an English JMdict dictionary alongside it
for words this one does not cover yet. The zip passes Yomitan's own dictionary
schemas. To build it yourself, run `python scripts/yomitan.py`.

## How it was made

- **Input.** For each JMdict entry, the translator saw the spellings, the
  reading, and every sense's English glosses, part of speech and usage notes.
  For each kanji, it saw KANJIDIC's meanings and readings, a curated meaning
  from Kanji alive where there is one, and up to five common words that use
  the kanji. Entries also came with **hints**: Bulgarian words that human-made
  sources pair with the Japanese word through English (English Wiktionary's
  translation tables, and the Bulgarian and Japanese wordnets through shared
  synset ids). The hints often belong to another sense, so they were
  suggestions, not answers.
- **Translation.** Claude Sonnet 5 translated 100 entries at a time, following
  [`method/TASK.md`](method/TASK.md), in September 2026. The main rules:
  - one Bulgarian sense per English sense, never merged or split
  - dictionary citation forms (singular indefinite nouns; verbs in the first
    person singular present, with the aspect pair `отварям, отворя`)
  - transitivity kept apart (開く *vi* → `отварям се`, 開ける *vt* → `отварям`)
  - established Bulgarian forms for names (`Токио`, `Фуджи`), otherwise
    Bulgarian transcription
  - a trailing `?` on any gloss the translator was not confident about
- **Checking.** Each chunk had to pass an automatic check before it was
  accepted. The check covers: every entry and sense present exactly once, no
  empty or overlong glosses, no English left in, and the text really
  Bulgarian. `scripts/build.py` repeats the alignment check when it builds
  `data/`. No human has reviewed the meanings yet.

The source code and the translation run live in
[Better-Kanji-Dictionary](https://github.com/CreeperBeatz/Better-Kanji-Dictionary)
(`pipeline/translate/`).

## Coverage and known weaknesses

- **Common words only, so far.** These are JMdict's 30,200 commonest entries
  (every entry with a priority tag, ordered by frequency), out of about
  219,000. That covers most of the words in everyday text, including about 96%
  of the word tokens in Tatoeba's Japanese sentences. The rest of JMdict is not
  translated yet.
- **English as a go-between.** The Bulgarian was translated from the English
  glosses, so wherever the English is ambiguous, the Bulgarian can pick the wrong sense.
  The headword, part of speech and hints were given to prevent this, but they
  cannot catch every case.
- **`?` marks the unsure glosses.** The 1,595 unsure glosses are mostly specialised terms: go
  and shogi, baseball, card games, historical offices and Japan-only foods.
  Some are plainly wrong. For example, 筋's "ninth vertical line" is a shogi
  term but came out as `(в го)?`. These are the best place to start a review.
- **Sense restrictions are not in the Yomitan version.** JMdict can limit a
  sense to some spellings (`stagk`/`stagr`). Those limits are not in
  this data, so Yomitan shows all of a word's senses under each of its
  spellings.

Corrections are very welcome. Please open an issue, or a pull request that
changes a row in `data/words.jsonl` or `data/kanji.jsonl` and sets its `source`
to say who corrected it.

## Rebuilding

```
python scripts/build.py --source ../BetterRTK   # data/ from the translation run
python scripts/yomitan.py                       # dist/jmdict-kanjidic-bg-yomitan.zip
```

`build.py` needs a Better-Kanji-Dictionary checkout with `pipeline/translate/in/`
(from `make_chunks.py`), `pipeline/translate/out/`, and
`pipeline/data/JMdict_e.gz`.

## Licence and attribution

This data is released under **[CC BY-SA 4.0](LICENSE)**.

It is a translation of the **[JMdict](https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project)**
and **[KANJIDIC](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project)**
dictionary files. They are the property of the
[Electronic Dictionary Research and Development Group](https://www.edrdg.org/),
and are used in conformance with the Group's
[licence](https://www.edrdg.org/edrdg/licence.html) (CC BY-SA 4.0). The
English glosses, readings, spellings and codes in this dataset are theirs.

The translator was also shown these sources as context:
- [Kanji alive](https://kanjialive.com) meanings, CC BY 4.0
- translation tables from [English Wiktionary](https://en.wiktionary.org) (via
  [kaikki.org](https://kaikki.org)), CC BY-SA 4.0
- the [BulTreeBank Bulgarian WordNet](https://github.com/omwn/omw-data),
  CC BY 3.0
- the [Japanese WordNet](https://bond-lab.github.io/wnja/) (NICT)

If you use this data, please credit the EDRDG and link back here, for
example:

> Bulgarian glosses from jmdict-kanjidic-bg
> (https://github.com/CreeperBeatz/jmdict-kanjidic-bg), a machine translation
> of JMdict and KANJIDIC (EDRDG), CC BY-SA 4.0.
