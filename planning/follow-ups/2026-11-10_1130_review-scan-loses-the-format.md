---
status: open
from: agent
found-while: GH-62
resolved-by:
---

# The review's scan can refuse a mixed tree that `generate` reads

`ListFallbacksQueryHandler.handle` (`src/i18n_ai/application/intents/locale/queries/list_fallbacks/handler.py`)
scans `replace(query.tree, include=(), exclude=())`. In a directory layout the scanner settles the format after
`--include` and `--exclude`, so when a filter is what leaves a tree that mixes formats (JSON and YAML) with one, the
review's scan raises `MixedLocaleFormats` where the run itself worked.

GH-62 fixed the same scan in `generate` by keeping the format read (`format=tree.format`, its impl.md, "Corrections
while building"). Left for later because it predates GH-62 and only the review shows it.

Fixing it: scan with the format of the filtered tree, as `generate` does, with a test on a mixed tree whose YAML
files are excluded.
