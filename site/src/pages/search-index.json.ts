// Served as /search-index.json: just what the search box needs, nothing more.
import { dict } from "../lib/dict";

export function GET() {
  const entries = dict.terms.map((t) => ({
    id: t.id,
    ja: t.ja,
    alt: t.alt ?? [],
    reading: t.reading,
    en: t.senses.flatMap((s) => s.en),
    defs: t.senses.map((s) => s.def_en ?? "").join(" "),
    tags: t.tags_all,
    draft: t.status === "draft",
  }));
  return new Response(JSON.stringify(entries));
}
