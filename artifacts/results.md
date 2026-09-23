# Results

Profit figures are deterministic (no randomness in the LP/MILP solve), so they
should match exactly regardless of who runs `make results` or on what
machine. Solve times will vary by hardware — that's expected, not a
reproducibility concern.

| Market | Resolution | Periods | Total profit | Solve time | Sanity checks |
|---|---|---|---|---|---|
| Market 1 only | Half-hourly | 52,608 | £153,354.08 | ~28s | passed |
| Market 2 only | Hourly | 26,304 | £174,540.65 | ~5s | passed |

## Two-market (joint model) — informational

Solving both markets jointly (with the full complementarity constraint linking
them — see `model.py`) is far more expensive at full 3-year scale: the
cross-market coupling is the dominant cost, not raw problem size (confirmed by
timing the single-market cases above against the joint model at the same
resolution — the joint solve took ~51x longer than the two
single-market solves combined). Not part of the default `make results` path
for that reason; observed once, logged here:

| Total profit | Solve time |
|---|---|
| £210,867.12 | ~27.7 min |

Note this is *higher* than either single-market result but *less* than their
naive sum (£327,894.73) — expected, since the joint model has one
physical battery competing for capacity between two markets, not two
independent batteries as the separate single-market solves implicitly assume.
