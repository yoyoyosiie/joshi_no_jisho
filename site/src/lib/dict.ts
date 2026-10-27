// Server-side helpers: load the dictionary that tools/build.py wrote and
// answer the questions pages ask. Runs at build time only, never in the browser.
import raw from "../data/dict.json";

export type Pair = [string] | [string, string]; // [text] or [text, reading]

export interface Sense {
  pos: string;
  en: string[];
  en_by?: string | null;
  def_en?: string | null;
  def_ja?: string | null;
  tags?: string[];
}

export interface Term {
  id: string;
  ja: string;
  alt?: string[];
  reading: string;
  furigana?: Pair[] | null;
  pitch?: { value: number | null; source: string | null; verified: boolean };
  senses: Sense[];
  sources: string[];
  added: string;
  status: "draft" | "reviewed";
  sentences: string[];
  card: string | null;
  tags_all: string[];
  anki: Record<string, string>;
}

export interface Sentence {
  id: string;
  ja: string;
  en: string | null;
  en_by: "human" | "machine" | "source" | null;
  source: { type: string; ref: string | null; url?: string | null; license?: string | null };
  terms: { id: string; surface: string }[];
  spans: Record<string, [number, number]>;
  segs: Pair[];
}

export interface Tag {
  id: string;
  ja: string;
  en: string;
  parent?: string | null;
}

export interface CuratedList {
  id: string;
  name: { en: string; ja: string };
  description?: { en: string; ja: string };
  terms: string[];
}

interface Dict {
  terms: Term[];
  sentences: Record<string, Sentence>;
  tags: Tag[];
  lists: CuratedList[];
  i18n: Record<string, Record<string, string>>;
}

export const dict = raw as unknown as Dict;
export const LANGS = ["en", "ja"] as const;
export type Lang = (typeof LANGS)[number];

export const termById = new Map(dict.terms.map((t) => [t.id, t]));
export const tagById = new Map(dict.tags.map((t) => [t.id, t]));

/** UI string for a key, with {n}/{name} placeholders filled from `vars`. */
export function t(lang: Lang, key: string, vars: Record<string, string | number> = {}): string {
  const s = dict.i18n[lang]?.[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`));
}

/** A link inside the site. Adds the /joshi_no_jisho base so links work on GitHub Pages. */
export function url(path: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return `${base}/${path.replace(/^\//, "")}`;
}

/** Furigana for a headword, falling back to the whole reading over the whole word. */
export function headwordPairs(term: Term): Pair[] {
  if (term.furigana) return term.furigana;
  return /[一-鿿々]/.test(term.ja) ? [[term.ja, term.reading]] : [[term.ja]];
}

/** Tag tree: children of a tag (or the roots when id is null), in tags.yaml order. */
export function tagChildren(id: string | null): Tag[] {
  return dict.tags.filter((t) => (t.parent ?? null) === id);
}

export function tagName(id: string, lang: Lang): string {
  const tag = tagById.get(id);
  return tag ? tag[lang] : id;
}

export const POS_NAMES: Record<string, { en: string; ja: string }> = {
  noun: { en: "noun", ja: "名詞" },
  "suru-noun": { en: "noun, する verb", ja: "名詞・サ変" },
  verb: { en: "verb", ja: "動詞" },
  "i-adj": { en: "い-adjective", ja: "形容詞" },
  "na-adj": { en: "な-adjective", ja: "形容動詞" },
  adverb: { en: "adverb", ja: "副詞" },
  expression: { en: "expression", ja: "表現" },
  prefix: { en: "prefix", ja: "接頭辞" },
  suffix: { en: "suffix", ja: "接尾辞" },
  counter: { en: "counter", ja: "助数詞" },
  other: { en: "other", ja: "その他" },
};

export const REPO = "https://github.com/yoyoyosiie/joshi_no_jisho";
