# 003: The setup is one form

**Date:** 2026-10-26 (ticket pass, Q3; picked "One form (Recommended)" from three sketches)

**Question:** how is the setup screen laid out?

**Decision:** **one scrolling form in two groups**, Tree (locale tree, source, targets with search, output) and
Model (provider, model, key). A field waits, greyed, until what it depends on is set: the tree gives the source and
the locales, the provider the models and the key. A line beside **Run** says the files and locales; `Ctrl+R` runs,
`Ctrl+P` opens the palette, `q` quits.

```
┌ i18n-ai ─ setup ─────────────── laravel preset ┐
│ Tree                                           │
│  Locale tree  [ lang  (laravel preset)     ▾]  │
│  Source       [ en (the keys of fr.json)   ▾]  │
│  Targets      [ de, es           search… ]     │
│               ☑ fr · in the tree  ☑ de  ☐ es   │
│  Output       [ beside the source          ▾]  │
│ Model                                          │
│  Provider     [ openai  (key set)          ▾]  │
│  Model        [ gpt-4.1-mini · recommended ▾]  │
│  Key          ✓ set (keyring)                  │
│           [ Run ]   12 files · 2 locales       │
└ ^r run  ^p palette  q quit ────────────────────┘
```

- **Why:** everything visible and editable at once, as #15 asks ("as a form").
- **Not chosen:** a stepper of pages (the prompts again, with more screens to build); fields beside a live precheck
  (crowds a narrow terminal, and is the plan screen's job, #31).
