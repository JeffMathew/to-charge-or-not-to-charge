"""Dispatch a battery against a single market — build, solve, validate, extract.

A separate, self-contained formulation from two_market_model.py/
two_market_results.py: no hour/half-hour index mapping, no cross-market
terms. One function serves either market via `dt_hours` (0.5 for Market 1,
1.0 for Market 2).
"""

import time
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import pulp

from battery_dispatch.data import BatteryParams, load_battery_params, load_market_prices

_TOLERANCE = 1e-6

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
# Written fresh on every run. Deliberately not "results.md" — that file holds
# the author's own captured experiment results and is never touched by this
# script, so anyone re-running it can diff their own output against it.
RESULTS_FILENAME = "new_results.md"

# Observed once (not reproduced by this script — see README/results.md for why).
TWO_MARKET_PROFIT_GBP = 210_867.12
TWO_MARKET_SOLVE_SECONDS = 1662.65


@dataclass
class SingleMarketDispatchModel:
    """A built (unsolved) single-market dispatch problem."""

    problem: pulp.LpProblem
    charge: dict[int, pulp.LpVariable]
    discharge: dict[int, pulp.LpVariable]
    is_charging: dict[int, pulp.LpVariable]
    soc: dict[int, pulp.LpVariable]
    n_periods: int
    dt_hours: float


def build_single_market_model(
    battery: BatteryParams,
    price_df: pl.DataFrame,
    dt_hours: float,
    n_periods: int | None = None,
) -> SingleMarketDispatchModel:
    """Build the MILP that maximises trading profit against one market."""
    df = price_df.head(n_periods) if n_periods is not None else price_df
    prices = df["price_gbp_per_mwh"].to_list()
    n = len(prices)
    periods = range(n)

    problem = pulp.LpProblem("single_market_dispatch", pulp.LpMaximize)

    charge = problem.add_variable_dicts(
        "charge", periods, lowBound=0, upBound=battery.max_charge_rate_mw
    )
    discharge = problem.add_variable_dicts(
        "discharge", periods, lowBound=0, upBound=battery.max_discharge_rate_mw
    )
    is_charging = problem.add_variable_dicts("is_charging", periods, cat="Binary")
    soc = problem.add_variable_dicts(
        "soc", range(n + 1), lowBound=0, upBound=battery.max_storage_mwh
    )

    problem += pulp.lpSum(
        (discharge[t] - charge[t]) * prices[t] * dt_hours for t in periods
    )

    problem += soc[0] == 0
    for t in periods:
        problem += charge[t] <= battery.max_charge_rate_mw * is_charging[t]
        problem += discharge[t] <= battery.max_discharge_rate_mw * (1 - is_charging[t])
        problem += soc[t + 1] == soc[t] + charge[t] * dt_hours * (
            1 - battery.charge_loss_fraction
        ) - discharge[t] * dt_hours / (1 - battery.discharge_loss_fraction)

    return SingleMarketDispatchModel(
        problem=problem,
        charge=charge,
        discharge=discharge,
        is_charging=is_charging,
        soc=soc,
        n_periods=n,
        dt_hours=dt_hours,
    )


@dataclass
class SingleMarketResult:
    """The solved single-market dispatch schedule and its total profit."""

    total_profit_gbp: float
    dispatch: pl.DataFrame  # timestamp, charge_mw, discharge_mw
    soc: pl.DataFrame  # timestamp, soc_mwh (n_periods + 1 rows)


def validate_single_market_solution(dispatch: SingleMarketDispatchModel) -> None:
    """Check the solved variables respect the invariants the model guarantees.

    Raises AssertionError if not — a violation means something is genuinely
    wrong (solver bug, formulation bug, or a numerical issue).
    """
    for t in range(dispatch.n_periods):
        charge = dispatch.charge[t].value()
        discharge = dispatch.discharge[t].value()
        if charge > _TOLERANCE and discharge > _TOLERANCE:
            raise AssertionError(
                f"period {t}: simultaneous charge ({charge}) and discharge ({discharge})"
            )
        if not (-_TOLERANCE <= charge <= dispatch.charge[t].upBound + _TOLERANCE):
            raise AssertionError(f"charge[{t}]={charge} outside rate bound")
        if not (-_TOLERANCE <= discharge <= dispatch.discharge[t].upBound + _TOLERANCE):
            raise AssertionError(f"discharge[{t}]={discharge} outside rate bound")

    for t, soc_var in dispatch.soc.items():
        value = soc_var.value()
        if not (soc_var.lowBound - _TOLERANCE <= value <= soc_var.upBound + _TOLERANCE):
            raise AssertionError(
                f"soc[{t}]={value} outside [{soc_var.lowBound}, {soc_var.upBound}]"
            )


