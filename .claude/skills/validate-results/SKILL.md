---
name: validate-results
description: Confirm code changes haven't moved the headline single-market profit numbers, by running the real-data regression test. Use after changing two_market_model.py, single_market.py, two_market_results.py, or data.py, or when the user invokes /validate-results explicitly.
---

Run this from the repo root to confirm the reported results (`artifacts/results.md`) still match what the codebase actually produces.

1. Run `make test-slow` and capture output.
2. Report a concise pass/fail summary.
   - On pass: state which known values were confirmed (Market 1, Market 2 profit).
   - On failure: surface the actual assertion output — it already shows expected
     vs. actual for whichever number diverged. Don't paraphrase it away.
3. If it fails, that means a genuine regression: something about the model,
   data loading, or solve path changed the answer. Stop and report it — don't
   silently update the expected values in `tests/test_single_market_real_data.py`
   to make it pass without the user first confirming the new numbers are
   correct and intentional.
4. Never run `git add` or `git commit` as part of this skill.
