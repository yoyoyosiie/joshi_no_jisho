// Anki export: one tab-separated file Anki can import directly.
// The note type it expects is described in docs/anki.md.

export const FIELDS = [
  "Term", "TermFurigana", "Reading", "Gloss", "Sentence",
  "SentenceFurigana", "SentenceEN", "POS", "Tag", "Source",
] as const;

export type AnkiRows = Record<string, Record<string, string>>; // term id -> field -> value

/**
 * Build the file. The lines starting with # tell Anki how to read it
 * (https://docs.ankiweb.net/importing/text-files.html#file-headers).
 * The first column is the GUID = term id, so importing again *updates* the
 * existing cards instead of making duplicates (your review history is kept).
 */
export function ankiFile(ids: string[], rows: AnkiRows, deck: string): string {
  const header = [
    "#separator:Tab",
    "#html:true",
    "#notetype:ジョシの辞書",
    `#deck:${deck.replace(/[\t\n]/g, " ")}`,
    "#guid column:1",
    `#columns:GUID\t${FIELDS.join("\t")}`,
  ];
  const lines = ids
    .filter((id) => rows[id])
    .map((id) => [id, ...FIELDS.map((f) => rows[id][f] ?? "")].join("\t"));
  return [...header, ...lines].join("\n") + "\n";
}
