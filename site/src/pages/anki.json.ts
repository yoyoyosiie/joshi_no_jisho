// Served as /anki.json: the Anki fields for every term (computed by tools/build.py).
import { dict } from "../lib/dict";

export function GET() {
  const rows = Object.fromEntries(dict.terms.map((t) => [t.id, t.anki]));
  return new Response(JSON.stringify(rows));
}
