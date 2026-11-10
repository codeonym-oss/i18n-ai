# Set up a TUI run as the Aurora wizard

## Problem

The setup is one long stock form: the tree, the source, the targets, the output, the provider, the model and the
key, all at once.

## The change

- In the Run mode, the setup becomes v2's wizard: steps with a progress header, the targets as locale cards (name,
  direction, what each would need) with toggles, the provider and model as cards, built on the kit (story decision
  003).
- It starts on the tree Home shows (decision 005), with the last answers as defaults, as today.
- Same queries and the same result as the form today: it ends on the plan screen.

## For the ticket pass

- How many steps, and which fields share one; how search in the locale cards works at 80 columns.

## Done when

- [ ] The setup's `Pilot` tests carried over and passing: a run set up through the wizard reaches the plan.
- [ ] Snapshots at 160×45 and 80×24.
