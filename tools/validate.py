"""Check everything under data/. CI runs this on every PR; a bad file fails the build.

    python tools/validate.py

Two layers of checks:
1. JSON Schema (schema/*.json): each file has the right fields and types.
2. Cross-file rules a schema can't express: links point at things that exist,
   tags are in tags.yaml, furigana matches the headword, and so on.
"""
import json
import sys

from jsonschema import Draft202012Validator

from common import DATA, I18N, LISTS, SCHEMA, SENTENCES, TAGS, TERMS, kata_to_hira, load_yaml


def schema(name):
    return Draft202012Validator(json.loads((SCHEMA / f"{name}.schema.json").read_text(encoding="utf-8")))


class Report:
    def __init__(self):
        self.errors = []

    def __call__(self, path, msg):
        self.errors.append(f"{path.relative_to(DATA.parent)}: {msg}")


def check_schema(err, validator, path, obj):
    ok = True
    for e in validator.iter_errors(obj):
        where = "/".join(str(p) for p in e.absolute_path) or "(top)"
        err(path, f"{where}: {e.message}")
        ok = False
    return ok


def load_folder(err, folder, validator):
    """Schema-check every file in a folder; return {id: (path, data)} for the valid ones."""
    out = {}
    for path in sorted(folder.glob("*.yaml")):
        try:
            obj = load_yaml(path)
        except Exception as e:  # YAML syntax error: report it and keep going
            err(path, f"cannot read YAML: {e}")
            continue
        if not check_schema(err, validator, path, obj):
            continue
        if obj["id"] != path.stem:
            err(path, f"id {obj['id']} does not match file name")
            continue
        out[obj["id"]] = (path, obj)
    return out


def check_tags(err):
    tags = load_yaml(TAGS)
    if not check_schema(err, schema("tags"), TAGS, tags):
        return set()
    ids = [t["id"] for t in tags]
    for dup in {i for i in ids if ids.count(i) > 1}:
        err(TAGS, f"tag {dup} defined twice")
    parent = {t["id"]: t.get("parent") for t in tags}
    for tid, p in parent.items():
        if p is not None and p not in parent:
            err(TAGS, f"tag {tid}: unknown parent {p}")
        seen = set()
        while p is not None and p in parent:  # walk up; coming back to a tag = loop
            if p in seen or p == tid:
                err(TAGS, f"tag {tid}: parent chain loops")
                break
            seen.add(p)
            p = parent[p]
    return set(parent)


def check_terms(err, terms, tags):
    by_key = {}
    for tid, (path, t) in terms.items():
        key = (t["ja"], kata_to_hira(t["reading"]))
        if key in by_key:
            err(path, f"same headword and reading as {by_key[key]}")
        by_key[key] = tid

        for i, s in enumerate(t["senses"]):
            for tag in s.get("tags", []):
                if tag not in tags:
                    err(path, f"senses/{i}: unknown tag {tag} (add it to data/tags.yaml first)")
            if t["status"] == "reviewed":
                if not s["en"]:
                    err(path, f"senses/{i}: a reviewed term needs English glosses")
                if not s.get("tags"):
                    err(path, f"senses/{i}: a reviewed term needs at least one tag")

        fg = t.get("furigana")
        if fg:
            if "".join(p[0] for p in fg) != t["ja"]:
                err(path, "furigana text does not spell the headword")
            joined = "".join(p[1] if len(p) == 2 else p[0] for p in fg)
            if kata_to_hira(joined).lower() != kata_to_hira(t["reading"]).lower():
                err(path, f"furigana reads {joined}, but reading is {t['reading']}")


def check_sentences(err, sentences, terms):
    linked = {}  # term id -> sentence ids, to check card_sentence below
    for sid, (path, s) in sentences.items():
        if (s["en"] is None) != (s["en_by"] is None):
            err(path, "en and en_by go together: set both or neither")
        ids = [link["id"] for link in s["terms"]]
        for link in s["terms"]:
            if link["id"] not in terms:
                err(path, f"links unknown term {link['id']}")
            if link["surface"] not in s["ja"]:
                err(path, f"surface {link['surface']} is not in the sentence")
            linked.setdefault(link["id"], set()).add(sid)
        for dup in {i for i in ids if ids.count(i) > 1}:
            err(path, f"term {dup} linked twice")

    for tid, (path, t) in terms.items():
        cs = t.get("card_sentence")
        if cs and cs not in linked.get(tid, ()):
            err(path, f"card_sentence {cs} does not exist or does not link this term")


def check_lists(err, lists, terms):
    for _, (path, lst) in lists.items():
        for tid in lst["terms"]:
            if tid not in terms:
                err(path, f"unknown term {tid}")


def check_i18n(err):
    v = schema("i18n")
    files = {p.stem: (p, load_yaml(p)) for p in sorted(I18N.glob("*.yaml"))}
    for p, obj in files.values():
        check_schema(err, v, p, obj)
    if "en" in files and "ja" in files:
        en, ja = set(files["en"][1]), set(files["ja"][1])
        for k in sorted(en - ja):
            err(files["ja"][0], f"missing key {k}")
        for k in sorted(ja - en):
            err(files["en"][0], f"missing key {k}")


def validate():
    err = Report()
    tags = check_tags(err)
    terms = load_folder(err, TERMS, schema("term"))
    sentences = load_folder(err, SENTENCES, schema("sentence"))
    lists = load_folder(err, LISTS, schema("list"))
    check_terms(err, terms, tags)
    check_sentences(err, sentences, terms)
    check_lists(err, lists, terms)
    check_i18n(err)
    return err.errors, len(terms), len(sentences)


def main():
    errors, n_terms, n_sentences = validate()
    for e in errors:
        print(e)
    if errors:
        print(f"\n{len(errors)} problem(s) found.")
        sys.exit(1)
    print(f"OK: {n_terms} terms, {n_sentences} sentences.")


if __name__ == "__main__":
    main()
