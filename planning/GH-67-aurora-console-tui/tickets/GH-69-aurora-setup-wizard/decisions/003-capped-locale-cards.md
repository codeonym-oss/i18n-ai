# 003: The targets as capped locale cards, filtered by search and chips; no native names

**Date:** 2026-11-11 (ticket pass, Q3; agreed: "ok", to the recommended option 1)

**Question:** what does a locale card show, and how do CLDR's 323 locales fit, when Textual mounts each card as a
widget and 80 columns hold two?

**Found:** `LocaleView` holds a code, a name and a direction, no native name; the scan gives each existing locale's
coverage, and the source's message count is what a new one needs.

**Decision:** **cards for what is shown, at most 24 mounted.**

- The search and the chips filter: **All**, **In the tree · n**, **Right to left**, **Picked · n**. Unfiltered, the
  tree's locales and the picked ones come first (the order of `locale_choices` today); past 24, a last line says
  "+N more · type to narrow".
- A card: the code, an RTL/LTR tag, the name, and its state, "in tree · 62% done" or "new · 75 messages". No native
  name.
- Space or Enter on the focused card toggles it, and a click does; a picked card is checked and outlined.
- Four columns from 120 columns, two below (story decision 002).
- The "This run" panel beside the steps shows the picked locales as chips and the plan's files, locales and
  messages.

- **Why:** the design's grid without mounting 323 widgets, and nothing new underneath (the story's rule).
- **Not chosen:** native names (a field added to `ListLocalesQuery`'s view for one line of text); a styled
  `SelectionList` (scales for free, but not the cards of the design).
