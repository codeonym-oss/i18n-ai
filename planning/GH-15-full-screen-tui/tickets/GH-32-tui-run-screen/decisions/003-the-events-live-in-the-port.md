# 003: The progress events live in the port, with the result they carry

**Date:** 2026-10-29 (review, Q3; agreed: "ok", to the recommended option 1)

**Found:** with the events beside the receipt (`generate_locales/progress.py`), `IGenerationProgress` named them only
under `TYPE_CHECKING`: the port pointed up at an intent's slice, against the layout CONTRIBUTING.md and
architecture.md describe (ports below the intents).

**Decision:** **the events, and `FileResult` and `ResultStatus` that `JobDone` carries, move down into
`application/ports/progress/`.** `receipt.py` keeps `GenerationReceipt`, which imports them from there; the public
exports do not change. Decision 001's events are unchanged.

- **Why:** the layout holds, with no import that only type checking sees.
- **Not chosen:** leaving them in the slice (the one `TYPE_CHECKING` import in `src`, pointing the wrong way); events
  with plain fields instead of a `FileResult` (changes decision 001, and the screens rebuild what it gives).
- **Kept apart:** the engine's `AtomStarted`/`AttemptRejected` carry the `TranslationJob` and its documents; the
  progress events carry only what a screen shows.
