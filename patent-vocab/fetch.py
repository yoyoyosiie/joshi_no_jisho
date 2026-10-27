"""Fetch a patent page from Google Patents and pull out its text sections.

Respects robots.txt and waits between requests. Also parses saved HTML files,
so you can download pages by hand and run the extractor offline.
"""
import re
import time
import urllib.robotparser
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

BASE = "https://patents.google.com"
UA = "josie-dict-vocab/0.1 (personal study dictionary; low-rate)"
DELAY_S = 5.0  # seconds between requests

_robots = None
_last = 0.0


@dataclass
class Patent:
    number: str
    lang: str
    title: str = ""
    abstract: str = ""
    claims: list = field(default_factory=list)  # one string per claim
    description: str = ""
    family: list = field(default_factory=list)  # publication numbers


def _allowed(url):
    global _robots
    if _robots is None:
        _robots = urllib.robotparser.RobotFileParser(BASE + "/robots.txt")
        _robots.read()
    return _robots.can_fetch(UA, url)


def get_html(number, lang="ja"):
    global _last
    url = f"{BASE}/patent/{number}/{lang}"
    if not _allowed(url):
        raise PermissionError(f"robots.txt disallows {url}")
    wait = DELAY_S - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    _last = time.time()
    r.raise_for_status()
    return r.text


def _text(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)) if node else ""


def parse(html, number="", lang="ja"):
    s = BeautifulSoup(html, "lxml")
    p = Patent(number=number, lang=lang)
    p.title = _text(s.find(itemprop="title"))
    p.abstract = _text(s.find("section", itemprop="abstract"))
    p.description = _text(s.find("section", itemprop="description"))
    claims = s.find("section", itemprop="claims")
    if claims:
        # top-level claims only; nested claim-text would duplicate text
        p.claims = [_text(c) for c in claims.select("div.claim:not(div.claim div.claim)")] \
            or [_text(claims)]
    for row in s.find_all(itemprop="docdbFamily"):
        num = row.find(itemprop="publicationNumber")
        if num:
            p.family.append(num.get_text(strip=True))
    return p


def fetch(number, lang="ja"):
    return parse(get_html(number, lang), number, lang)


def english_member(p):
    """Pick the family member most likely to be an English text (US > EP > WO)."""
    for prefix in ("US", "EP", "WO", "GB", "AU", "CA"):
        for n in p.family:
            if n.startswith(prefix):
                return n
    return None
