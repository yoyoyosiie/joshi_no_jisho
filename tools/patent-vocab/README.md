# Patent vocab extractor

Pulls technical terms (with readings) out of Japanese patents for the dictionary.

## Setup
    pip install -r requirements.txt
    # for PDFs: poppler, and Tesseract with the Japanese model for scanned ones
    sudo apt install poppler-utils tesseract-ocr tesseract-ocr-jpn   # macOS: brew install poppler tesseract tesseract-lang

## Use
Run these from this folder (`cd tools/patent-vocab`).

    python run.py JP2019123456A JP2020012345A -o vocab.csv   # fetch from Google Patents
    python run.py --html saved/*.html -o vocab.csv           # pages you saved from patents.google.com
    python run.py --pdf pdfs/*.pdf -o vocab.csv              # JPO gazette or WIPO (WO) PDFs
    python run.py ... --no-english --min-freq 1              # options

Output `vocab.csv` (opens in Excel): term, reading, freq, n_patents, sources,
example_ja, english (blank, for you), en_source. `vocab.english.json` holds the
title and claim 1 of each patent's English family member (US > EP > WO) to
translate against.

## Into the dictionary
    python tools/import.py tools/patent-vocab/vocab.csv --jmdict JMdict_e.gz   # from the repo root

Every row becomes a draft term; see `data/README.md` for reviewing them.

## How it works
- `pdf.py`: patent PDF -> same sections. Uses the text layer if there is one, otherwise OCRs each page with Tesseract `jpn` at 2x native width (about 1 s/page on 4 cores; cached in `~/.cache/patent-vocab`). Skips drawing sheets and the search report. On a WIPO front page it OCRs the printed English title + abstract into `vocab.english.json`.
- `fetch.py`: Google Patents page -> title / abstract / claims / description / family. Checks robots.txt, waits 5 s between requests.
- `extract.py`: Sudachi (mode C) tokenizes; consecutive nouns are joined (減速 + 機構 -> 減速機構); boilerplate (前記, 本発明, 請求項...) and verb-use サ変 nouns (低減する) are dropped. Score = freq x patents seen in, with a bonus for compounds over 3 chars.

## Known limits
- English column is not filled automatically. JP and EN family texts are not sentence-parallel, so term-level alignment needs a statistical aligner or an LLM pass. Claim 1 pairs are the best context.
- J-PlatPat is not used: it is a JS app and its terms discourage automated bulk access. For bulk JP data, JPO's 特許情報取得API (registration required) is the official route.
- OCR is not perfect. Expect a few misread terms (e.g. ワソーク for ワーク) at low frequency; check the example_ja column before trusting a rare term.
- Sudachi sometimes gives the wrong reading (経時 -> きょうじ, should be けいじ). Check readings of kanji compounds.
- `tests/sample.html` is a hand-written fixture, not a real patent.
