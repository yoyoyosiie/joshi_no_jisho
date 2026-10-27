# data/

This folder **is** the dictionary. Every term and sentence is a small YAML file
you can edit in any text editor (or right on GitHub with the pencil icon).
`python tools/validate.py` checks it; CI runs the same check on every PR.

| Path | What | Format |
| --- | --- | --- |
| `terms/t000123.yaml` | One term | `schema/term.schema.json` |
| `sentences/s000045.yaml` | One example sentence, shared by every term it mentions | `schema/sentence.schema.json` |
| `tags.yaml` | The only tags allowed, as a tree (`parent`) | `schema/tags.schema.json` |
| `lists/*.yaml` | Curated study lists (Phase 2) | `schema/list.schema.json` |
| `i18n/en.yaml`, `i18n/ja.yaml` | Website UI text; both need the same keys | `schema/i18n.schema.json` |

## Reviewing a draft term

Everything imported starts as `status: draft`. To review one:

1. Check `reading` (Sudachi sometimes guesses wrong, e.g. 経時 is けいじ, not きょうじ)
   and `furigana` (fill it in if it's `null`, e.g. `[[難, なん], [削性, さくせい]]`).
2. Fix the English in `senses[].en`. JMdict glosses (`en_by: jmdict`) are general
   dictionary meanings: 加工 comes in as "manufacturing, processing", but in a
   machining context you may want "machining". Set `en_by: human` once you've edited them.
3. Set `pos` and add at least one tag from `tags.yaml`.
4. Optionally add `def_en` (a one-line definition) and `def_ja`.
5. Change `status: draft` to `status: reviewed`. The validator then requires
   glosses and a tag on every sense.

A term with two technical meanings (ピッチ: thread pitch / blade pitch) gets two
items under `senses`.

## Linking sentences

A sentence lists the terms it contains under `terms`, with `surface` = the exact
text in the sentence. That is the only place the link is stored: term pages
find their sentences at build time. To add a translation, fill `en` and set
`en_by` (`human`, `machine`, or `source`).

## Ids

Ids (`t000123`, `s000045`) never change and are never reused, even if you delete
a term. The Anki export uses the term id to update cards instead of
duplicating them.
