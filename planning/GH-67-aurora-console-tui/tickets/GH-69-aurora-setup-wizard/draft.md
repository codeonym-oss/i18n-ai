# Set up a TUI run as the Aurora wizard

## Problem

The setup is one long stock form: the tree, the source, the targets, the output, the provider, the model and the
key, all at once.

## The change

- In the Run mode, the setup becomes v2's wizard, built on the kit (story decision 003): three steps, **Tree**,
  **Targets** and **Model**, with today's fields and no options step (decision 001), on one screen whose steps
  switch in place: a chip opens its step, Continue the next, Esc the previous, ⌃R plans from any of them
  (decision 002).
- **Targets** as locale cards: the code, the direction, the name, and what each would need ("in tree · 62% done",
  "new · 75 messages"), filtered by a search and by chips (In the tree, Right to left, Picked), at most 24 shown
  (decision 003).
- **Model:** the provider and model selects under a model card saying the provider, the model and the key's state
  (decision 004).
- A **This run** panel beside the steps: the picked locales, the plan's files, locales and messages, the model card,
  and the recorded fallbacks.
- It starts on the tree Home shows (story decision 005), with the last answers as defaults, as today, and opens on
  Targets once the tree is scanned, on Tree when the tree or its source must be given (decision 005).
- Same queries and the same result as the form today: it ends on the plan screen.

## Not part of it

- The run's options (overwrite, classify, context) in the TUI; strict stays out (GH-15 decision 003).
- Native locale names on the cards.

## Done when

- [ ] The setup's `Pilot` tests carried over and passing: a run set up through the wizard reaches the plan.
- [ ] Snapshots of each step at 160×45 and 80×24.
