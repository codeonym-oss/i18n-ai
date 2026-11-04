# 012: A pipe plural's placeholders are compared as a set

**Date:** 2026-10-23 (ticket pass, Q6; agreed: "ok", to the recommended option 1)

**Question:** a pipe plural grown from 2 forms to 3 repeats its placeholders, and a form may leave `:count` out;
how are its placeholders checked?

**Decision:** **as a set over the whole message:** every placeholder of the source appears in at least one form of
the translation (its case free, decision 004), and none appears that the source lacks. How often is not compared.

- **Why:** the number of forms changes with the language, and which form shows the count is the language's business.
- **Not chosen:** per form, by index (Russian's third form has no English counterpart); the counts with `:count`
  exempt (`:name` in three forms still rejected).
- **Cost accepted:** a form that loses `:name` while the others keep it passes.
