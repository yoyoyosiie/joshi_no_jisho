"""Read a Japanese patent PDF (JPO gazette or WIPO WO pamphlet) into a Patent.

Pages with a text layer are read with pdftotext. Scanned pages (most patent
PDFs) are OCR'd with Tesseract's jpn model; results are cached so reruns are
instant. Needs poppler-utils, plus tesseract-ocr + tesseract-ocr-jpn for scans.
"""
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from fetch import Patent

CACHE = pathlib.Path(os.environ.get("PATENT_VOCAB_CACHE", "~/.cache/patent-vocab")).expanduser()
JP_CHAR = r"[々぀-ヿ一-鿿]"
# OCR'd scans are often only 72 "dpi" in the PDF; render at twice native width.
OCR_WIDTH = 4960

# Repeated page furniture: "WO 2021/079959 17 PCT/JP2020/039803", "(2) JP 2020-123456 A 2020.8.13"
HEADER = re.compile(r"^\s*(WO\s?\d{4}/|.*PCT/JP|\(\d+\)\s*(JP|特開|特表)|(JP|特開|特表)\s*[\d\-]+\s*[AB]\d?\s)")
DRAWING_SHEET = re.compile(r"^\s*\S{1,2}\s*/\s*\d{1,2}\s*$")  # "1/6" sheet number on WIPO drawing pages
TAIL_PAGE = re.compile(r"INTERNATIONAL\s*SEARCH\s*REPORT|国際調査報告|【書類名】\s*図面")
PARA_NO = re.compile(r"【\s*[\dOoＯ ]{4,6}\s*[】\]1l]?")  # 【0002】, OCR'd as 【00021 or 【0 003】
NUMBER = re.compile(r"WO\s?\d{4}\s?[/7]?\s?[\dS]{6}(?![\dS])|(特開|特表|再表)\s?\d{4}\s?-\s?\d+|特許第?\s?\d{7}号?|JP\s?\d{4}-?\d+\s?[AB]\d?")


def _run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def _need(tool, pkg):
    if not shutil.which(tool):
        raise RuntimeError(f"{tool} not found: install {pkg}")


def _page_count(path):
    return int(re.search(r"Pages:\s+(\d+)", _run("pdfinfo", str(path))).group(1))


def _ocr_page(path, page, lang):
    _need("tesseract", "tesseract-ocr and tesseract-ocr-jpn")
    with tempfile.TemporaryDirectory() as d:
        img = pathlib.Path(d) / "p"
        _run("pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-gray", "-png",
             "-scale-to", str(OCR_WIDTH), str(path), str(img))
        # one thread per tesseract; parallelism comes from running pages side by side
        env = {**os.environ, "OMP_THREAD_LIMIT": "1"}
        return subprocess.run(["tesseract", f"{img}.png", "-", "-l", lang, "--psm", "6"],
                              capture_output=True, text=True, check=True, env=env).stdout


def pages(path):
    """Text of each page, OCR'ing pages that have no text layer. Cached per file."""
    _need("pdftotext", "poppler-utils")
    key = hashlib.sha1(pathlib.Path(path).read_bytes()).hexdigest()[:16]
    cache = CACHE / f"{key}.pages.txt"
    if cache.exists():
        return cache.read_text(encoding="utf-8").split("\f")

    def one(i):
        t = _run("pdftotext", "-f", str(i), "-l", str(i), "-enc", "UTF-8", str(path), "-")
        return t if len(re.findall(JP_CHAR, t)) >= 20 else _ocr_page(path, i, "jpn")

    n = _page_count(path)
    with ThreadPoolExecutor(os.cpu_count() or 2) as ex:
        out = list(ex.map(one, range(1, n + 1)))
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text("\f".join(out), encoding="utf-8")
    return out


def clean(text):
    text = unicodedata.normalize("NFKC", text)  # full-width digits/letters -> ASCII; 【】 survive
    text = "\n".join(l for l in text.splitlines() if not HEADER.match(l))
    text = PARA_NO.sub("\n", text)
    text = re.sub(r"(?m)(^|\s)[「」'|‘’“”]+(?=\s|$)", " ", text)  # OCR specks at line ends
    # Japanese has no spaces: rejoin words split by line breaks or OCR gaps.
    text = re.sub(rf"(?<={JP_CHAR}|[、。)）])\s+(?={JP_CHAR}|[(（])", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _section(text, start, stops):
    m = re.search(start, text)
    if not m:
        return ""
    end = min([m.end() + n.start() for s in stops if (n := re.search(s, text[m.end():]))] or [len(text)])
    return text[m.end():end].strip()


def _front_english(path):
    """English title + abstract printed on a WIPO front page (Japanese-language filings)."""
    try:
        t = _ocr_page(path, 1, "eng")
    except (RuntimeError, subprocess.CalledProcessError):
        return {}
    t = re.sub(r"[ \t]+", " ", t)
    title = re.search(r"Title:\s*(.+)", t)
    abstract = re.search(r"Abstract:\s*(.+)", t, re.S)
    out = {}
    if title:
        out["title"] = title.group(1).strip()
    if abstract:
        lines = []
        for l in abstract.group(1).splitlines():
            words = re.findall(r"[A-Za-z]+", l)
            # English prose is mostly lowercase words; the Japanese abstract OCR'd as eng is not
            if not words or sum(w.islower() for w in words) < 0.6 * len(words):
                break
            lines.append(re.sub(r"^\W{0,4}", "", l))
        out["abstract"] = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return out


def parse_pdf(path, number=""):
    """Returns (Patent, english) where english is {} or the front-page title/abstract."""
    path = pathlib.Path(path)
    raw = pages(path)
    english = {}
    body = []
    for i, pg in enumerate(raw):
        head = "\n".join(pg.strip().splitlines()[:4])
        if TAIL_PAGE.search(head):
            break  # search report / drawings follow; nothing useful after
        if any(DRAWING_SHEET.match(l) for l in head.splitlines()):
            continue
        if i == 0 and re.search(r"Title:|Abstract:|\(5[47]\)", pg):
            english = _front_english(path)  # bibliographic front page, not body text
            continue
        body.append(pg)
    text = clean("\n".join(body))

    p = Patent(number=number or _guess_number("\n".join(raw[:2]), path), lang="ja")
    p.title = _section(text, r"【発明の名称】", [r"【"])[:100]
    p.abstract = _section(text, r"【要約】|要約書", [r"【選択図】", r"【", r"$"])
    claims = _section(text, r"請求の範囲|特許請求の範囲】", [r"【書類名】", r"明細書", r"要約書", r"【要約】"])
    p.claims = [c.strip() for c in re.split(r"【\s*請求項\s*\d+\s*】", claims) if c.strip()]
    p.description = _section(text, r"【技術分野】|【発明の詳細な説明】", [r"【符号の説明】", r"請求の範囲", r"【書類名】"])
    if not (p.claims or p.description):
        p.description = text  # unknown layout: use everything rather than nothing
    return p, english


def _guess_number(text, path):
    m = NUMBER.search(unicodedata.normalize("NFKC", text))
    if not m:
        return path.stem
    n = re.sub(r"\s", "", m.group(0))
    if n.startswith("WO"):  # OCR reads the slash as 7 and 5 as S
        n = "WO" + n[2:6] + "/" + n[-6:].replace("S", "5")
    return n
