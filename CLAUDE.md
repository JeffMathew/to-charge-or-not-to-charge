# Project context

This repo is the deliverable for a technical assessment: a Python package that
dispatches a battery across two wholesale electricity markets to maximise profit.
See `data/2nd Round Technical Question.pdf` for the brief. The audience is an
interviewer who will read and discuss the code, so clarity beats cleverness.

# Working agreement

- **Simplicity first.** Write code that a reader unfamiliar with it can follow
  end-to-end quickly. Prefer the obvious approach over the clever one.
- **Slice sensibly.** Organise the package into small, reusable modules where
  that earns its keep. Don't split things that don't need splitting.
- **Docstrings.** Every function gets a short (1-2 line) docstring describing
  what it does, not why.
- **Tooling (default, may be revised once the package is scaffolded):**
  `pytest` for tests, `ruff` for lint.
- **MILP solver: PuLP modelling + HiGHS backend (`highspy`), not PuLP's bundled CBC.**
  Discovered while building slice-2: PuLP's bundled CBC binary has no macOS
  arm64 build, so it can't run at all on Apple Silicon — a real reproducibility
  risk for anyone else on the same architecture, not just this machine. HiGHS
  (via `highspy`) ships normal cross-platform wheels, no system-level install
  needed anywhere, and is also generally the faster solver of the two for this
  problem shape (SciPy itself moved to HiGHS for `linprog`/`milp`).
  `two_market_model.py` only builds a solver-agnostic `pulp.LpProblem`, so this was a one-line change
  at the `.solve(...)` call site — a genuine upgrade, not a workaround.
- **End of each slice:** run `/checks` before presenting the diff for review.
- **Never commit.** Diffs are reviewed by the user at the end of each slice;
  the user runs `git add`/`git commit` themselves.

# Roadmap

- [x] slice-0: repo skeleton (uv/pyproject/Makefile, src layout, twine-buildable)
- [x] slice-1: data loading (Attachment 1 + 2 parsing) + price series plots to artifacts/
- [x] slice-2: core MILP model (PuLP) — variables, constraints, objective
- [x] slice-3: solve + results extraction, with sanity checks (no simultaneous charge/discharge, SoC bounds)
- [ ] slice-4: reproducible run script/CLI + 1-paragraph approach summary
- [~] slice-5: dropped — PDF's worked examples don't need to be coded up (explicit call)

**Single-market-per-market is the primary reported result, not the two-market joint model.**
Measured at full 3-year scale: single-market solves take ~28s (Market 1) and
~5s (Market 2), while the two-market joint model — correct, tested, and kept
in the codebase (`two_market_model.py`/`two_market_results.py`) — takes ~28 minutes, because the
cross-market complementarity coupling is the dominant cost, not raw problem
size (confirmed by isolating it experimentally). The brief explicitly allows
"focussing on one market" as a simplification; given the measured gap, slices
3/4's "reproducible run" goal is satisfied by `make results` /
`single_market.py` (see `README.md`), with the two-market result logged
alongside it as an informational, non-default data point rather than deleted
or hidden. `make results` writes to `artifacts/new_results.md`, freshly
generated every run — `artifacts/results.md` is the author's own captured
reference run and is never overwritten by the script, so the two can be
diffed to confirm reproducibility. The two-market model also has its own
runnable entry point (`make two-market-results`), clearly separate from the
default path — console output only, no file written, ~25-30 min. Slice-4's
"1-paragraph approach summary" is satisfied by `README.md`'s new "Approach"
section.
