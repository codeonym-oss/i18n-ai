# Review fallbacks on the Aurora review screen

## Problem

The review is a stock list and a separate edit screen: the source, the rejected translation and the fix are never
side by side.

## The change

- v2's three-way comparison for the fallback under the cursor: the source, the model's last rejected translation
  with its rule, and the editor; the attempts beside it.
- Edit, retry and accept through the commands there are today (#15 decision 002); the list updates as each is done.
- The other locales of the same key, as far as the tree holds them.

## For the ticket pass

- Whether the editor checks the rules as you type, and through what (no new command, story rule).
- How far "other locales" can go on the tree alone (story decision 001).

## Done when

- [ ] The review's `Pilot` tests carried over: edit, retry and accept each update the record.
- [ ] Snapshots at 160×45 and 80×24.
