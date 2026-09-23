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
- **End of each slice:** run `/checks` before presenting the diff for review.
- **Never commit.** Diffs are reviewed by the user at the end of each slice;
  the user runs `git add`/`git commit` themselves.

# Roadmap

- [x] slice-0: repo skeleton (uv/pyproject/Makefile, src layout, twine-buildable)
- [ ] slice-1: data loading (Attachment 1 + 2 parsing) + price series plots to artifacts/
- [ ] slice-2: core MILP model (PuLP) — variables, constraints, objective
- [ ] slice-3: solve + results extraction, with sanity checks (no simultaneous charge/discharge, SoC bounds)
- [ ] slice-4: reproducible run script/CLI + 1-paragraph approach summary
- [ ] slice-5: tests — synthetic scenario reproducing the PDF's worked examples, wired into /checks
