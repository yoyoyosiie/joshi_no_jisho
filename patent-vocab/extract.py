"""Pull technical compound nouns out of Japanese patent text with Sudachi.

Consecutive nouns are joined into one compound (減速 + 機構 -> 減速機構).
Patent boilerplate (前記, 本発明, 請求項 ...) is dropped.
"""
import re
from collections import defaultdict

from sudachipy import dictionary, tokenizer

_tok = dictionary.Dictionary(dict="core").create(tokenizer.Tokenizer.SplitMode.C)

# Boilerplate that shows up in every patent and is not vocabulary.
STOP = set("""
前記 上記 当該 本 本発明 発明 実施 実施形態 実施例 形態 一態様 態様 請求 請求項 図 図面
参照 場合 こと もの ため よう 以下 以上 未満 一方 他方 各 複数 一部 全体 構成 方法 装置
課題 解決 解決手段 手段 効果 提供 目的 特許 文献 技術 分野 背景 記載 説明 説明図 符号 所定 同様 例 第 等 他
必要 特徴 一般 従来 近年 容易 正確 可能 状態 具体 詳細
""".split())
PREFIX_STOP = ("前記", "上記", "当該", "該", "本", "各", "第")

SENT_SPLIT = re.compile(r"(?<=[。！？])")
HAS_JP = re.compile(r"[一-鿿゠-ヿ]")


def kata_to_hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def _reading(m):
    """Per-token reading: kanji -> hiragana, katakana and ASCII (TPF, W) kept as written."""
    surf = m.surface()
    if re.fullmatch(r"[\x21-\x7e]+|[゠-ヿ]+", surf):
        return surf
    return kata_to_hira(m.reading_form())


def _is_noun(m):
    pos = m.part_of_speech()
    if pos[0] == "名詞" and pos[1] != "数詞":
        return True
    # 性 / 化 / 器 style suffixes glue onto the preceding noun
    return pos[0] == "接尾辞" and pos[1] == "名詞的"


def compounds(sentence):
    """Yield (surface, reading) for each noun run in one sentence."""
    run = []

    def flush():
        n = len(run)
        while run and run[0].surface() in PREFIX_STOP:
            run.pop(0)
        # Sudachi tags 高 in 前記高周波 as a suffix of 前記; after 前記 it starts the term.
        # Only a suffix that opens the sentence-level run is really dangling.
        while len(run) == n and run and run[0].part_of_speech()[0] == "接尾辞":
            run.pop(0)
            n -= 1
        if run:
            yield "".join(m.surface() for m in run), "".join(_reading(m) for m in run)
        run.clear()

    for m in _tok.tokenize(sentence):
        if _is_noun(m):
            run.append(m)
            continue
        # a lone サ変 noun used as a verb (低減する, 支持される) is not a term
        if len(run) == 1 and run[0].part_of_speech()[2] == "サ変可能" and m.part_of_speech()[0] == "動詞":
            run.clear()
        yield from flush()
    yield from flush()


def keep(term):
    return len(term) >= 2 and term not in STOP and HAS_JP.search(term) \
        and not re.fullmatch(r"[぀-ゟ]+", term)  # all-hiragana is rarely a term


def extract(docs):
    """docs: iterable of (source_id, text). Returns a list of term dicts sorted by score."""
    terms = defaultdict(lambda: {"reading": "", "freq": 0, "sources": set(), "example": ""})
    for src, text in docs:
        for sent in SENT_SPLIT.split(text):
            sent = re.sub(r"【[^】]*】", "", sent).strip()
            for surf, read in compounds(sent):
                if not keep(surf):
                    continue
                t = terms[surf]
                t["reading"] = read
                t["freq"] += 1
                t["sources"].add(src)
                if not t["example"] or len(sent) < len(t["example"]):
                    t["example"] = sent[:200]
    out = [{"term": k, **v, "sources": sorted(v["sources"])} for k, v in terms.items()]
    # Longer compounds and terms seen in many patents are more likely real vocabulary.
    for t in out:
        t["score"] = t["freq"] * (1 + 0.5 * (len(t["term"]) > 3)) * len(t["sources"])
    return sorted(out, key=lambda t: -t["score"])
