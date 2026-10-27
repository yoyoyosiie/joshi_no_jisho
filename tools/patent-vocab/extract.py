"""Pull technical compound nouns out of Japanese patent text with Sudachi.

Consecutive nouns are joined into one compound (減速 + 機構 -> 減速機構).
Patent boilerplate (前記, 本発明, 請求項 ...) is dropped.
Each term gets `flags` for a human to check: likely OCR junk, or a reading
Sudachi had to guess (see FLAGS).
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
特開 特開平 特表 公報 号公報 特許文献 フロントページ 続き 発明者 丁目 図略 不図示
""".split())
PREFIX_STOP = ("前記", "上記", "当該", "該", "本", "各", "第", "ため", "それぞれ", "そのまま", "種々", "下記")

# Words Sudachi doesn't know or reads wrong in machine-part text, keyed by the
# surface of one to three consecutive Sudachi tokens (longest match wins).
READING_FIX = {
    "経時": "けいじ",          # Sudachi: きょうじ
    "削性": "さくせい",        # 難削性, 被削性 (unknown word, no reading)
    "削材": "さくざい",        # 被削材
    "削": "さく",              # 被削対象材
    "赤色": "あかいろ",        # Sudachi: せきしょく; patents list it with 青色 (あおいろ), 黄色 ...
    "挿通孔": "そうつうこう",  # 挿+通+孔: さしとおりこう
    "通孔": "つうこう",
    "端板": "たんばん",        # はたいた
    "溝間": "みぞかん",
    "等分割": "とうぶんかつ",  # とうぶんわり
    "上方": "じょうほう",      # かみがた
    "外歯": "そとば",          # 外歯車 そとばぐるま; Sudachi: そとは
    "内歯": "うちば",          # 内歯車 うちばぐるま; Sudachi: うちは
    "普通刃": "ふつうば",      # ふつうじん (外周刃 がいしゅうじん is right as is)
    "刃形": "はがた",          # 波刃形: なみじんけい
    "介装": "かいそう",        # すけそう
    "主面": "しゅめん",        # しゅうづら
    "上面": "じょうめん",      # うわつら
    "受": "うけ",              # 主軸受: しゅじくじゅ
    "縮径": "しゅくけい",      # ちぢみけい
    "係合": "けいごう",        # かかりあい
    "位置決め": "いちぎめ",    # いちきめ
    "溝": "みぞ",              # ボール溝, ピン溝: こう
    "外面": "がいめん",        # そとづら
    "低コスト": "ていコスト",  # one token, so its katakana got turned into hiragana
}
# Conjunctions OCR or Sudachi sometimes glue onto the end of a term (余剰周波数又は).
TRAIL_STOP = {"又", "及", "等"}

FLAGS = {
    "ocr?": "probably an OCR misread: unknown katakana word, or a rare near-copy of a common term",
    "reading?": "Sudachi didn't know part of this word, so the reading is a guess or missing",
    "reading-fixed": "reading corrected from READING_FIX; worth a glance",
}

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
    # 性 / 化 / 器 style suffixes glue onto the preceding noun; 被 / 非 / 無 style prefixes onto the next
    return (pos[0] == "接尾辞" and pos[1] == "名詞的") or pos[0] == "接頭辞"


LABEL = re.compile(r"[A-Za-z]{1,2}\d*")  # reference labels: ワークW, 工具T1
UNIT = re.compile(r"[a-zμ%°/]+")  # tail of a number (5%以下, 100m/min時, 6b側): not part of the word


def _token_reading(m, notes):
    surf = m.surface()
    if m.is_oov() and re.fullmatch(r"[゠-ヿ]+", surf):
        notes.add("oov-kata")
    elif m.is_oov() and re.search(r"[一-鿿]", surf):  # ASCII like TPF is fine as written
        notes.add("reading?")
    return _reading(m)


def _run_reading(run, notes):
    out, i = [], 0
    while i < len(run):
        for n in (3, 2, 1):
            surf = "".join(m.surface() for m in run[i:i + n])
            if i + n <= len(run) and surf in READING_FIX:
                notes.add("reading-fixed")
                out.append(READING_FIX[surf])
                i += n
                break
        else:
            out.append(_token_reading(run[i], notes))
            i += 1
    return "".join(out)


