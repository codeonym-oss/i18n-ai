---
status: done
from: agent
found-while: GH-33
resolved-by: GH-50, GH-58
---

# Five Dependabot alerts on `main`

Every push on 2026-11-04 reported: "GitHub found 5 vulnerabilities on codeonym-oss/i18n-ai's default branch
(1 critical, 2 high, 1 moderate, 1 low)", at https://github.com/codeonym-oss/i18n-ai/security/dependabot.

Not looked at: they are unrelated to GH-33's ticket pass. Fixing it: read each alert, find which are direct
dependencies in `pyproject.toml` and which come through `uv.lock`, and bump them (or merge the Dependabot pull
requests that cover them), checking that `uv run pytest` still passes.

GH-50 raised the npm examples' floors only; the Laravel example (`laravel/framework` `^11.0`) and `virtualenv` in `uv.lock` were left, and GH-58 fixed them (2026-11-09).
