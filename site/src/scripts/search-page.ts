// Wires up the search page: input, filters, results list, "add to list".
import { listPicker } from "./lists";
import { load, save } from "./prefs";
import { search, type Entry } from "./search";
import { el, getJSON, t, url, lang } from "./ui";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const q = $<HTMLInputElement>("q");
const drafts = $<HTMLInputElement>("drafts");
const results = $<HTMLUListElement>("results");
const tagBoxes = [...document.querySelectorAll<HTMLInputElement>('input[name="tag"]')];

const entries = await getJSON<Entry[]>("search-index.json");

// Restore the query/tags from the address bar (?q=…&tag=…) and the drafts choice from last time.
const params = new URLSearchParams(location.search);
q.value = params.get("q") ?? "";
const fromUrl = new Set(params.getAll("tag"));
tagBoxes.forEach((b) => (b.checked = fromUrl.has(b.value)));
if (fromUrl.size) $<HTMLDetailsElement>("tag-filter").open = true;
drafts.checked = load("jisho.showDrafts", false);

function selectedTags(): Set<string> {
  return new Set(tagBoxes.filter((b) => b.checked).map((b) => b.value));
}

function render(): void {
  const tags = selectedTags();
  const { hits, hiddenDrafts } = search(entries, { query: q.value, tags, drafts: drafts.checked });

  results.replaceChildren(
    ...hits.slice(0, 300).map((e) =>
      el("li", {},
        el("input", { type: "checkbox", value: e.id, ariaLabel: e.ja }),
        el("a", { href: url(`${lang}/t/${e.id}/`) },
          el("span", { class: "ja", lang: "ja" }, e.ja),
          el("span", { class: "reading", lang: "ja" }, e.reading),
          ...(e.draft ? [el("span", { class: "badge draft" }, t("term.draft"))] : []),
          el("span", { class: "gloss" }, e.en.slice(0, 4).join(", ") || "—"),
        ),
      ),
    ),
  );
  $("count").textContent = t("search.count", { n: hits.length });
  const note = $("note");
  note.hidden = hits.length > 0 && !hiddenDrafts;
  note.textContent = hiddenDrafts ? t("search.drafts_hidden", { n: hiddenDrafts }) : t("search.no_results");
  $<HTMLInputElement>("select-all").checked = false;

  const tc = $("tag-count");
  tc.hidden = !tags.size;
  tc.textContent = String(tags.size);

  // Keep the address bar in sync so a search can be bookmarked or shared.
  const p = new URLSearchParams();
  if (q.value) p.set("q", q.value);
  tags.forEach((tag) => p.append("tag", tag));
  history.replaceState(null, "", p.size ? `?${p}` : location.pathname);
}

q.addEventListener("input", render);
drafts.addEventListener("change", () => {
  save("jisho.showDrafts", drafts.checked);
  render();
});
tagBoxes.forEach((b) => b.addEventListener("change", render));
$("clear-tags").addEventListener("click", () => {
  tagBoxes.forEach((b) => (b.checked = false));
  render();
});
$<HTMLInputElement>("select-all").addEventListener("change", (ev) => {
  const on = (ev.target as HTMLInputElement).checked;
  results.querySelectorAll<HTMLInputElement>("input[type=checkbox]").forEach((b) => (b.checked = on));
});
listPicker($<HTMLSelectElement>("bulk-add"), () =>
  [...results.querySelectorAll<HTMLInputElement>("input[type=checkbox]:checked")].map((b) => b.value),
);

render();
