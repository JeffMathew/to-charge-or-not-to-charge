---
name: checks
description: Run end-of-slice sanity checks (lint, tests) to catch regressions before a diff is reviewed. Use whenever a meaningful chunk of code has just been written or changed in this project, or when the user invokes /checks explicitly.
---

Run this from the repo root after finishing a slice of work, before showing the diff for review.

1. Check whether a `Makefile` exists.
   - If it doesn't, or it doesn't have a `lint`/`test` target yet, say so plainly
     (e.g. "no Makefile yet — nothing to check") rather than treating it as a
     pass or fail. This is expected before the package is scaffolded.
2. If the targets exist, run in order and capture output:
   - `make lint`
   - `make test`
   - `make typecheck` (only if that target exists)
3. Report a concise pass/fail summary per check. On failure, surface the
   actual error output — don't swallow or paraphrase it away.
4. If something fails, stop and report it. Don't silently fix it without
   flagging what was wrong and what you changed.
5. Never run `git add` or `git commit` as part of this skill.
