---
status: open
from: agent
found-while: GH-69
resolved-by:
---

# Giving a key clears the picked model

In the setup's Model step, giving the provider's key fetches the models again (`_give_key` calls `_list_models`,
`src/i18n_ai/cli/tui/setup.py:685`), and `_fill` (`setup.py:797`) resets `#model` with `set_options`. A model picked
before the key goes back to the saved default, or to nothing. The old form on `main` did the same; GH-69's
`test_wizard.py` model-card test gives the key before picking the model to step around it.

Left for later because it predates GH-69 and isn't part of the wizard's change.

Fixing it: when the listing comes back, keep the current pick if it is in the new list, and fall back to the default
only otherwise. Then put the model-card test in the natural order: pick the model, then give the key.
