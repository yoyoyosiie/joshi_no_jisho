# Handoff: ジョシの辞書 (joshi_no_jisho)

A Japanese–English dictionary of technical / engineering / STEM terms, built for
studying from and exporting to Anki. This file is the brief for the session that
builds it. Decisions marked **decided** were made with josie (repo owner, ME
senior, ~JLPT N3) on 2026-10-27; don't reopen them without asking. Items marked
**your call** are left to you.

Full planning doc (same content, more discussion):
https://claude.ai/artifact/5YLZm7BkHGsTfXdXJjphsc

## 1. Decisions

| Topic | Decision |
| --- | --- |
| Platform | **decided**: static site on GitHub Pages, all search client-side. No server, no DB, no user accounts. |
| Source of truth | **decided**: the repo. YAML files under `data/`, validated in CI. |
| Contributions | **decided**: GitHub PRs (later: an issue form a bot turns into a draft PR). Accounts / in-app review queue deferred, probably forever. |
| UI language | **decided**: reader picks EN or JA UI; choice remembered in the browser. Search accepts either language regardless of UI. |
| Audience | **decided**: personal study tool first, public repo from day one, should hold up if others use it. Non-commercial. |
| License | **decided**: data CC BY-SA 4.0, code MIT. (Forced anyway by JMdict / Kanjium / KanjiVG ShareAlike.) |
| Tags | **decided**: hierarchical, controlled list (`data/tags.yaml`, each tag has an optional `parent`). Filtering on a parent includes its children. |
| Machine translation | **decided**: allowed for sentences if flagged (`en_by: machine`, shown as a badge). |
| Anki | **decided**: JA→EN sentence cards first; EN→JA later as an option. Spec in section 6. |
| Site stack | **decided** (Phase 0 build, 2026-10-27): A, Astro + Python data tools. See section 3. |

josie has little web experience but wants to learn. Keep the code readable,
comment the non-obvious parts, and put setup steps in the README.

## 2. Repo layout (target)

```
data/
  terms/t000123.yaml        one file per term
  sentences/s000045.yaml    one file per sentence
  tags.yaml                 controlled, hierarchical tag list (ja + en names)
  lists/*.yaml              curated lists (e.g. "CNC basics")
  i18n/en.yaml, i18n/ja.yaml  UI strings
schema/*.json               JSON Schema for each record type
tools/
  patent-vocab/             existing extractor (move from repo root)
  validate.py               schema + referential checks, run in CI
  import.py                 CSV -> draft term + sentence YAML
  build.py                  resolve links, derive fields, write site data
site/                       front end (stack per section 3)
docs/handoff.md             this file
LICENSE (MIT), LICENSE-DATA (CC BY-SA 4.0), ATTRIBUTION.md
```

Pipeline: `data/` → `validate.py` (CI fails on bad data) → `build.py` (romaji,
furigana, back-links, search keys → JSON) → front end → GitHub Actions deploys
to Pages on merge to the default branch.

Python for the tools matches `patent-vocab` and reuses its Sudachi reading code.

## 3. Site stack: your call

Data tooling stays in Python either way. The choice is how pages are made.

| Option | What it is | Pros | Cons |
| --- | --- | --- | --- |
| **A. Astro + Python data tools** (recommended) | Static-site framework. Pages are HTML-like `.astro` components; reads the JSON that `build.py` writes; built-in i18n routing. | One page per term for free, JA/EN routing, components for the term page / card preview, room for the interactive parts (lists, export, toggle) without spaghetti. Big docs + community. | josie must learn Node/npm and some JS/TS. Two languages in the repo. |
| **B. Plain HTML from Python** | `build.py` renders Jinja2 templates to static HTML; a small vanilla JS file does search, lists, export. | Fewest moving parts, one language for the build. Fast to start. | Lists, Anki export, and the UI toggle become hand-written JS that gets messy as features grow. |

Recommendation is A because josie asked for robustness if it grows, and the
interactive features are exactly where B degrades. If you pick B, keep the JS
in small modules from the start. Either way: no heavy client framework is
needed, and the build must work with a plain `npm run build` / `python
tools/build.py` on a fresh clone.

## 4. Data model

IDs are stable and never the kanji (one spelling can have two readings).
A term has **senses** because technical words split by field (ピッチ = thread
pitch / blade pitch / musical pitch).

