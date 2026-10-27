"""Split a term into furigana pairs: 加工振動 -> [[加工, かこう], [振動, しんどう]].

Uses Sudachi (same as tools/patent-vocab). If Sudachi isn't installed, or its
reading doesn't agree with the term's stored reading, returns None and the
term simply has no furigana until someone adds it by hand.
"""
import re

from common import KANJI, kata_to_hira

try:
    from sudachipy import dictionary, tokenizer
    # Mode A = shortest units, so 加工振動 splits into 加工 + 振動.
    _tok = dictionary.Dictionary(dict="core").create(tokenizer.Tokenizer.SplitMode.A)
except ImportError:
    _tok = None

KANA = re.compile(r"[ぁ-ゖァ-ヺー]+")


def _split_token(surface, reading):
    """One token -> pairs. Kana inside the word (okurigana) anchors the split:
    切り込み / きりこみ -> [切, き], [り], [込, こ], [み]."""
    if not KANJI.search(surface):
        return [[surface]]
    parts = re.findall(r"[々〆ヵヶ一-鿿㐀-䶿]+|[^々〆ヵヶ一-鿿㐀-䶿]+", surface)
    pattern = "".join("(.+?)" if KANJI.match(p) else "(" + re.escape(kata_to_hira(p)) + ")" for p in parts)
    m = re.fullmatch(pattern, reading)
    if not m:
        return [[surface, reading]]
    return [[p, r] if KANJI.match(p) else [p] for p, r in zip(parts, m.groups())]


def furigana(ja, reading):
    if _tok is None or not KANJI.search(ja):
        return None
    pairs = []
    for m in _tok.tokenize(ja):
        r = kata_to_hira(m.reading_form())
        if KANJI.search(m.surface()) and not KANA.fullmatch(r):
            return None  # Sudachi didn't know this word (e.g. 難削性): leave it to a human
        pairs += _split_token(m.surface(), r)
    joined = "".join(p[1] if len(p) == 2 else p[0] for p in pairs)
    if kata_to_hira(joined).lower() != kata_to_hira(reading).lower():
        return None  # disagrees with the stored reading; don't guess
    return pairs
