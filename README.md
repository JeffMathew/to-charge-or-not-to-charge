# battery-dispatch

Battery dispatch optimisation across two wholesale electricity markets.

## Approach

This models battery dispatch as a full mixed-integer linear program (MILP):
binary charge/discharge exclusivity per timestep, efficiency-loss-adjusted
state-of-charge dynamics, and rate/capacity constraints, solved with PuLP +
HiGHS. The primary, reproducible result solves each market **separately**
(Market 1 half-hourly, Market 2 hourly) rather than jointly — measured, not
assumed: the cross-market complementarity constraint needed to stop the
battery exploiting price-spread wash trades between markets makes the joint
two-market MILP roughly 50x slower to solve at full 3-year scale (~28 minutes
vs ~30 seconds combined). The joint two-market model is fully implemented and
tested (`two_market_model.py`/`two_market_results.py`) and runnable on
demand — just not the default path, given that cost.

## Setup

1. Install and select the pinned Python version (see `.python-version`):
   ```sh
   pyenv install
   ```
2. Create the virtual environment and install dependencies:
   ```sh
   uv sync
   ```

## Running the solves

### Single-market (primary, reproducible result)

```sh
make results
```

Solves each market **separately** (see `single_market.py`), validates the
solution (no simultaneous charge/discharge, charge/discharge rates
respected, SoC within bounds), and writes
[`artifacts/results.md`](artifacts/results.md). Takes well under a minute.
Profit figures are deterministic, so re-running this — on this machine or any
other — should reproduce the exact same numbers; solve time will vary by
hardware.

### Two-market / joint model

```sh
make two-market-results
```

Solves both markets jointly, including the cross-market complementarity
constraint (see `two_market_model.py`/`two_market_results.py`).

> [!WARNING]
> Takes **~25-30 minutes**. Results are **printed to console only — no file
> is written**. This isn't part of the default reproduce path; run it only if
> you want to see the joint-model answer for yourself.

## Validating reproducibility

```sh
make test-slow
```

Or invoke the `/validate-results` Claude Code skill
(`.claude/skills/validate-results/`). Both run the real-data regression test
that confirms the codebase still reproduces the exact single-market profit
figures reported in `artifacts/results.md` — a guard against future changes
silently moving the numbers.
