"""Turn data/ into the one JSON file the website is built from.

    python tools/build.py            # writes site/src/data/dict.json

What it adds on top of the YAML:
- each term's sentence list (links are only stored on sentences; see data/README.md)
- furigana for every sentence, with the linked terms' own furigana taking priority
- where each linked term sits in its sentence, for highlighting
- every tag's ancestors, so filtering on a parent tag finds its children's terms
- the Anki fields for each term (docs/anki.md)
- the UI strings from data/i18n/

`npm run build` in site/ runs this first, so you rarely need to call it yourself.
It also counts terms that appear in a sentence without being linked
(`--verbose` lists them), so you can add the links in the sentence files.
"""
import json
import pathlib
import sys

from common import I18N, LISTS, ROOT, SENTENCES, TAGS, TERMS, KANJI, load_yaml, records
import furigana
from validate import validate

OUT = ROOT / "site" / "src" / "data" / "dict.json"


def tag_ancestors(tags):
    parent = {t["id"]: t.get("parent") for t in tags}
    out = {}
    for tid in parent:
        chain, p = [tid], parent[tid]
        while p:
            chain.append(p)
            p = parent.get(p)
        out[tid] = chain  # [self, parent, grandparent, ...]
    return out


def place_spans(ja, links):
    """Character span of each linked term in the sentence: {term id: [start, end]}.

    Longer surfaces are placed first, and a shorter one prefers an occurrence
    that isn't inside an already-placed term (so 振動 in 「加工振動の…振動を」
    highlights the second, standalone 振動).
    """
    spans = {}
    for link in sorted(links, key=lambda x: -len(x["surface"])):
        s, hits, i = link["surface"], [], ja.find(link["surface"])
        while i != -1:
            hits.append(i)
            i = ja.find(s, i + 1)
        if not hits:
            continue
        free = [h for h in hits if not any(a <= h < b or a < h + len(s) <= b for a, b in spans.values())]
        start = (free or hits)[0]
        spans[link["id"]] = [start, start + len(s)]
    return spans


def sentence_segments(ja, spans, terms):
    """Furigana pairs for a sentence, cut so no pair crosses a highlight edge.

    The sentence is split at every span edge and each piece read separately.
    A piece that is exactly a linked term uses that term's furigana, which a
    human may have corrected, instead of Sudachi's guess.
    """
    cuts = sorted({0, len(ja), *[x for se in spans.values() for x in se]})
    own = {ja[a:b]: terms[tid].get("furigana") for tid, (a, b) in spans.items() if tid in terms}
    segs = []
    for a, b in zip(cuts, cuts[1:]):
        piece = ja[a:b]
        segs += own.get(piece) or furigana.sentence(piece)
    return segs


def anki_ruby(pairs, bold=None):
    """Pairs -> Anki furigana syntax: 写真集[しゃしんしゅう]. `bold` = (start, end) to wrap in <b>.

    Anki reads the text before `[` back to the previous space as the base, so a
    space goes in front of every annotated part; the {{furigana:}} filter drops it.
    """
    out, pos = [], 0
    for p in pairs:
        text = p[0]
        if bold and pos == bold[0]:
            out.append("<b>")
        out.append(f" {text}[{p[1]}]" if len(p) == 2 else text)
        pos += len(text)
        if bold and pos == bold[1]:
            out.append("</b>")
    return "".join(out).strip()


def clean(s):
    # Anki's CSV import splits on tabs and lines; keep fields on one line.
    return " ".join((s or "").split())


