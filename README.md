# ジョシの辞書 (joshi_no_jisho)

A Japanese–English dictionary of technical / engineering / STEM terms, built
for studying and exporting to Anki. Plan and decisions: [docs/handoff.md](docs/handoff.md).

**Status: Phase 1 (MVP website).** 175 draft terms from one machining patent,
a searchable website with term pages, EN/JA interface, study lists and Anki export.
Live at https://yoyoyosiie.github.io/joshi_no_jisho/ once GitHub Pages is switched on
(see "Publishing" below).

## How it fits together

```
CSV of candidate terms ──tools/import.py──▶ data/ (YAML, one file per term/sentence)
                                               │
                                tools/validate.py (runs in CI on every PR)
                                               │
                          tools/build.py ──▶ site/ (Astro) ──▶ GitHub Pages
```

- `data/` is the dictionary itself. See [data/README.md](data/README.md) for how to review a draft term.
- `schema/` describes what a valid file looks like (JSON Schema).
- `tools/` holds the Python scripts, including the [patent vocab extractor](tools/patent-vocab/README.md).
- `site/` is the website (Astro). `tools/build.py` turns `data/` into one JSON file the site reads.
- `docs/anki.md` explains the Anki note type the export expects.

## Setup (once)

You need Python 3.10 or newer and git.

```bash
git clone https://github.com/yoyoyosiie/joshi_no_jisho.git
cd joshi_no_jisho
python -m venv .venv                 # a private Python just for this project
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r tools/requirements.txt
```

Run `source .venv/bin/activate` again each time you open a new terminal.

## Everyday commands

```bash
python tools/validate.py                         # check all data; prints OK or a list of problems
python -m unittest discover tools/tests          # test the tools themselves
python tools/import.py my_vocab.csv --dry-run    # preview an import
python tools/import.py my_vocab.csv --jmdict JMdict_e.gz   # import, with English glosses pre-filled
```

`JMdict_e.gz` is the free JMdict dictionary (English-only file), downloadable from
the [EDRDG JMdict page](https://www.edrdg.org/jmdict/j_jmdict.html). It is not
stored in the repo because it is large. Without it, imported terms have blank glosses.

## Running the website on your computer

You also need [Node.js](https://nodejs.org/) 24 (the "LTS" download).

```bash
cd site
npm install          # once, and whenever package.json changes
npm run dev          # builds the data, then serves the site at http://localhost:4321/joshi_no_jisho/
```

`npm run dev` reloads the page when you edit files in `site/src/`. After editing
`data/`, stop it (Ctrl+C) and run it again so `tools/build.py` picks up the change.
Other commands: `npm run build` (the real build, into `site/dist/`), `npm test`
(search tests), `npm run check` (TypeScript errors).

| File | What it is |
| --- | --- |
| `site/src/pages/[lang]/index.astro` | Search page (`[lang]` = `en` or `ja`, so each page exists twice) |
| `site/src/pages/[lang]/t/[id].astro` | One page per term |
| `site/src/pages/[lang]/lists.astro` | My lists + Anki download |
| `site/src/scripts/search.ts` | How the search box matches kanji / kana / romaji / English |
| `site/src/scripts/lists.ts`, `anki.ts` | Lists in the browser, Anki file format |
| `site/src/styles/global.css` | Colours and shared styles |
| `data/i18n/*.yaml` | Every piece of interface text, in both languages |

## Publishing

`.github/workflows/deploy.yml` rebuilds and publishes the site every time `main`
changes. It needs one switch, once: **Settings → Pages → Build and deployment →
Source: GitHub Actions**.

## Making a change

1. Make a branch: `git switch -c fix-reading-keiji` (a branch is your own copy to experiment on).
2. Edit files, then run `python tools/validate.py`.
3. `git add -A && git commit -m "Fix reading of 経時"` and `git push -u origin fix-reading-keiji`.
4. Open a pull request on GitHub. CI runs the validator; a green ✓ means the data is consistent.
5. Merge into `main`.

For small edits you can skip the terminal: open the file on GitHub, click the
pencil icon, and choose "Create a new branch and start a pull request".

## License

- Code: MIT ([LICENSE](LICENSE))
- Data (`data/`): CC BY-SA 4.0 ([LICENSE-DATA](LICENSE-DATA))
- Sources and credits: [ATTRIBUTION.md](ATTRIBUTION.md)
