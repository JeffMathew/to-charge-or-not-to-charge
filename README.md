# battery-dispatch

Battery dispatch optimisation across two wholesale electricity markets.

## Setup

```sh
uv sync
```

## Results

```sh
make results
```

Solves the battery dispatch problem against each market **separately** (Market 1
half-hourly, Market 2 hourly — see `single_market.py`), validates the solution
(no simultaneous charge/discharge, charge/discharge rates respected, SoC
within bounds), and writes [`artifacts/results.md`](artifacts/results.md).
Takes well under a minute. Profit figures are deterministic, so re-running
this — on this machine or any other — should reproduce the exact same numbers;
solve time will vary by hardware.

The codebase also has a full two-market joint model (`two_market_model.py`/`two_market_results.py`)
that co-optimises both markets together, including the cross-market
complementarity constraint that stops the battery exploiting a wash trade
between them. It's correct and tested, but far more expensive to solve at
full 3-year scale (order of minutes, not seconds — see `artifacts/results.md`
for the measured comparison), so it isn't part of the default reproduce path.

Run `/validate-results` (Claude Code skill, `.claude/skills/validate-results/`)
or `make test-slow` to confirm the codebase still reproduces the exact profit
figures reported above — a regression guard against future changes silently
moving the numbers.
