"""Look up English glosses in JMdict (https://www.edrdg.org/jmdict/j_jmdict.html).

Download JMdict_e.gz (English-only) and pass its path; it is ~60 MB unpacked, so
it is not stored in the repo. Glosses taken from it are CC BY-SA 4.0 (EDRDG)
and are credited in ATTRIBUTION.md.
"""
import gzip
import re
import xml.etree.ElementTree as ET

from common import kata_to_hira

# JMdict part-of-speech descriptions -> our short `pos` values (schema/term.schema.json).
# First match wins, so order matters: a sense marked both "noun" and "takes suru"
# is a suru-noun, and "adverbial noun" (毎秒, 通常) is a noun, not a verb.
POS_MAP = [
    (r"takes the aux\. verb suru", "suru-noun"),
    (r"^adjectival nouns", "na-adj"),
    (r"^adjective \(keiyoushi\)", "i-adj"),
    (r"^(noun|adverbial noun)", "noun"),
    (r"\bverb\b", "verb"),
    (r"^adverb", "adverb"),
    (r"^expressions", "expression"),
    (r"^prefix", "prefix"),
    (r"^suffix", "suffix"),
    (r"^counter", "counter"),
]


def map_pos(jm_pos):
    for pattern, ours in POS_MAP:
        if any(re.search(pattern, p) for p in jm_pos):
            return ours
    return "other"


def load(path):
    """Index JMdict by (written form, reading in hiragana) -> list of senses.

    Each sense is {"pos", "gloss", "stagk", "stagr", "field"}, each a list of strings.
    """
    opener = gzip.open if str(path).endswith(".gz") else open
    index = {}
    with opener(path, "rb") as f:
        # iterparse keeps memory flat: each <entry> is handled and then cleared.
        for _, el in ET.iterparse(f):
            if el.tag != "entry":
                continue
            kebs = [k.text for k in el.iter("keb")]
            rebs = [r.text for r in el.iter("reb")]
            senses, last_pos = [], []
            for s in el.iter("sense"):
                # JMdict only repeats <pos> when it changes; inherit otherwise.
                pos = [p.text for p in s.iter("pos")] or last_pos
                last_pos = pos
                gloss = [g.text for g in s.iter("gloss")]
                if gloss:
                    senses.append({"pos": pos, "gloss": gloss, "stagk": [t.text for t in s.iter("stagk")],
                                   "stagr": [t.text for t in s.iter("stagr")],
                                   "field": [t.text for t in s.iter("field")]})
            for written in kebs or rebs:
                for reb in rebs:
                    # Some senses only apply to certain spellings (stagk) or readings (stagr).
                    mine = [s for s in senses if (not s["stagk"] or written in s["stagk"])
                            and (not s["stagr"] or reb in s["stagr"])]
                    index.setdefault((written, kata_to_hira(reb)), []).extend(mine)
            el.clear()
    return index


def lookup(index, ja, reading, max_senses=3):
    return index.get((ja, kata_to_hira(reading)), [])[:max_senses]
