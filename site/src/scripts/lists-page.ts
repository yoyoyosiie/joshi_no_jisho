// Fills in the "My lists" page from localStorage.
import { ankiFile, type AnkiRows } from "./anki";
import { deleteList, download, exportList, getLists, importList, updateList, type List } from "./lists";
import type { Entry } from "./search";
import { el, getJSON, lang, t, toast, url } from "./ui";

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const which = $<HTMLSelectElement>("which");
const entries = new Map((await getJSON<Entry[]>("search-index.json")).map((e) => [e.id, e]));
let anki: AnkiRows | null = null; // loaded the first time someone exports

const current = (): List | undefined => getLists().find((l) => l.id === which.value);

function render(selectId?: string): void {
  const lists = getLists();
  which.replaceChildren(...lists.map((l) => el("option", { value: l.id, textContent: `${l.name} (${l.terms.length})` })));
  if (selectId) which.value = selectId;
  $("empty").hidden = lists.length > 0;
  $("current").hidden = lists.length === 0;
  which.hidden = lists.length === 0;

  const list = current();
  if (!list) return;
  $("terms").replaceChildren(
    ...(list.terms.length ? [] : [el("li", { class: "muted" }, t("lists.list_empty"))]),
    ...list.terms.map((id) => {
      const e = entries.get(id);
      const remove = el("button", { class: "small", textContent: t("lists.remove") });
      remove.addEventListener("click", () => {
        updateList(list.id, (l) => (l.terms = l.terms.filter((x) => x !== id)));
        render(list.id);
      });
      return el("li", {},
        el("a", { href: url(`${lang}/t/${id}/`), lang: "ja" }, e?.ja ?? id),
        el("span", { lang: "ja" }, e?.reading ?? ""),
        el("span", { class: "gloss" }, e?.en.slice(0, 3).join(", ") ?? ""),
        remove,
      );
    }),
  );
}

async function exportAnki(name: string, ids: string[]): Promise<void> {
  anki ??= await getJSON<AnkiRows>("anki.json");
  // Each list becomes a sub-deck: ジョシの辞書::<list name>
  download(`${name}.anki.txt`, ankiFile(ids, anki, `ジョシの辞書::${name}`));
}

which.addEventListener("change", () => render(which.value));
$("anki").addEventListener("click", () => {
  const l = current();
  if (l) void exportAnki(l.name, l.terms);
});
$("export").addEventListener("click", () => {
  const l = current();
  if (l) exportList(l);
});
$("rename").addEventListener("click", () => {
  const l = current();
  const name = l && prompt(t("lists.rename"), l.name);
  if (l && name?.trim()) {
    updateList(l.id, (x) => (x.name = name.trim()));
    render(l.id);
  }
});
$("delete").addEventListener("click", () => {
  const l = current();
  if (l && confirm(t("lists.delete_confirm", { name: l.name }))) {
    deleteList(l.id);
    render();
  }
});
$<HTMLInputElement>("import").addEventListener("change", async (ev) => {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  const list = await importList(file);
  if (!list) return toast(t("lists.import_failed"));
  render(list.id);
});
document.querySelectorAll<HTMLButtonElement>(".curated-anki").forEach((b) =>
  b.addEventListener("click", () => void exportAnki(b.dataset.name!, b.dataset.ids!.split(","))),
);

render();
