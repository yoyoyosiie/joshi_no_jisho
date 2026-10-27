"""Tests for the data tools. Run from the repo root:

    python -m unittest discover tools/tests

Each test copies tags.yaml + i18n into a temp folder and points the tools at it
with JISHO_DATA, so the real data/ is never touched.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).resolve().parent.parent
ROOT = TOOLS.parent
SAMPLE_CSV = TOOLS / "patent-vocab" / "tests" / "sample_vocab.csv"

sys.path.insert(0, str(TOOLS))
import build  # noqa: E402
import jmdict  # noqa: E402


def run(tool, *args, data):
    env = {**os.environ, "JISHO_DATA": str(data), "PYTHONWARNINGS": "ignore"}
    return subprocess.run([sys.executable, str(TOOLS / tool), *map(str, args)],
                          capture_output=True, text=True, env=env, encoding="utf-8")


class DataTest(unittest.TestCase):
    def setUp(self):
        self.data = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.data)
        shutil.copy(ROOT / "data" / "tags.yaml", self.data)
        shutil.copytree(ROOT / "data" / "i18n", self.data / "i18n")
        for d in ("terms", "sentences", "lists"):
            (self.data / d).mkdir()

    def write(self, rel, text):
        (self.data / rel).write_text(text, encoding="utf-8")

    def assertInvalid(self, needle):
        r = run("validate.py", data=self.data)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(needle, r.stdout)

    def term(self, tid="t000001", ja="振動", reading="しんどう", extra=""):
        self.write(f"terms/{tid}.yaml", f"""id: {tid}
ja: {ja}
reading: {reading}
senses:
- {{pos: noun, en: [vibration], tags: [vibration]}}
sources: []
added: 2026-10-27
status: reviewed
{extra}""")


class ValidateTest(DataTest):
    def test_real_data_is_valid(self):
        r = subprocess.run([sys.executable, str(TOOLS / "validate.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_minimal_term_ok(self):
        self.term()
        self.assertEqual(run("validate.py", data=self.data).returncode, 0)

    def test_unknown_tag(self):
        self.term(extra="")
        p = self.data / "terms/t000001.yaml"
        p.write_text(p.read_text(encoding="utf-8").replace("tags: [vibration]", "tags: [nope]"), encoding="utf-8")
        self.assertInvalid("unknown tag nope")

    def test_furigana_must_match(self):
        self.term(extra="furigana: [[振動, しんど]]\n")
        self.assertInvalid("furigana reads")

    def test_reviewed_needs_gloss(self):
        self.term()
        p = self.data / "terms/t000001.yaml"
        p.write_text(p.read_text(encoding="utf-8").replace("en: [vibration]", "en: []"), encoding="utf-8")
        self.assertInvalid("needs English glosses")

    def test_duplicate_headword(self):
        self.term()
        self.term(tid="t000002", reading="シンドウ")  # katakana reading = same word
        self.assertInvalid("same headword and reading")

    def test_file_name_must_match_id(self):
        self.term()
        (self.data / "terms/t000001.yaml").rename(self.data / "terms/t000009.yaml")
        self.assertInvalid("does not match file name")

    def test_sentence_links(self):
        self.term()
        self.write("sentences/s000001.yaml", """id: s000001
