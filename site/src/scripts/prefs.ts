// Small settings remembered in this browser (localStorage).
// localStorage can be missing or blocked (private windows, strict settings),
// so every access is wrapped in try/catch and the site works without it.

export function load<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : (JSON.parse(v) as T);
  } catch {
    return fallback;
  }
}

export function save(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable: setting just isn't remembered */
  }
}

export const setLang = (lang: string) => save("jisho.lang", lang);
export const getLang = () => load<string | null>("jisho.lang", null);