```yaml
# data/terms/t000123.yaml
id: t000123
ja: 加工振動
alt: []                     # other spellings
reading: かこうしんどう       # romaji is derived at build, never stored
furigana: [[加工, かこう], [振動, しんどう]]   # optional; auto-filled, hand-fixable
pitch: {value: null, source: null, verified: false}
senses:
  - pos: noun               # shown on the Anki card
    en: [machining vibration, chatter]
    def_en: Vibration of the tool or workpiece during cutting.
    def_ja: null            # optional; most will be blank for a while
    tags: [machining, vibration]
card_sentence: null         # optional sentence id to put on the Anki card
images: []                  # {file, credit, license}
sources: [WO2021/079959]    # where the term was found
added: 2026-10-27           # set by import.py
status: draft               # draft | reviewed
```

```yaml
# data/sentences/s000045.yaml
id: s000045
ja: 加工振動の判定では、空転時の振動を許容値として設定している。
en: To judge machining vibration, the vibration during idle rotation is set as the allowable value.
terms:                      # the ONLY place the term<->sentence link is stored
  - {id: t000123, surface: 加工振動}
  - {id: t000088, surface: 振動}
source: {type: patent, ref: WO2021/079959, url: null, license: null}
en_by: human                # human | machine | source
added: 2026-10-27
```

Rules:
- Sentences are shared many-to-many. Term pages get their sentence list computed
  at build. `surface` is the form as it appears (handles 振動して etc.) for
  highlighting.
- Sentence order for a term: by `added`, then `id`. First = the Anki card
  sentence unless `card_sentence` is set.
- `build.py` warns when a known term appears in a sentence but isn't linked.
- Only `status: reviewed` terms show on the site by default (toggle to show drafts).
- `tags.yaml`: `{id, ja, en, parent}`. Validation rejects unknown tags.

## 5. Search, import, lists

**Search** (one box, all client-side; a few thousand terms is small):
- Kanji: substring on `ja` + `alt` (振動 finds 加工振動).
- Kana: fold katakana → hiragana.
- Romaji: convert input to kana with WanaKana (MIT); `kakou`, `kakō`, `kakoo` all hit かこう.
- English: word-prefix on glosses, then definitions.
- Tag filter: hierarchical checkbox tree.

**Import**: `tools/import.py` reads CSV (the patent extractor's output as-is:
`term, reading, freq, n_patents, sources, example_ja, english, en_source`, plus
optional `tags` (`;`-separated), `def_en`, `pos`). Creates `draft` terms,
skips duplicates by (`ja`, `reading`), turns `example_ja` into a sentence with
`en: null` linked to that term. Pre-fill English glosses from JMdict where a
match exists (mark as unreviewed). Multi-sense and extra links are edited in
YAML afterward. Note the patent CSV has a UTF-8 BOM.

**Lists**: playlist model. "Add to list" button on each term, checkboxes on
search results for bulk add. Personal lists in localStorage (wrap in try/catch)
with import/export as a file; curated lists as YAML in `data/lists/`.

## 6. Anki export

Match josie's existing deck. Reference screenshots:
`docs/anki-card-reference-front.png`, `docs/anki-card-reference-back.png`.
Dark theme, centered, one accent color (salmon/red in the screenshots) for the
target term.

| Side | Top to bottom |
| --- | --- |
| Front | Term, large, no furigana. Sentence, no furigana, target term bold in accent color. |
| Back | Term, large, with furigana. Reading in kana. English gloss. Divider. Sentence with furigana; target term and its reading in accent color. English translation. Side block: part of speech, top-level tag. Small footer: sentence source + `en_by`. |

Fields: `Term, TermFurigana, Reading, Gloss, Sentence, SentenceFurigana,
SentenceEN, POS, Tag, Source`. Use Anki's furigana syntax
(`写真集[しゃしんしゅう]`) with the `{{furigana:...}}` / `{{kanji:...}}`
filters so one field serves both sides.

- **Phase 1**: CSV export with Anki header lines (`#separator`, `#notetype`,
  `#deck`, `#guid column`) plus a documented note type josie creates once.
- **Phase 2**: `.apkg` with the note type and CSS bundled (genanki in Python,
  or a browser-side equivalent).
- **Must**: GUID = term id, so re-importing updates cards instead of
  duplicating them and wiping review history.

## 7. Data sources and licensing