def extract_single_market_results(
    dispatch: SingleMarketDispatchModel, price_df: pl.DataFrame
) -> SingleMarketResult:
    """Read solved variable values into a SingleMarketResult."""
    timestamps = price_df["timestamp"].head(dispatch.n_periods)

    dispatch_df = pl.DataFrame(
        {
            "timestamp": timestamps,
            "charge_mw": [dispatch.charge[t].value() for t in range(dispatch.n_periods)],
            "discharge_mw": [
                dispatch.discharge[t].value() for t in range(dispatch.n_periods)
            ],
        }
    )

    period_delta = timestamps[1] - timestamps[0] if dispatch.n_periods > 1 else None
    final_timestamp = pl.Series(
        [timestamps[-1] + period_delta] if period_delta is not None else [timestamps[-1]],
        dtype=timestamps.dtype,
    )
    soc_timestamps = pl.concat([timestamps, final_timestamp])
    soc_df = pl.DataFrame(
        {
            "timestamp": soc_timestamps,
            "soc_mwh": [dispatch.soc[t].value() for t in range(dispatch.n_periods + 1)],
        }
    )

    return SingleMarketResult(
        total_profit_gbp=dispatch.problem.objective.value(),
        dispatch=dispatch_df,
        soc=soc_df,
    )


def solve_single_market(
    battery: BatteryParams,
    price_df: pl.DataFrame,
    dt_hours: float,
    n_periods: int | None = None,
) -> tuple[SingleMarketResult, float]:
    """Build, solve (HiGHS), validate, and extract. Returns (result, solve_seconds)."""
    dispatch = build_single_market_model(battery, price_df, dt_hours, n_periods)

    start = time.time()
    dispatch.problem.solve(pulp.HiGHS(msg=False))
    solve_seconds = time.time() - start

    status = pulp.LpStatus[dispatch.problem.status]
    if status != "Optimal":
        raise RuntimeError(f"solver did not find an optimal solution: {status}")

    validate_single_market_solution(dispatch)
    result = extract_single_market_results(dispatch, price_df)
    return result, solve_seconds


def _write_results_md(
    m1_result: SingleMarketResult,
    m1_seconds: float,
    m2_result: SingleMarketResult,
    m2_seconds: float,
) -> None:
    naive_sum = m1_result.total_profit_gbp + m2_result.total_profit_gbp
    slowdown = TWO_MARKET_SOLVE_SECONDS / (m1_seconds + m2_seconds)
    content = f"""# Results (freshly generated)

Profit figures are deterministic (no randomness in the LP/MILP solve), so they
should match exactly regardless of who runs `make results` or on what
machine. Solve times will vary by hardware — that's expected, not a
reproducibility concern. Compare this file against `results.md` (the
author's own captured run) to confirm your own run reproduces the same
numbers — `results.md` itself is never overwritten by this script.

| Market | Resolution | Periods | Total profit | Solve time | Sanity checks |
|---|---|---|---|---|---|
| Market 1 only | Half-hourly | {m1_result.dispatch.height:,} | £{m1_result.total_profit_gbp:,.2f} | ~{m1_seconds:.0f}s | passed |
| Market 2 only | Hourly | {m2_result.dispatch.height:,} | £{m2_result.total_profit_gbp:,.2f} | ~{m2_seconds:.0f}s | passed |

## Two-market (joint model) — informational

Solving both markets jointly (with the full complementarity constraint linking
them — see `two_market_model.py`) is far more expensive at full 3-year scale: the
cross-market coupling is the dominant cost, not raw problem size (confirmed by
timing the single-market cases above against the joint model at the same
resolution — the joint solve took ~{slowdown:.0f}x longer than the two
single-market solves combined). Not part of the default `make results` path
for that reason; observed once, logged here:

| Total profit | Solve time |
|---|---|
| £{TWO_MARKET_PROFIT_GBP:,.2f} | ~{TWO_MARKET_SOLVE_SECONDS / 60:.1f} min |

Note this is *higher* than either single-market result but *less* than their
naive sum (£{naive_sum:,.2f}) — expected, since the joint model has one
physical battery competing for capacity between two markets, not two
independent batteries as the separate single-market solves implicitly assume.
"""
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    (ARTIFACTS_DIR / RESULTS_FILENAME).write_text(content)


if __name__ == "__main__":
    battery = load_battery_params()
    prices = load_market_prices()

    m1_result, m1_seconds = solve_single_market(
        battery, prices.market_1_half_hourly, dt_hours=0.5
    )
    print(f"Market 1: £{m1_result.total_profit_gbp:,.2f} ({m1_seconds:.1f}s)")

    m2_result, m2_seconds = solve_single_market(
        battery, prices.market_2_hourly, dt_hours=1.0
    )
    print(f"Market 2: £{m2_result.total_profit_gbp:,.2f} ({m2_seconds:.1f}s)")

    _write_results_md(m1_result, m1_seconds, m2_result, m2_seconds)
    print(f"Wrote {ARTIFACTS_DIR / RESULTS_FILENAME}")
