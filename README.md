# battery-dispatch

Battery dispatch optimisation across two wholesale electricity markets.

## Approach

Firstly, I was thrown off by seeing negative prices in the dataset and
did some reading with Claude to understand why that happens in the real world,
and the implications when solving across such numbers (model is incentivised
to buy when prices are negative). I initially considered treating this as a relaxed
LP with no charge/discharge constraint because in a single market, the optima wouldn't
be to charge/discharge at the same time into the same market at the same price anyway.
However, it turned out if I wanted to solve for the two-market scenario, I would need to
explicitly disallow charge/discharge at the same time, otherwise model would prefer to use
that simultaneous mechanism when spreads between markets were good enough. Thus, it is effectively a full MILP.

In the end, I have framed both the single-market and dual-market problems and solved for them, with Claude driving the code development and tool proposals, I reviewed (almost) each file and made commits myself. This README has instructions to run both single-market and two-market flavours of the problem, the latter took ~30 mins to run on my machine.




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
[`artifacts/new_results.md`](artifacts/new_results.md) — freshly generated
every run, so it never overwrites
[`artifacts/results.md`](artifacts/results.md) (the author's own captured
reference run). Takes well under a minute. Profit figures are deterministic,
so your own `new_results.md` should match `results.md` exactly; solve time
will vary by hardware.

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
