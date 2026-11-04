# 002: The record is a flat, sorted list, its paths as segments

**Date:** 2026-10-26 (ticket pass, Q2; agreed: "ok", to the recommended option 1)

**Question:** what does `.i18n-ai-fallbacks.json` look like?

**Decision:**

```json
{
  "version": 1,
  "fallbacks": [
    {"file": "fr/auth.json", "path": ["errors", "locked"],
     "problems": [{"rule": "placeholders", "message": "{{name}} is missing"}],
     "rejected": "Compte bloqué"}
  ]
}
```

- `file` is relative to the record's directory (story decision 009); a bundle's entry adds `"key"`, its locale's key.
- `path` is the `KeyPath`'s segments, strings and list indexes, so any key round-trips.
- `problems` are the errors the last attempt broke; `rejected` is that attempt's text, `null` when the model gave
  none.
- Entries are sorted by file, key and path, written with an indent and a final newline: stable diffs.
- A run replaces every entry of each (file, key) it wrote, and leaves the others.

- **Why:** exact for any key (Laravel's keys are sentences with dots), line-friendly in a diff, versioned.
- **Not chosen:** nesting by the printed path (dots in keys need escaping); nesting by the path's JSON (unreadable
  in a diff).
