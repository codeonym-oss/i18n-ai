# 011: A pipe plural is one unit

**Date:** 2026-10-23 (ticket pass, Q5; agreed: "ok", to the recommended option 1)

**Question:** is a pipe plural translated as one unit (the whole string), or as one unit per form?

**Decision:** **one unit.** Its signature holds the parsed shape (the forms, their ranges); the prompt asks for the
target's number of forms, each described by the counts Laravel's table sends to it; `check` parses the answer and
rejects a wrong number of forms or a changed range, which is sent back like any rejection.

- **Why:** the model sees every form together and keeps them consistent; no new kind of slot in the schema.
- **Not chosen:** a unit per form (a slot that joins units, and forms indexed by Laravel's numbers, which
  `PluralForm`'s CLDR categories do not fit).
