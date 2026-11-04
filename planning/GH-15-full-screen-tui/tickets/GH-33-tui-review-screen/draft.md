# Review the fallbacks in the TUI: edit, retry or accept

## Problem

A run can leave messages in their source text. The person should see them, with why they failed, and fix them
without leaving the TUI. Ticket 1 records them; nothing acts on the record yet.

## The change

- A query and three application intents (story decision 002; decisions 001–003):
  - **list the fallbacks:** each recorded fallback with its source text, its current text, the rule it broke and the
    model's last rejected translation. An entry whose message, file or locale is gone is listed as stale
    (decision 007).
  - **set a message:** any message of a target; the text is checked against the rules and, when it passes, written
    into the target file; a recorded one leaves the record. A text that breaks a rule is refused with the
    violations, and nothing changes.
  - **retry fallbacks:** the model translates the chosen fallbacks again, through the engine's existing request
    (decision 001); what passes is written and leaves the record, what fails again is recorded anew.
  - **accept fallbacks:** they leave the record, and keep their text; no locale file is touched (decision 002).
- **Review screen:** the fallbacks as a table, with the highlighted one's source, rejected translation and rule.
  `space` marks rows; **edit** (`e`), **retry** (`r`) or **accept** (`a`) the marked or highlighted ones (decision
  006). A stale entry can only be accepted.
- **Ways in** (decision 005): **Review** (`v`) on the run's receipt when fallbacks remain, and on the setup screen,
  which says how many are recorded once a tree is scanned. Retry uses the form's model, and is off without one.

## Out of scope

- An `i18n-ai review` command (story decision 002).
- `generate` dropping stale record entries (decision 007).

## Done when

- [ ] Intent tests: a passing edit is written and unrecorded; a failing one is refused and changes nothing; a retry
      with the fake model sends only the chosen messages and writes what passes, the others staying recorded;
      accept clears entries, stale ones included, and touches no locale file.
- [ ] A `Pilot` test reviews a fallback left by a CLI run: edits it, and finds it written and out of the record.
- [ ] A story-level run, setup to review, works on an `examples/` tree with the fake model.

Ships as two pull requests, the intents then the screen (decision 004).
