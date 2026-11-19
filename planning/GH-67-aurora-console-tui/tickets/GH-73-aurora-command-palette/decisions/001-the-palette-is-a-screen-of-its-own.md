# 001: The palette is a screen of i18n-ai's own, not Textual's providers

**Date:** 2026-11-19 (ticket pass, Q1; taken as recommended after the person asked to "finish all the remaining tasks", no answer given to the question itself)

**Question:** how do v2's grouped results and the `>`, `@`, `#` prefixes plug into Textual?

**Decision:** **a modal `PaletteScreen` in `kit/palette.py`** that the app's `command_palette` action opens (`Ctrl+P`
and the command bar's ⌕). An input on top, then the results in an `OptionList`: a header per group (COMMANDS,
GO TO, FILES), each result its glyph, its title with the matched letters lit (Textual's `Matcher`), its hint and its
key. A prefix keeps one group and searches the rest of the text; no prefix searches all three. `↑`/`↓` move,
`enter` runs the highlighted one, `escape` closes. Textual's `CommandPalette` is no longer opened.

- **Why:** Textual's providers return one list sorted by score, with no group headers, and the palette's look is
  Textual's; a screen of our own is short, styled in `aurora.tcss`, and tested with `Pilot` like the others.
- **Not chosen:** Textual's `CommandPalette` with three providers (no groups; prefixes parsed in each provider,
  its stock commands to filter out).