| Need | Source | License | Notes |
| --- | --- | --- | --- |
| Stroke order | [KanjiVG](https://github.com/KanjiVG/kanjivg) | CC BY-SA 3.0 (checked) | Per kanji, animated SVG. |
| Pitch accent | [Kanjium](https://github.com/mifunetoshiro/kanjium) `accents.txt` | CC BY-SA 4.0 (checked) | Common words only; compound technical terms mostly missing. Leave blank or hand-enter with `verified: false`. |
| Furigana split | [JmdictFurigana](https://github.com/Doublevil/JmdictFurigana) | Same as JMdict (checked) | Fall back to Sudachi. |
| Seed glosses | [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) | CC BY-SA 4.0 (from memory, verify) | Field tags {engr} {mech} {comp}. |
| Sentences | Tatoeba | Text CC BY 2.0 FR (from memory, verify) | Little technical text. |
| Sentences | Patents via `tools/patent-vocab` | Reuse terms not verified | JA only; EN family text is not sentence-parallel, so translate (MT allowed, flagged). |
| Audio | Browser Web Speech API | n/a | Phase 3. No recorded audio source exists for technical terms. |

Do not use or scrape: OJAD (no open license found; personal reference only),
NHK / Shinmeikai accent dictionaries, Forvo, commercial dictionary definitions,
JIS standard text. Credit every source in `ATTRIBUTION.md` and on the site.

## 8. Phases

**Phase 0: foundation**
- [x] Layout above; move `patent-vocab/` to `tools/`; licenses; README with setup.
- [x] JSON Schemas, `validate.py`, CI on every PR.
- [x] `import.py`; `tags.yaml` v1 (mechanical engineering / machining tree first).
- [x] Import `WO2021-079959_vocab.csv` (175 rows) as drafts to prove the path.

**Phase 2**: `.apkg` with the note type and CSS bundled (genanki in Python,
  or a browser-side equivalent).
- **Must**: GUID = term id, so re-importing updates cards instead of
  duplicating them and wiping review history.

## 7. Data sources and licensing

| Need | Source | License | Notes |
| --- | --- | --- | --- |
| Stroke order | [KanjiVG](https://github.com/KanjiVG/kanjivg) | CC BY-SA 3.0 (checked) | Per kanji, animated SVG. |
| Pitch accent | [Kanjium](https://github.com/mifunetoshiro/kanjium) `accents.txt` | CC BY-SA 4.0 (checked) | Common words only; compound technical terms mostly missing. Leave blank or hand-enter with `verified: false`. |
| Furigana split | [JmdictFurigana](https://github.com/Doublevil/JmdictFurigana) | Same as JMdict (checked) | Fall back to Sudachi. |
| Seed glosses | [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) | CC BY-SA 4.0 (from memory, verify) | Field tags {engr} {mech} {comp}. |
| Sentences | Tatoeba | Text CC BY 2.0 FR (from memory, verify) | Little technical text. |
| Sentences | Patents via `tools/patent-vocab` | Reuse terms not verified | JA only; EN family text is not sentence-parallel, so translate (MT allowed, flagged). |
| Audio | Browser Web Speech API | n/a | Phase 3. No recorded audio source exists for technical terms. |

Do not use or scrape: OJAD (no open license found; personal reference only),
NHK / Shinmeikai accent dictionaries, Forvo, commercial dictionary definitions,
JIS standard text. Credit every source in `ATTRIBUTION.md` and on the site.

## 8. Phases

**Phase 0: foundation**
- [x] Layout above; move `patent-vocab/` to `tools/`; licenses; README with setup.
- [x] JSON Schemas, `validate.py`, CI on every PR.
- [x] `import.py`; `tags.yaml` v1 (mechanical engineering / machining tree first).
- [x] Import `WO2021-079959_vocab.csv` (175 rows) as drafts to prove the path.

**Phase 1: MVP** (done = josie can study ~100 reviewed terms from it)
- [x] Term page: headword + furigana, reading, senses, tags, linked sentences with highlighted terms, sources.
- [x] One search box (kanji / kana / romaji / English) + tag tree filter.
- [x] EN/JA UI toggle.
- [x] Lists + Anki CSV export per section 6.
- [ ] Deployed to GitHub Pages.

**Phase 2**: Kanjium pitch accent + pitch graph; KanjiVG stroke order; images
with credit/license; `.apkg` export; curated lists.

**Phase 3**: TTS play button; offline PWA; "suggest a term" issue form → draft PR.

## 9. Known pitfalls

- Patent CSV is raw candidates: OCR misreads (ワソーク for ワーク) and wrong
  Sudachi readings (経時 → きょうじ, should be けいじ). Everything imports as draft.
- Japanese definitions are the most expensive field; keep optional.
- Don't commit large images; prefer SVG or compressed WebP.
- The cloud sandbox blocks patent sites and edrdg.org; josie supplies patent PDFs (see
  `tools/patent-vocab/README.md`).
