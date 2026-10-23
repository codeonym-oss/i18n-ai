---
planning-root: planning
forge: github
default-branch: main
tracker: github
tracker-project: codeonym-oss/i18n-ai
tracker-board: "4"
key-prefix: GH-
epic-as: issue with sub-issues
story-as: issue with sub-issues
ticket-as: issue
---

# Project rules

- Branches are named `<type>/<issue>-<slug>`, e.g. `feat/17-laravel`.
- Pull request titles are `<type>: <summary> (#issue)`, and pull requests are squash-merged.
- A pull request body says `Closes #N`, or `Part of #N` when the issue has more pull requests to come.
- Commits and pull requests carry no Claude attribution: no `Co-Authored-By: Claude`, no `Claude-Session:` link, no "Generated with Claude Code" line.
- On board 4, an issue moves to In Progress when its work starts, to In Review when its pull request opens, and to Done when it merges.