ja: 振動を測る。
en: null
terms: [{id: t000001, surface: 振動}, {id: t000002, surface: 揺れ}]
source: {type: original, ref: null}
en_by: null
added: 2026-10-27
""")
        r = run("validate.py", data=self.data)
        self.assertIn("unknown term t000002", r.stdout)
        self.assertIn("surface 揺れ is not in the sentence", r.stdout)


class ImportTest(DataTest):
    def test_import_sample_then_rerun(self):
        r = run("import.py", SAMPLE_CSV, "--date", "2026-10-27", data=self.data)
        self.assertEqual(r.returncode, 0, r.stderr)
        terms = sorted((self.data / "terms").glob("*.yaml"))
        self.assertEqual(len(terms), 12)
        self.assertIn("status: draft", terms[0].read_text(encoding="utf-8"))
        self.assertEqual(run("validate.py", data=self.data).returncode, 0)

        # Same CSV again: everything is a duplicate, nothing new is written.
        r = run("import.py", SAMPLE_CSV, data=self.data)
        self.assertIn("0 new terms", r.stdout)
        self.assertEqual(len(list((self.data / "terms").glob("*.yaml"))), 12)

    def test_machine_gloss_and_flags(self):
        csv_path = self.data / "v.csv"
        csv_path.write_text(
            "term,reading,freq,n_patents,sources,example_ja,english,en_by,en_source,flags\n"
            "びびり振動,びびりしんどう,5,1,JP1,びびり振動を抑える。,chatter; chatter vibration,machine,,\n"
            "ワソーク,ワソーク,1,1,JP1,ワソークを固定する。,,,,ocr?\n"
            "警告城,けいこくじょう,1,1,JP1,警告城に入る。,,,,not-a-term?\n", encoding="utf-8")
        r = run("import.py", csv_path, "--date", "2026-10-27", data=self.data)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("? ", r.stdout)
        self.assertIn("1 imported rows flagged", r.stdout)
        self.assertIn("1 not-a-term rows skipped", r.stdout)
        self.assertEqual(len(list((self.data / "terms").glob("*.yaml"))), 2)
        first = (self.data / "terms" / "t000001.yaml").read_text(encoding="utf-8")
        self.assertIn("en_by: machine", first)
        self.assertEqual(run("validate.py", data=self.data).returncode, 0)

    def test_shared_sentence(self):
        run("import.py", SAMPLE_CSV, "--date", "2026-10-27", data=self.data)
        # 減速機構 and 回転軸 share one example sentence -> one file, two links.
        shared = [p for p in (self.data / "sentences").glob("*.yaml")
                  if "減速機構" in p.read_text(encoding="utf-8") and "t000002" in p.read_text(encoding="utf-8")]
        self.assertEqual(len(shared), 1)


class ExtractFlagsTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(TOOLS / "patent-vocab"))
        import extract
        self.extract = extract

    def terms(self, text):
        return {t["term"]: t for t in self.extract.extract([("JP1", text)], ocr_sources={"JP1"})}

    def test_flags(self):
        t = self.terms("経時変化を測定する。被削材を加工する。ワークWを固定する。ワソークを固定する。"
                       "ワークを固定する。ワークを測定する。")
        self.assertEqual(t["経時変化"]["reading"], "けいじへんか")
        self.assertEqual(t["経時変化"]["flags"], ["reading-fixed"])
        self.assertEqual(t["被削材"]["reading"], "ひさくざい")  # 被 prefix is kept
        self.assertEqual(self.terms("内歯ピンを入れる。")["内歯ピン"]["reading"], "うちばピン")
        self.assertNotIn("ワークW", t)                        # drawing label dropped
        self.assertEqual(t["ワーク"]["flags"], [])
        self.assertIn("ocr?", t["ワソーク"]["flags"])

    def test_no_ocr_flags_on_text_layer(self):
        t = {t["term"]: t for t in self.extract.extract([("JP1", "ワソークを固定する。5%以下にする。")])}
        self.assertEqual(t["ワソーク"]["flags"], [])
        self.assertNotIn("%以下", t)  # unit tail of a number is dropped


class JmdictTest(unittest.TestCase):
    XML = """<JMdict><entry><ent_seq>1</ent_seq>
<k_ele><keb>赤色</keb></k_ele><r_ele><reb>あかいろ</reb></r_ele><r_ele><reb>せきしょく</reb></r_ele>
<sense><pos>noun (common) (futsuumeishi)</pos><gloss>red</gloss></sense>
<sense><stagr>せきしょく</stagr><gloss>communism</gloss></sense>
</entry><entry><ent_seq>2</ent_seq><k_ele><keb>毎秒</keb></k_ele><r_ele><reb>まいびょう</reb></r_ele>
<sense><pos>adverbial noun (fukushitekimeishi)</pos><gloss>every second</gloss></sense></entry></JMdict>"""

    def test_lookup(self):
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
            f.write(self.XML)
        self.addCleanup(os.unlink, f.name)
        idx = jmdict.load(f.name)
        self.assertEqual([s["gloss"] for s in jmdict.lookup(idx, "赤色", "あかいろ")], [["red"]])
        self.assertEqual(len(jmdict.lookup(idx, "赤色", "セキショク")), 2)  # katakana reading folds
        self.assertEqual(jmdict.map_pos(jmdict.lookup(idx, "毎秒", "まいびょう")[0]["pos"]), "noun")


class BuildTest(unittest.TestCase):
    def test_spans_prefer_standalone_occurrence(self):
        links = [{"id": "a", "surface": "振動"}, {"id": "b", "surface": "加工振動"}]
        spans = build.place_spans("加工振動の判定では、空転時の振動を", links)
        self.assertEqual(spans, {"b": [0, 4], "a": [14, 16]})

    def test_anki_ruby(self):
        pairs = [["写真", "しゃしん"], ["家"], ["の"], ["写真集", "しゃしんしゅう"], ["を"]]
        self.assertEqual(build.anki_ruby(pairs), "写真[しゃしん]家の 写真集[しゃしんしゅう]を")
        self.assertEqual(build.anki_ruby(pairs, (4, 7)), "写真[しゃしん]家の<b> 写真集[しゃしんしゅう]</b>を")

    def test_segments_use_term_furigana_and_cover_sentence(self):
        terms = {"t1": {"furigana": [["経時", "けいじ"]]}}
        ja = "経時変化を見る。"
        segs = build.sentence_segments(ja, {"t1": [0, 2]}, terms)
        self.assertEqual(segs[0], ["経時", "けいじ"])  # the term's own (corrected) reading wins
        self.assertEqual("".join(p[0] for p in segs), ja)


if __name__ == "__main__":
    unittest.main()
