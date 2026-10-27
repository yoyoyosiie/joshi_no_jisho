// Helpers shared by the browser scripts: UI strings, links, the toast message.

const strings: Record<string, string> = JSON.parse(document.getElementById("i18n")?.textContent || "{}");

/** UI string in the page's language, with {n}/{name} filled in. */
export function t(key: string, vars: Record<string, string | number> = {}): string {
  return (strings[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`));
}

export const lang = document.body.dataset.lang as "en" | "ja";
const base = (document.body.dataset.base || "/").replace(/\/$/, "");

/** A link inside the site (adds the GitHub Pages base path). */
export const url = (path: string) => `${base}/${path.replace(/^\//, "")}`;

let timer: number | undefined;
/** Show a short message at the bottom of the screen. */
export function toast(msg: string): void {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(timer);
  timer = window.setTimeout(() => el.classList.remove("show"), 2500);
}

/** Create an element without innerHTML, so text from the data can never inject HTML. */
export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Partial<HTMLElementTagNameMap[K]> & { class?: string } = {},
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  const { class: cls, ...rest } = props;
  if (cls) node.className = cls;
  Object.assign(node, rest);
  node.append(...children);
  return node;
}

/** Fetch one of the JSON files the site generates (search-index.json, anki.json). */
export async function getJSON<T>(name: string): Promise<T> {
  const res = await fetch(url(name));
  return res.json() as Promise<T>;
}
