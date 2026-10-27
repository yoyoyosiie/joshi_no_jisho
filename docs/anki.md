# Anki export

The site's **My lists → Download for Anki** button saves a list as a text file
Anki can import. It's made to match your existing deck (dark card, salmon
highlight; see `anki-card-reference-*.png`).

You set up the note type **once**; after that every export just imports.

## 1. Create the note type (once)

1. In Anki: **Tools → Manage Note Types → Add → "Add: Basic"**, name it exactly
   `ジョシの辞書` (the export file asks for that name).
2. Select it, click **Fields…**, and make these 10 fields, in this order
   (rename Front/Back to the first two, then add the rest):

   `Term` · `TermFurigana` · `Reading` · `Gloss` · `Sentence` · `SentenceFurigana` · `SentenceEN` · `POS` · `Tag` · `Source`

3. Click **Cards…** and paste the three boxes below into Front Template,
   Back Template and Styling.

### Front template

```html
<div class="term">{{Term}}</div>
<div class="sentence">{{Sentence}}</div>
```

### Back template

```html
<div class="term">{{furigana:TermFurigana}}</div>
<div class="reading">{{Reading}}</div>
<div class="gloss">{{Gloss}}</div>
<hr>
<div class="sentence">{{furigana:SentenceFurigana}}</div>
<div class="en">{{SentenceEN}}</div>
<div class="side">{{POS}}{{#Tag}}<br>{{Tag}}{{/Tag}}</div>
<div class="source">{{Source}}</div>
```

### Styling

```css
.card {
  font-family: "Noto Sans JP", "Hiragino Sans", "Yu Gothic UI", sans-serif;
  text-align: center;
  color: #ececec;
  background: #1f1f21;
  font-size: 22px;
  line-height: 1.6;
}
.term { font-size: 64px; font-weight: 700; margin-top: 24px; }
.reading, .gloss { font-size: 28px; margin-top: 8px; }
.sentence { font-size: 30px; margin-top: 16px; }
.en { color: #b8b8be; font-size: 22px; margin-top: 8px; }
b, b rt { color: #ff6b61; }          /* the target term */
rt { font-size: 0.45em; color: #c8c8cc; }
hr { border: 0; border-top: 1px solid #77777c; width: 85%; margin: 24px auto; }
.side { display: inline-block; text-align: left; border-left: 2px solid #55555a;
        padding-left: 14px; margin-top: 20px; color: #c8c8cc; font-size: 18px; }
.source { color: #85858b; font-size: 14px; margin-top: 20px; }
```

## 2. Import a list

**File → Import**, pick the downloaded `.txt`. The file's header lines tell
Anki the separator, note type and deck (`ジョシの辞書::<list name>`), so the
defaults on the import screen are right; just click **Import**.

**Re-importing is safe.** Each card's ID is the term's ID (`t000123`), so when
a term gets corrected on the site, exporting and importing again *updates* the
card in place and keeps your review history. Make sure "Existing notes" on the
import screen is set to **Update**.

## The fields

| Field | Example | Notes |
| --- | --- | --- |
| Term | 振動 | Headword. |
| TermFurigana | `振動[しんどう]` | Anki furigana syntax; `{{furigana:…}}` shows it as ruby, `{{kanji:…}}` hides it. |
| Reading | しんどう | |
| Gloss | oscillation, vibration | Senses separated by `;`. |
| Sentence | `…の<b>振動</b>を…` | First example sentence (or the term's `card_sentence`), target term in `<b>`. |
| SentenceFurigana | `… <b> 振動[しんどう]</b>を…` | Same sentence with readings. Readings of other words are Sudachi's guesses. |
| SentenceEN | | Blank until someone translates the sentence. |
| POS | suru-noun | First sense. |
| Tag | 機械工学 | Top-level field of the first tag. |
| Source | patent WO2021/079959 · no translation yet | Where the sentence is from and who translated it. |

Phase 2 will add a ready-made `.apkg` with this note type built in, so step 1 goes away.