def anki_fields(t, sentence, tag_names, roots):
    """The 10 fields of the Anki note (order = docs/anki.md)."""
    fg = t.get("furigana") or ([[t["ja"], t["reading"]]] if KANJI.search(t["ja"]) else [[t["ja"]]])
    sense = t["senses"][0]
    gloss = "; ".join(", ".join(s["en"]) for s in t["senses"] if s["en"])
    tags = sense.get("tags") or []
    top = tag_names[roots[tags[0]][-1]]["ja"] if tags else ""
    f = {"Term": t["ja"], "TermFurigana": anki_ruby(fg), "Reading": t["reading"], "Gloss": gloss,
         "Sentence": "", "SentenceFurigana": "", "SentenceEN": "", "POS": sense["pos"], "Tag": top, "Source": ""}
    if sentence:
        a, b = sentence["spans"].get(t["id"], (None, None))
        ja = sentence["ja"]
        f["Sentence"] = ja if a is None else f"{ja[:a]}<b>{ja[a:b]}</b>{ja[b:]}"
        f["SentenceFurigana"] = anki_ruby(sentence["segs"], (a, b) if a is not None else None)
        f["SentenceEN"] = sentence["en"] or ""
        src = sentence["source"]
        by = {"machine": "machine translation", "human": "translated by hand",
              "source": "translation from source", None: "no translation yet"}[sentence["en_by"]]
        f["Source"] = f"{src['type']} {src.get('ref') or ''}".strip() + f" · {by}"
    return {k: clean(v) for k, v in f.items()}


def unlinked_warnings(terms, sentences):
    """Known terms that appear in a sentence but aren't linked to it.

    A mention inside an already-linked term doesn't count (加工 inside a
    linked 加工振動 is fine).
    """
    out = []
    for s in sentences.values():
        ja, spans = s["ja"], s["spans"].values()
        for t in terms.values():
            if t["id"] in s["spans"] or len(t["ja"]) < 2:
                continue
            for w in [t["ja"], *t.get("alt", [])]:
                i = ja.find(w)
                while i != -1 and any(a <= i and i + len(w) <= b for a, b in spans):
                    i = ja.find(w, i + 1)
                if i != -1:
                    out.append(f"{s['id']}: contains {w} ({t['id']}) but doesn't link it")
                    break
    return out


def build(verbose=False):
    errors, _, _ = validate()
    if errors:
        print("\n".join(errors))
        sys.exit("Data is invalid; fix the problems above (python tools/validate.py).")

    tags = load_yaml(TAGS)
    tag_by_id = {t["id"]: t for t in tags}
    roots = tag_ancestors(tags)
    terms = {t["id"]: t for _, t in records(TERMS)}
    sentences = {}
    for _, s in records(SENTENCES):
        s["spans"] = place_spans(s["ja"], s["terms"])
        s["segs"] = sentence_segments(s["ja"], s["spans"], terms)
        sentences[s["id"]] = s

    # Term -> its sentences, ordered by date added, then id (docs/handoff.md section 4).
    by_date = sorted(sentences.values(), key=lambda s: (s["added"], s["id"]))
    for t in terms.values():
        t["sentences"] = [s["id"] for s in by_date if any(x["id"] == t["id"] for x in s["terms"])]
        t["card"] = t.get("card_sentence") or (t["sentences"][0] if t["sentences"] else None)
        t["tags_all"] = sorted({a for s in t["senses"] for tag in s.get("tags", []) for a in roots[tag]})
        t["anki"] = anki_fields(t, sentences.get(t["card"]), tag_by_id, roots)

    warnings = unlinked_warnings(terms, sentences)
    for w in warnings if verbose else []:
        print("warning:", w)

    out = {
        "terms": sorted(terms.values(), key=lambda t: t["id"]),
        "sentences": sentences,
        "tags": tags,
        "lists": [lst for _, lst in records(LISTS)],
        "i18n": {p.stem: load_yaml(p) for p in sorted(I18N.glob("*.yaml"))},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    reviewed = sum(t["status"] == "reviewed" for t in terms.values())
    print(f"Wrote {pathlib.Path(OUT).relative_to(ROOT)}: {len(terms)} terms ({reviewed} reviewed), "
          f"{len(sentences)} sentences.")
    if warnings and not verbose:
        print(f"{len(warnings)} places where a sentence mentions a known term without linking it; "
              "see them with: python tools/build.py --verbose")


if __name__ == "__main__":
    build(verbose="--verbose" in sys.argv)
