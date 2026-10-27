// The search box: one input that understands kanji, kana, romaji and English.
// Pure functions only (no page access), so it's easy to test and reason about.
import { isKana, toHiragana } from "wanakana";

export interface Entry {
  id: string;
  ja: string;
  alt: string[];
  reading: string;
  en: string[];
  defs: string;
  tags: string[];
  draft: boolean;
}

const KANJI = /[㐀-鿿々]/;

/** カタカナ -> ひらがな, so ハウジング and はうじんぐ compare equal. */
export const kataToHira = (s: string) =>
  s.replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));

/**
 * Romaji the reader might type, as kana: kakou / kakoo / kakō all give かこう.
 * Long vowels are ambiguous (おおきい is "ookii"), so every variant is tried.
 */
export function romajiVariants(q: string): string[] {
  // Each macron vowel can be spelled two ways in kana (ō = おう or おお, ē = えい or ええ).
  const long: [RegExp, string, string][] = [[/ā/g, "aa", "aa"], [/ī/g, "ii", "ii"], [/ū/g, "uu", "uu"],
    [/ē/g, "ei", "ee"], [/[ōô]/g, "ou", "oo"]];
  const a = long.reduce((s, [re, x]) => s.replace(re, x), q);
  const b = long.reduce((s, [re, , y]) => s.replace(re, y), q);
  const out = new Set([a, b, a.replace(/oo/g, "ou")]);
  return [...out].map((v) => toHiragana(v)).filter((k) => isKana(k));
}

/** How well `hay` matches `needle`: exact 3, starts with 2, contains 1, else 0. */
function grade(hay: string, needle: string): number {
  if (!needle || !hay.includes(needle)) return 0;
  return hay === needle ? 3 : hay.startsWith(needle) ? 2 : 1;
}

/** English: a gloss equal to the query, or containing it at the start of a word. */
function gradeEnglish(texts: string[], q: string): number {
  let best = 0;
  const wordStart = new RegExp(`(^|[^a-z])${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`);
  for (const x of texts) {
    const s = x.toLowerCase();
    if (s === q || s.replace(/\s*\(.*?\)\s*/g, "") === q) best = Math.max(best, 3);
    else if (s.startsWith(q)) best = Math.max(best, 2);
    else if (wordStart.test(s)) best = Math.max(best, 1.5);
  }
  return best;
}

/** Score one entry for a query (0 = no match). Higher = better. */
export function score(e: Entry, raw: string): number {
  const q = raw.normalize("NFKC").trim().toLowerCase();
  if (!q) return 1;
  const reading = kataToHira(e.reading.toLowerCase());
  const written = [e.ja, ...e.alt].map((w) => kataToHira(w.toLowerCase()));
  let best = 0;

  if (KANJI.test(q)) {
    // Kanji: substring of the headword or another spelling (振動 finds 加工振動).
    for (const w of written) best = Math.max(best, grade(w, kataToHira(q)) * 10);
    return best;
  }
  if (isKana(q)) {
    const k = kataToHira(q);
    best = Math.max(best, grade(reading, k) * 10, ...written.map((w) => grade(w, k) * 10));
    return best;
  }
  // Latin letters: could be romaji (kakou) or English (vibration). Try both.
  for (const k of romajiVariants(q)) {
    const g = grade(reading, k);
    // Mid-word romaji hits only count for 3+ kana, so English like "time" (ちめ) doesn't match noise.
    if (g >= 2 || (g === 1 && k.length >= 3)) best = Math.max(best, g * 9);
  }
  best = Math.max(best, gradeEnglish(e.en, q) * 10);
  if (!best && q.length > 2 && gradeEnglish([e.defs], q)) best = 5; // definitions rank last
  // Headwords with Latin letters in them (NC装置) match too.
  best = Math.max(best, ...written.map((w) => grade(w, q) * 8));
  return best;
}

export interface Filters {
  query: string;
  tags: Set<string>; // selected tag ids; empty = all
  drafts: boolean;   // include draft terms
}

/** Run a search. Returns matches in order, plus how many drafts were hidden. */
export function search(entries: Entry[], f: Filters): { hits: Entry[]; hiddenDrafts: number } {
  const scored: { e: Entry; s: number }[] = [];
  let hiddenDrafts = 0;
  for (const e of entries) {
    if (f.tags.size && !e.tags.some((t) => f.tags.has(t))) continue;
    const s = score(e, f.query);
    if (!s) continue;
    if (e.draft && !f.drafts) {
      hiddenDrafts++;
      continue;
    }
    scored.push({ e, s });
  }
  // Best score first; ties in dictionary (reading) order.
  scored.sort((a, b) => b.s - a.s || kataToHira(a.e.reading).localeCompare(kataToHira(b.e.reading), "ja"));
  return { hits: scored.map((x) => x.e), hiddenDrafts };
}