def compounds(sentence):
    """Yield (surface, reading, notes) for each noun run in one sentence."""
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
        while run and run[-1].part_of_speech()[0] == "接頭辞":  # prefix with nothing after it
            run.pop()
        # A trailing label (ワークW, 工具T1) is a drawing reference, not part of the word.
        # Leading letters stay: X軸, V溝 are real terms.
        while len(run) > 1 and (LABEL.fullmatch(run[-1].surface()) or run[-1].surface() in TRAIL_STOP):
            run.pop()
        while len(run) > 1 and UNIT.fullmatch(run[0].surface()):
            run.pop(0)
        if run:
            notes = set()
            reading = _run_reading(run, notes)
            yield "".join(m.surface() for m in run), reading, notes
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
    return len(term) >= 2 and term not in STOP and HAS_JP.search(term) and "株式会社" not in term \
        and not re.fullmatch(r"[぀-ゟ]+", term)  # all-hiragana is rarely a term


def _near(a, b):
    """True if a and b differ by one character swapped, or one extra character inside.

    That is what OCR misreads look like (スベクトラム / スペクトラム). An extra
    character at either end is usually a real longer compound, so it doesn't count.
    """
    if abs(len(a) - len(b)) > 1 or a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = sorted((a, b), key=len)
    return any(long_[:i] + long_[i + 1:] == short for i in range(1, len(long_) - 1))


def flag(terms, ocr_sources=()):
    """Turn per-token notes into the CSV `flags`: ocr?, reading?, reading-fixed.

    The ocr? checks only run on terms from OCR'd sources; in a text-layer PDF an
    unknown katakana word or a near-copy is a real word.
    """
    common = [t for t in terms if t["freq"] >= 3]
    for t in terms:
        notes, f = t.pop("notes"), set()
        ocr = bool(set(t["sources"]) & set(ocr_sources))
        if ocr and "oov-kata" in notes and t["freq"] < 5:
            f.add("ocr?")
        if ocr and t["freq"] <= 2 and len(t["term"]) >= 3 and \
                any(c["freq"] >= 3 * t["freq"] and _near(t["term"], c["term"]) for c in common):
            f.add("ocr?")
        if "reading?" in notes or re.search(r"[一-鿿]", t["reading"]):
            f.add("reading?")
        f |= notes & {"reading-fixed"}
        t["flags"] = sorted(f)
    return terms


def _clip(sent, term, width=200):
    """At most `width` chars of the sentence, always including the term."""
    if len(sent) <= width:
        return sent
    start = max(0, min(sent.find(term) - width // 3, len(sent) - width))
    return sent[start:start + width]


def extract(docs, ocr_sources=()):
    """docs: iterable of (source_id, text); ocr_sources: ids whose text came from OCR.
    Returns a list of term dicts sorted by score."""
    terms = defaultdict(lambda: {"reading": "", "freq": 0, "sources": set(), "example": "", "notes": set()})
    for src, text in docs:
        for sent in SENT_SPLIT.split(text):
            sent = re.sub(r"【[^】]*】", "", sent).strip()
            sent = sent.replace("又は", "または")  # else Sudachi reads 周波数又は as 周波 + 数又 (a place name)
            for surf, read, notes in compounds(sent):
                if not keep(surf):
                    continue
                t = terms[surf]
                t["reading"] = read
                t["notes"] |= notes
                t["freq"] += 1
                t["sources"].add(src)
                if not t["example"] or len(sent) < len(t["example"]):
                    t["example"] = _clip(sent, surf)
    out = [{"term": k, **v, "sources": sorted(v["sources"])} for k, v in terms.items()]
    # Longer compounds and terms seen in many patents are more likely real vocabulary.
    for t in out:
        t["score"] = t["freq"] * (1 + 0.5 * (len(t["term"]) > 3)) * len(t["sources"])
    return sorted(flag(out, ocr_sources), key=lambda t: -t["score"])
