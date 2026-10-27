"""Shared helpers for the data tools: where things live, YAML in/out, kana folding."""
import os
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
# JISHO_DATA lets the tests point the tools at a scratch copy of data/.
DATA = pathlib.Path(os.environ.get("JISHO_DATA", ROOT / "data"))
TERMS = DATA / "terms"
SENTENCES = DATA / "sentences"
LISTS = DATA / "lists"
I18N = DATA / "i18n"
TAGS = DATA / "tags.yaml"
SCHEMA = ROOT / "schema"

KANJI = re.compile(r"[々〆ヵヶ一-鿿㐀-䶿]")


class _Loader(yaml.SafeLoader):
    pass


class _Dumper(yaml.SafeDumper):
    pass


# PyYAML turns `added: 2026-10-27` into a date object, which then fails the JSON
# Schema "string" check. Drop the timestamp rule so dates stay plain strings,
# both when reading and when writing (otherwise the dumper quotes them).
for cls in (_Loader, _Dumper):
    cls.yaml_implicit_resolvers = {
        k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:timestamp"]
        for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Loader)


def dump_yaml(obj):
    # default_flow_style=None: short lists like `en: [vibration]` stay on one line,
    # while records with nested parts are written as blocks.
    return yaml.dump(obj, Dumper=_Dumper, allow_unicode=True, sort_keys=False,
                     default_flow_style=None, width=1000)


def write_yaml(path, obj):
    path.write_text(dump_yaml(obj), encoding="utf-8")


def kata_to_hira(s):
    """ア -> あ. Leaves ー, ASCII and kanji alone."""
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def records(folder):
    """Every *.yaml in a folder, sorted, as (path, data)."""
    return [(p, load_yaml(p)) for p in sorted(folder.glob("*.yaml"))]


def next_id(folder, prefix):
    """t000001, t000002, ...: one more than the highest id already on disk."""
    nums = [int(p.stem[1:]) for p in folder.glob(f"{prefix}*.yaml") if p.stem[1:].isdigit()]
    return max(nums, default=0) + 1
