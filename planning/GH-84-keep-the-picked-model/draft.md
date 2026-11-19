# Giving a key in the TUI's setup clears the picked model

## Problem

In the setup's Model step, giving the provider's key lists the models again (`SetupScreen._give_key` →
`_list_models`), and `_fill` resets `#model` to the default: a model picked before the key is lost. A run started
with a key typed in the form does the same as it starts, so back from the run the setup has no model.

## The change

When the models are listed again after a key, keep the model picked before if the new list has it; else the
default, as today. A provider picked anew still starts from its default.

## Done when

- [ ] The model-card test in its natural order: pick the model, then give the key; the card still names it.
- [ ] The run's stop test no longer picks the model again after Back.

Takes up the follow-up `planning/GH-67-aurora-console-tui/follow-ups/2026-11-11_1434_key-clears-the-picked-model.md`.
