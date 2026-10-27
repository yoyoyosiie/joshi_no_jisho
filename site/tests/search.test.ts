// Tests for the search box logic. Run: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { romajiVariants, search, type Entry } from "../src/scripts/search.ts";

const entry = (id: string, ja: string, reading: string, en: string[], extra: Partial<Entry> = {}): Entry =>
  ({ id, ja, alt: [], reading, en, defs: "", tags: [], draft: false, ...extra });

const entries = [
  entry("t1", "加工", "かこう", ["machining", "processing"], { tags: ["machining", "manufacturing", "mech-eng"] }),
  entry("t2", "加工振動", "かこうしんどう", ["machining vibration", "chatter"]),
  entry("t3", "振動", "しんどう", ["vibration"], { tags: ["vibration", "dynamics", "mech-eng"] }),
  entry("t4", "ハウジング", "ハウジング", ["housing"]),
  entry("t5", "工具", "こうぐ", ["tool"], { draft: true }),
];
const ids = (query: string, extra: { tags?: string[]; drafts?: boolean } = {}) =>
  search(entries, { query, tags: new Set(extra.tags ?? []), drafts: extra.drafts ?? false }).hits.map((e) => e.id);

test("kanji is a substring search, exact match first", () => {
  assert.deepEqual(ids("振動"), ["t3", "t2"]);
});

test("hiragana and katakana find each other", () => {
  assert.deepEqual(ids("はうじんぐ"), ["t4"]);
  assert.deepEqual(ids("カコウ"), ["t1", "t2"]);
});

test("romaji: kakou, kakoo and kakō all find かこう", () => {
  for (const q of ["kakou", "kakoo", "kakō", "KAKOU"]) assert.deepEqual(ids(q), ["t1", "t2"], q);
  assert.ok(romajiVariants("ookii").includes("おおきい"));
});

test("English matches the start of words in glosses", () => {
  assert.deepEqual(ids("vibration"), ["t3", "t2"]);
  assert.deepEqual(ids("chat"), ["t2"]);
  assert.deepEqual(ids("ibration"), []);
});

test("a parent tag includes its children's terms", () => {
  assert.deepEqual(ids("", { tags: ["mech-eng"] }).sort(), ["t1", "t3"]);
  assert.deepEqual(ids("", { tags: ["vibration"] }), ["t3"]);
});

test("drafts are hidden unless asked for, and counted", () => {
  assert.deepEqual(ids("tool"), []);
  assert.equal(search(entries, { query: "tool", tags: new Set(), drafts: false }).hiddenDrafts, 1);
  assert.deepEqual(ids("tool", { drafts: true }), ["t5"]);
});
