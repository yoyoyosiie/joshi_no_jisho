"""Turn a vocab CSV into draft term + sentence YAML files under data/.

    python tools/import.py vocab.csv                         # glosses left blank
    python tools/import.py vocab.csv --jmdict JMdict_e.gz    # pre-fill glosses from JMdict
    python tools/import.py vocab.csv --dry-run               # show what would happen

CSV columns (the patent extractor's output, as-is):
    term, reading, freq, n_patents, sources, example_ja, english, en_by, en_source, flags
plus optional: tags (`;`-separated tag ids), def_en, pos.
`english` may hold `;`-separated glosses; when filled it wins over JMdict.
`en_by` says who wrote them (human, machine); blank means human.
`flags` (ocr?, reading?, ...) are printed so you can check those rows; they are not imported.
Rows flagged `not-a-term?` (gloss.py found no meaning: OCR junk) are skipped.

Rules:
- Every new term is `status: draft`; nothing goes live until a human reviews it.
- A row whose (term, reading) already exists is skipped, so re-running is safe.
- `example_ja` becomes a sentence (en: null) linked to the term. Identical
  sentences are shared: the second term is added to the existing file.
"""
import argparse
import csv
import datetime
import re

from common import KANJI, SENTENCES, TERMS, TAGS, kata_to_hira, load_yaml, next_id, records, write_yaml
import furigana
import jmdict

EN_BY = {"human", "machine"}
POS = {"noun", "suru-noun", "verb", "i-adj", "na-adj", "adverb", "expression", "prefix", "suffix", "counter", "other"}
PATENT_NO = re.compile(r"^(WO|JP|US|EP|CN|KR)\s?[\d/\-]+")


def split(cell, sep=";"):
    return [x.strip() for x in (cell or "").split(sep) if x.strip()]


def make_senses(row, jm_index):
    """One sense from the CSV if it has English; else JMdict's senses; else one empty sense."""
    tags, pos = split(row.get("tags")), (row.get("pos") or "").strip() or None
    def_en = (row.get("def_en") or "").strip() or None
    english = split(row.get("english"))
    if english:
        return [{"pos": pos or "noun", "en": english, "en_by": (row.get("en_by") or "").strip() or "human", "def_en": def_en, "def_ja": None, "tags": tags}]
    found = jmdict.lookup(jm_index, row["term"], row["reading"]) if jm_index else []
    if found:
        return [{"pos": pos or jmdict.map_pos(s["pos"]), "en": s["gloss"], "en_by": "jmdict",
                 "def_en": def_en if i == 0 else None, "def_ja": None, "tags": tags} for i, s in enumerate(found)]
    return [{"pos": pos or "noun", "en": [], "en_by": None, "def_en": def_en, "def_ja": None, "tags": tags}]


def sentence_source(sources):
    ref = sources[0] if sources else None
    kind = "patent" if ref and PATENT_NO.match(ref) else "other"
    return {"type": kind, "ref": ref, "url": None, "license": None}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--jmdict", help="path to JMdict_e.gz (or .xml) to pre-fill English glosses")
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help="value for `added` (default: today)")
    ap.add_argument("--dry-run", action="store_true", help="print a summary, write nothing")
    a = ap.parse_args()

    known_tags = {t["id"] for t in load_yaml(TAGS)}
    jm_index = jmdict.load(a.jmdict) if a.jmdict else None

    existing = {(t["ja"], kata_to_hira(t["reading"])) for _, t in records(TERMS)}
    sentences = {s["ja"]: (p, s) for p, s in records(SENTENCES)}  # reuse identical sentences
    t_next, s_next = next_id(TERMS, "t"), next_id(SENTENCES, "s")
    new_terms, touched, skipped, junk, problems, flagged = [], {}, 0, 0, [], []

    for path in a.csv:
        # utf-8-sig: the extractor writes a BOM so Excel opens it correctly; strip it here.
        with open(path, newline="", encoding="utf-8-sig") as f:
            for n, row in enumerate(csv.DictReader(f), start=2):  # line 1 is the header
                ja, reading = row["term"].strip(), row["reading"].strip()
                row["term"], row["reading"] = ja, reading
                where = f"{path}:{n} {ja}"
                if KANJI.search(reading) or not reading:
                    problems.append(f"{where}: reading {reading!r} is not kana; fix it in the CSV and re-run")
                    continue
                bad = [t for t in split(row.get("tags")) if t not in known_tags]
                if bad or (row.get("pos") and row["pos"].strip() not in POS):
                    problems.append(f"{where}: unknown tag(s) {bad} or pos {row.get('pos')!r}")
                    continue
                if (row.get("en_by") or "").strip() not in EN_BY | {""}:
                    problems.append(f"{where}: en_by {row['en_by']!r} should be human or machine")
                    continue
                if "not-a-term?" in (row.get("flags") or "").split():
                    junk += 1
                    continue
                if (ja, kata_to_hira(reading)) in existing:
                    skipped += 1
                    continue
                existing.add((ja, kata_to_hira(reading)))

                tid = f"t{t_next:06d}"
                t_next += 1
                srcs = row.get("sources", "").split()
                term = {
                    "id": tid, "ja": ja, "alt": [], "reading": reading,
                    "furigana": furigana.furigana(ja, reading),
                    "pitch": {"value": None, "source": None, "verified": False},
                    "senses": make_senses(row, jm_index),
                    "card_sentence": None, "images": [], "sources": srcs,
                    "added": a.date, "status": "draft",
                }
                new_terms.append(term)
                if (row.get("flags") or "").strip():
                    flagged.append(f"{where}: {row['flags'].strip()}")

                ex = (row.get("example_ja") or "").strip()
                if not ex:
                    continue
                if ja not in ex:
                    problems.append(f"{where}: example sentence doesn't contain the term; not linked")
                    continue
                if ex in sentences:
                    spath, s = sentences[ex]
                    if tid not in [link["id"] for link in s["terms"]]:
                        s["terms"].append({"id": tid, "surface": ja})
                else:
                    sid = f"s{s_next:06d}"
                    s_next += 1
                    spath = SENTENCES / f"{sid}.yaml"
                    s = {"id": sid, "ja": ex, "en": None,
                         "terms": [{"id": tid, "surface": ja}],
                         "source": sentence_source(srcs), "en_by": None, "added": a.date}
                    sentences[ex] = (spath, s)
                touched[spath] = s

    for p in problems:
        print("!", p)
    for f in flagged:
        print("?", f)
    glossed = sum(1 for t in new_terms if t["senses"][0]["en"])
    with_fg = sum(1 for t in new_terms if t["furigana"])
    print(f"{len(new_terms)} new terms ({glossed} with glosses, {with_fg} with furigana), "
          f"{len(touched)} sentence files new/updated, {skipped} duplicates and {junk} not-a-term rows skipped, {len(problems)} rows need attention, "
          f"{len(flagged)} imported rows flagged for a check.")
    if a.dry_run:
        return
    for t in new_terms:
        write_yaml(TERMS / f"{t['id']}.yaml", t)
    for spath, s in touched.items():
        write_yaml(spath, s)
    print("Now run: python tools/validate.py")


if __name__ == "__main__":
    main()
