# Attribution

ジョシの辞書 builds on other people's open data. Everything below is credited
here and will be credited on the site. Data in this repo is CC BY-SA 4.0
(see `LICENSE-DATA`), which these licenses allow.

## Used now

| Source | What we use | License | Notes |
| --- | --- | --- | --- |
| [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html), © Electronic Dictionary Research and Development Group | Draft English glosses (`en_by: jmdict` in a term's sense) | [CC BY-SA 4.0](https://www.edrdg.org/edrdg/licence.html) | The first import (2026-10-27) used the JMdict copy bundled in the `jamdict-data` 1.5 Python package (an older JMdict release), because edrdg.org was unreachable from the build sandbox. Future imports should use a current `JMdict_e.gz`. |
| [SudachiPy](https://github.com/WorksApplications/SudachiPy) + SudachiDict, Works Applications | Readings and furigana splits for imported terms | Apache 2.0 | Readings are auto-generated and can be wrong; every imported term is a draft. |
| Patent WO2021/079959 (WIPO) | Candidate terms and example sentences (`source.type: patent`) | Not verified | Patent text is used as short quoted examples. Reuse terms for patent publications have not been checked yet. |

## Planned (see docs/handoff.md section 7)

| Source | License |
| --- | --- |
| [KanjiVG](https://github.com/KanjiVG/kanjivg) (stroke order) | CC BY-SA 3.0 |
| [Kanjium](https://github.com/mifunetoshiro/kanjium) (pitch accent) | CC BY-SA 4.0 |
| [JmdictFurigana](https://github.com/Doublevil/JmdictFurigana) | Same as JMdict |
| [WanaKana](https://github.com/WaniKani/WanaKana) (romaji search) | MIT |
| Tatoeba (sentences) | CC BY 2.0 FR (verify before use) |

Not used, on purpose: OJAD, NHK / Shinmeikai accent dictionaries, Forvo,
commercial dictionary definitions, JIS standard text (no open license).
