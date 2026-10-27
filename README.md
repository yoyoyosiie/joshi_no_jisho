# ジョシの辞書 (joshi_no_jisho)

A Japanese–English dictionary of technical / engineering / STEM terms, built
for studying and exporting to Anki. Plan and decisions: [docs/handoff.md](docs/handoff.md).

**Status: Phase 0 (foundation).** The data format, checks and import are in
place, with 175 draft terms from one machining patent. There is no website yet:
that is Phase 1.

## How it fits together

```
CSV of candidate terms ──tools/import.py──▶ data/ (YAML, one file per term/sentence)
                                               │
                                tools/validate.py (runs in CI on every PR)
                                               │
                         Phase 1: tools/build.py ──▶ site/ (Astro) ──▶ GitHub Pages
```

- `data/` is the dictionary itself. See [data/README.md](data/README.md) for how to review a draft term.
- `schema/` describes what a valid file looks like (JSON Schema).
- `tools/` holds the Python scripts, including the [patent vocab extractor](tools/patent-vocab/README.md).

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

## Making a change

1. Make a branch: `git switch -c fix-reading-keiji` (a branch is your own copy to experiment on).
2. Edit files, then run `python tools/validate.py`.
3. `git add -A && git commit -m "Fix reading of 経時"` and `git push -u origin fix-reading-keiji`.
4. Open a pull request on GitHub. CI runs the validator; a green ✓ means the data is consistent.
5. Merge into `main`.

For small edits you can skip the terminal: open the file on GitHub, click the
pencil icon, and choose "Create a new branch and start a pull request".

## Site stack (decided for Phase 1)

**Astro**, reading JSON that `tools/build.py` writes. It gives one page per term,
JA/EN routes, and a clean place for the interactive parts (lists, Anki export).
Phase 1 will add Node.js to the setup steps (`npm install`, `npm run build`).

## License

- Code: MIT ([LICENSE](LICENSE))
- Data (`data/`): CC BY-SA 4.0 ([LICENSE-DATA](LICENSE-DATA))
- Sources and credits: [ATTRIBUTION.md](ATTRIBUTION.md)
