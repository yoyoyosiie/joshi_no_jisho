"""Build a vocab list from Japanese patents.

  python run.py JP2019123456A JP2020012345A -o vocab.csv     # fetch from Google Patents
  python run.py --html saved/*.html -o vocab.csv             # use pages you saved yourself
  python run.py --pdf pdfs/*.pdf -o vocab.csv                # patent PDFs (scans are OCR'd)

For each JP patent it also fetches one English family member (US/EP/WO) and
stores the matching claim 1 text, so each term has an English passage to
translate against.
"""
import argparse
import csv
import json
import pathlib

import extract
import fetch
import pdf


# english/en_by are filled by gloss.py; flags are explained in extract.FLAGS.
COLUMNS = ["term", "reading", "freq", "n_patents", "sources", "example_ja", "english", "en_by", "en_source", "flags"]


def claim1(p):
    return p.claims[0] if p.claims else p.abstract


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("numbers", nargs="*", help="JP publication numbers, e.g. JP2019123456A")
    ap.add_argument("--html", nargs="*", default=[], help="saved Google Patents HTML pages")
    ap.add_argument("--pdf", nargs="*", default=[], help="patent PDFs (JPO gazette or WIPO pamphlet)")
    ap.add_argument("--no-english", action="store_true", help="skip fetching English family members")
    ap.add_argument("--min-freq", type=int, default=2)
    ap.add_argument("-o", "--out", default="vocab.csv")
    a = ap.parse_args()

    patents = [fetch.fetch(n) for n in a.numbers]
    patents += [fetch.parse(pathlib.Path(f).read_text(encoding="utf-8"), pathlib.Path(f).stem)
                for f in a.html]

    english = {}
    for f in a.pdf:
        p, en = pdf.parse_pdf(f)
        print(f"{f}: {p.number}, {len(p.claims)} claims, {len(p.description)} chars of description")
        patents.append(p)
        if en:  # WIPO front pages print an English title/abstract: no family lookup needed
            english[p.number] = {"number": p.number + " (front page, OCR)", "title": en.get("title", ""),
                                 "abstract": en.get("abstract", "")}

    for p in patents:
        if p.number in english:
            continue
        en = None if a.no_english else fetch.english_member(p)
        if en:
            try:
                ep = fetch.fetch(en, "en")
                english[p.number] = {"number": en, "title": ep.title, "claim1": claim1(ep)}
            except Exception as e:  # one missing member should not kill the run
                print(f"skip English {en}: {e}")

    docs = [(p.number, "。".join([p.title, p.abstract, *p.claims, p.description])) for p in patents]
    ocr = {p.number for p in patents if getattr(p, "ocr", False)}
    terms = [t for t in extract.extract(docs, ocr) if t["freq"] >= a.min_freq]

    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel reads UTF-8
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for t in terms:
            en = english.get(t["sources"][0], {})
            w.writerow([t["term"], t["reading"], t["freq"], len(t["sources"]), " ".join(t["sources"]),
                        t["example"], "", "", en.get("number", ""), " ".join(t["flags"])])
    pathlib.Path(a.out).with_suffix(".english.json").write_text(
        json.dumps(english, ensure_ascii=False, indent=2), encoding="utf-8")
    flagged = sum(1 for t in terms if t["flags"])
    print(f"{len(terms)} terms from {len(patents)} patents -> {a.out} ({flagged} flagged for a check)")
    print(f"Next: python gloss.py {a.out}   # fill the english column")


if __name__ == "__main__":
    main()
