// Astro settings. Docs: https://docs.astro.build/en/reference/configuration-reference/
import { defineConfig } from "astro/config";

export default defineConfig({
  // GitHub Pages serves the site at https://yoyoyosiie.github.io/joshi_no_jisho/,
  // so every link has to start with /joshi_no_jisho/. Use the `url()` helper
  // in src/lib/dict.ts instead of writing paths by hand.
  site: "https://yoyoyosiie.github.io",
  base: "/joshi_no_jisho",
});
