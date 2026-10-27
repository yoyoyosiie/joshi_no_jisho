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
example_ja, english, en_by, en_source, flags. `vocab.english.json` holds the
title and claim 1 of each patent's English family member (US > EP > WO) to
translate against.

`flags` marks rows to check by hand:
- `ocr?`: an unknown katakana word (ワソーク), or a rare term one character off a common one (スベクトラム vs スペクトラム).
- `reading?`: Sudachi didn't know a kanji part, so the reading is a guess.
- `reading-fixed`: the reading came from `READING_FIX` in extract.py (経時 → けいじ). Add to that table when you find another.
- `not-a-term?`: gloss.py found no meaning. The importer skips these rows.

## English glosses
    python gloss.py vocab.csv                        # needs ANTHROPIC_API_KEY
    python gloss.py vocab.csv --prompt-only          # no key: paste the prompts into Claude, save its JSON answers
    python gloss.py vocab.csv --apply glosses.json   # write those answers ({"term": ["gloss", ...]})

Fills only blank `english` cells, using the patent's English abstract/claim 1 as
context so glosses match machining usage. Filled rows get `en_by=machine`; the
importer keeps that label, so the site can tell machine glosses from reviewed ones.

## Into the dictionary
    python tools/import.py tools/patent-vocab/vocab.csv --jmdict JMdict_e.gz   # from the repo root

Every row becomes a draft term; see `data/README.md` for reviewing them.

## How it works
- `pdf.py`: patent PDF -> same sections. Uses the text layer if there is one, otherwise OCRs each page with Tesseract `jpn` at 2x native width (about 1 s/page on 4 cores; cached in `~/.cache/patent-vocab`). Skips drawing sheets and the search report. On a WIPO front page it OCRs the printed English title + abstract into `vocab.english.json`.
- `fetch.py`: Google Patents page -> title / abstract / claims / description / family. Checks robots.txt, waits 5 s between requests.
- `extract.py`: Sudachi (mode C) tokenizes; consecutive nouns are joined (減速 + 機構 -> 減速機構); boilerplate (前記, 本発明, 請求項...) and verb-use サ変 nouns (低減する) are dropped. Score = freq x patents seen in, with a bonus for compounds over 3 chars.

## Known limits
- Machine glosses are a first draft. They're good for compounds the English abstract names (空転周波数 → idling frequency) and weaker for generic words.
- J-PlatPat is not used: it is a JS app and its terms discourage automated bulk access. For bulk JP data, JPO's 特許情報取得API (registration required) is the official route.
- The flags catch most OCR junk, not all: 警告城 (for 警告域) and 総和基 (for 総和量) are real kanji, so only the gloss step notices them.
- Sudachi readings can be wrong without being flagged (X刃数 read as Xじんすう). Readings of rare kanji compounds still need a look.
- `tests/sample.html` is a hand-written fixture, not a real patent.
