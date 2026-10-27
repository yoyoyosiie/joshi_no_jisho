// Personal study lists, kept in this browser's localStorage (like playlists).
// Export/import as a small JSON file to back them up or move them.
import { load, save } from "./prefs";
import { el, t, toast } from "./ui";

export interface List {
  id: string;
  name: string;
  terms: string[]; // term ids, in the order they were added
}

const KEY = "jisho.lists";
const FORMAT = "joshi-no-jisho-list"; // marks our export files

export const getLists = (): List[] => load<List[]>(KEY, []);
const setLists = (lists: List[]) => save(KEY, lists);

export function createList(name: string): List {
  const list = { id: `l${Date.now().toString(36)}`, name: name.trim(), terms: [] };
  setLists([...getLists(), list]);
  return list;
}

/** Add terms to a list, skipping ones already in it. Returns how many were new. */
export function addTerms(listId: string, ids: string[]): number {
  const lists = getLists();
  const list = lists.find((l) => l.id === listId);
  if (!list) return 0;
  const fresh = ids.filter((id) => !list.terms.includes(id));
  list.terms.push(...fresh);
  setLists(lists);
  return fresh.length;
}

export function updateList(listId: string, change: (l: List) => void): void {
  const lists = getLists();
  const list = lists.find((l) => l.id === listId);
  if (list) change(list);
  setLists(lists);
}

export const deleteList = (listId: string) => setLists(getLists().filter((l) => l.id !== listId));

/** Save text as a file download. */
export function download(filename: string, text: string, type = "text/plain"): void {
  const a = el("a", { href: URL.createObjectURL(new Blob([text], { type })), download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

export function exportList(list: List): void {
  const data = { format: FORMAT, version: 1, name: list.name, terms: list.terms };
  download(`${list.name}.json`, JSON.stringify(data, null, 2), "application/json");
}

/** Read an exported list file and add it as a new list. Returns null if the file isn't one. */
export async function importList(file: File): Promise<List | null> {
  try {
    const data = JSON.parse(await file.text());
    if (data.format !== FORMAT || !Array.isArray(data.terms)) return null;
    const list = createList(String(data.name || file.name));
    addTerms(list.id, data.terms.filter((x: unknown) => typeof x === "string"));
    return list;
  } catch {
    return null;
  }
}

/**
 * Turn a <select> into an "Add to list…" picker.
 * `getIds` says which term ids to add when the reader picks a list.
 */
export function listPicker(select: HTMLSelectElement, getIds: () => string[]): void {
  const fill = () => {
    select.replaceChildren(
      el("option", { value: "", textContent: t("list.add_to") }),
      ...getLists().map((l) => el("option", { value: l.id, textContent: `${l.name} (${l.terms.length})` })),
      el("option", { value: "__new", textContent: t("list.new") }),
    );
  };
  fill();
  select.addEventListener("focus", fill); // pick up lists made in another tab
  select.addEventListener("change", () => {
    const choice = select.value;
    select.value = "";
    if (!choice) return;
    const ids = getIds();
    if (!ids.length) return toast(t("list.nothing_selected"));
    let list = getLists().find((l) => l.id === choice);
    if (choice === "__new") {
      const name = prompt(t("list.new_prompt"));
      if (!name?.trim()) return;
      list = createList(name);
    }
    if (!list) return;
    addTerms(list.id, ids);
    toast(t("list.added", { name: list.name }));
    fill();
  });
}
