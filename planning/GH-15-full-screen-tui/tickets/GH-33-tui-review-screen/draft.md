# Review the fallbacks in the TUI: edit, retry or accept

## Problem

A run can leave messages in their source text. The person should see them, with why they failed, and fix them
without leaving the TUI. Ticket 1 records them; nothing acts on the record yet.

## The change

- Two new application intents (story decision 002):
  - **set a message:** the text is checked against the rules; when it passes, it is written into the target file and
    leaves the record. A text that breaks a rule is refused with the violations.
  - **retry messages:** the model translates the given fallbacks again; what passes is written and leaves the record.
- **Review screen**, after the run and from the TUI's start (for fallbacks earlier runs left): each recorded
  fallback with its source, the last rejected translation and the rule it broke. **Edit**, **retry** or **accept**
  (the message stays as it is and leaves the record).

## Out of scope

- An `i18n-ai review` command (decision 002).

## Done when

- [ ] Intent tests: a passing edit is written and unrecorded; a failing one is refused and changes nothing; a retry
      with the fake model writes what passes.
- [ ] A `Pilot` test reviews a fallback left by a CLI run: edits it, and finds it written and out of the record.
- [ ] A story-level run, setup to review, works on an `examples/` tree with the fake model.

## For the ticket pass

- Retry needs the engine to translate only some messages of a file: through `EngineRequest`, or a request of its own.
- Whether this splits into the intents and the screen (decision 010 allows it).
