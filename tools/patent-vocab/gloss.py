"""Fill the blank `english` column of a vocab CSV with machining-aware glosses.

    python gloss.py vocab.csv                      # ask Claude (needs ANTHROPIC_API_KEY)
    python gloss.py vocab.csv --prompt-only        # print the prompts; paste them into Claude yourself
    python gloss.py vocab.csv --apply glosses.json # write glosses you already have ({"term": ["gloss", ...]})

Each batch of terms is sent with its Japanese example sentence and the English
title / abstract / claim 1 from vocab.english.json, so the model can use the
patent's own English wording (chatter frequency, not "trembling frequency").

Only empty `english` cells are filled; anything you typed is kept. Filled rows
get en_by=machine (or --by), and the importer carries that into the YAML so a
machine gloss is never mistaken for a reviewed one. A term the model says is
not real vocabulary gets the flag `not-a-term?`.
"""
import argparse
import csv
import json
import os
import pathlib
import re

import requests

from run import COLUMNS

API = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5-5"
BATCH = 40

PROMPT = """You are building a Japanese-English dictionary of mechanical engineering and machining terms.
For each Japanese term below, give 1-3 short English glosses, the way an English-speaking machinist
or engineer would say it. Prefer the wording the patent's own English text uses, when it has one.
Use standard engineering terms (びびり振動 -> "chatter", 被削材 -> "workpiece material"), not literal
word-by-word translations. If a term is not real vocabulary (OCR garbage, a fragment, a drawing label),
give an empty list.

English text of the patent(s), for context:
{context}

Terms (term / reading / example sentence):
{terms}

Answer with only a JSON object mapping each term to its list of glosses, e.g. {{"加工振動": ["machining vibration"]}}."""


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    cols = COLUMNS + [c for c in rows[0] if c not in COLUMNS] if rows else COLUMNS
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows({c: r.get(c, "") or "" for c in cols} for r in rows)


def context(english, rows):
    srcs = sorted({s for r in rows for s in r["sources"].split()})
    parts = []
    for s in srcs:
        e = english.get(s)
        if e:
            parts.append("\n".join(f"{k}: {v}" for k, v in e.items() if v))
    return "\n\n".join(parts) or "(none)"


def prompts(rows, english):
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        terms = "\n".join(f"{r['term']} / {r['reading']} / {r['example_ja']}" for r in batch)
        yield PROMPT.format(context=context(english, batch), terms=terms)


def ask(prompt, key, model):
    r = requests.post(API, timeout=300, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": model, "max_tokens": 4096, "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json()["content"])
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))


def apply(rows, glosses, by):
    n = 0
    for r in rows:
        if r.get("english", "").strip() or r["term"] not in glosses:
            continue
        en = [g.strip() for g in glosses[r["term"]] if g.strip()]
        if en:
            r["english"], r["en_by"] = "; ".join(en), by
            n += 1
        else:
            flags = set(r.get("flags", "").split()) | {"not-a-term?"}
            r["flags"] = " ".join(sorted(flags))
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--apply", help="JSON file of {term: [glosses]} to write instead of asking Claude")
    ap.add_argument("--prompt-only", action="store_true", help="print the prompts and stop")
    ap.add_argument("--by", default="machine", choices=["machine", "human"], help="value for en_by")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("-o", "--out", help="output CSV (default: overwrite the input)")
    a = ap.parse_args()

    rows = read_csv(a.csv)
    todo = [r for r in rows if not r.get("english", "").strip()]
    en_path = pathlib.Path(a.csv).with_suffix(".english.json")
    english = json.loads(en_path.read_text(encoding="utf-8")) if en_path.exists() else {}

    if a.apply:
        glosses = json.loads(pathlib.Path(a.apply).read_text(encoding="utf-8"))
    elif a.prompt_only:
        for p in prompts(todo, english):
            print(p, end="\n\n" + "=" * 40 + "\n\n")
        return
    else:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise SystemExit("Set ANTHROPIC_API_KEY, or use --prompt-only / --apply.")
        glosses = {}
        try:
            for i, p in enumerate(prompts(todo, english), 1):
                print(f"batch {i}...")
                glosses.update(ask(p, key, a.model))
        except Exception as e:  # keep the batches already paid for; a re-run only asks for blank rows
            print(f"batch {i} failed ({e}); saving what came back so far. Re-run to finish.")

    n = apply(rows, glosses, a.by)
    write_csv(a.out or a.csv, rows)
    print(f"{n} of {len(todo)} blank rows glossed (en_by={a.by}) -> {a.out or a.csv}")


if __name__ == "__main__":
    main()
