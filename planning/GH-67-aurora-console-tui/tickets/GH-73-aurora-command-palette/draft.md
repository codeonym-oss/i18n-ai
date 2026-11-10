# Search commands, locales and files in the Aurora palette

## Problem

`Ctrl+P` opens Textual's stock palette: the screens' commands mixed with Textual's own, themes included.

## The change

- v2's palette: grouped results (commands, go to, files), each with its glyph, hint and key.
- Prefixes: `>` commands, `@` locales, `#` files of the tree Home shows; no prefix searches all.
- Only i18n-ai's commands; Textual's stock ones (themes, screenshots) are gone (story decision 003).

## For the ticket pass

- How the prefixes plug into Textual's command providers; what choosing a locale or a file does.

## Done when

- [ ] `Pilot` tests: each prefix narrows the results, and running a command does what its key does.
- [ ] Snapshots at 160×45 and 80×24.
