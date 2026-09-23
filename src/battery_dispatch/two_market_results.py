"""Solve a built dispatch model and turn it into checked, usable results."""

import time
from dataclasses import dataclass
from datetime import timedelta

import polars as pl
import pulp

from battery_dispatch.data import MarketPrices, load_battery_params, load_market_prices
from battery_dispatch.two_market_model import DispatchModel, build_dispatch_model

_TOLERANCE = 1e-6


def _check_within_bounds(var: pulp.LpVariable, name: str) -> None:
    value = var.value()
    if not (var.lowBound - _TOLERANCE <= value <= var.upBound + _TOLERANCE):
        raise AssertionError(f"{name}={value} outside [{var.lowBound}, {var.upBound}]")


@dataclass
class DispatchResult:
    """The solved dispatch schedule and its total profit."""

    total_profit_gbp: float
    market_1: pl.DataFrame  # timestamp, charge_mw, discharge_mw (half-hourly)
    market_2: pl.DataFrame  # timestamp, charge_mw, discharge_mw (hourly)
    soc: pl.DataFrame  # timestamp, soc_mwh (half-hourly, n_half_hours + 1 rows)


def validate_solution(dispatch: DispatchModel) -> None:
    """Check the solved variables respect the invariants the model is meant to guarantee.

    Raises AssertionError if not — a violation means something is genuinely
    wrong (solver bug, formulation bug, or a numerical issue), not something
    to silently tolerate.
    """
    for t in range(dispatch.n_half_hours):
        h = t // 2
        charge = dispatch.charge_m1[t].value() + dispatch.charge_m2[h].value()
        discharge = dispatch.discharge_m1[t].value() + dispatch.discharge_m2[h].value()
        if charge > _TOLERANCE and discharge > _TOLERANCE:
            raise AssertionError(
                f"half-hour {t}: simultaneous charge ({charge}) and discharge ({discharge})"
            )
        _check_within_bounds(dispatch.charge_m1[t], f"charge_m1[{t}]")
        _check_within_bounds(dispatch.discharge_m1[t], f"discharge_m1[{t}]")

    for h in range(dispatch.n_hours):
        _check_within_bounds(dispatch.charge_m2[h], f"charge_m2[{h}]")
        _check_within_bounds(dispatch.discharge_m2[h], f"discharge_m2[{h}]")

    for t, soc_var in dispatch.soc.items():
        _check_within_bounds(soc_var, f"soc[{t}]")


def extract_results(dispatch: DispatchModel, prices: MarketPrices) -> DispatchResult:
    """Read solved variable values into a DispatchResult."""
    m1_timestamps = prices.market_1_half_hourly["timestamp"].head(dispatch.n_half_hours)
    m2_timestamps = prices.market_2_hourly["timestamp"].head(dispatch.n_hours)

    market_1 = pl.DataFrame(
        {
            "timestamp": m1_timestamps,
            "charge_mw": [dispatch.charge_m1[t].value() for t in range(dispatch.n_half_hours)],
            "discharge_mw": [
                dispatch.discharge_m1[t].value() for t in range(dispatch.n_half_hours)
            ],
        }
    )
    market_2 = pl.DataFrame(
        {
            "timestamp": m2_timestamps,
            "charge_mw": [dispatch.charge_m2[h].value() for h in range(dispatch.n_hours)],
            "discharge_mw": [dispatch.discharge_m2[h].value() for h in range(dispatch.n_hours)],
        }
    )
    # soc has one more point than there are half-hours: the state *after* the
    # final period, half an hour past the last price timestamp. Cast to match
    # m1_timestamps' dtype explicitly — real data loads as Datetime('ms'), but
    # a fresh pl.Series of Python datetimes defaults to Datetime('us').
    final_soc_timestamp = pl.Series(
        [m1_timestamps[-1] + timedelta(minutes=30)], dtype=m1_timestamps.dtype
    )
    soc_timestamps = pl.concat([m1_timestamps, final_soc_timestamp])
    soc = pl.DataFrame(
        {
            "timestamp": soc_timestamps,
            "soc_mwh": [dispatch.soc[t].value() for t in range(dispatch.n_half_hours + 1)],
        }
    )

    return DispatchResult(
        total_profit_gbp=dispatch.problem.objective.value(),
        market_1=market_1,
        market_2=market_2,
        soc=soc,
    )


def solve_and_extract(dispatch: DispatchModel, prices: MarketPrices) -> DispatchResult:
    """Solve the model (HiGHS), validate the solution, and extract the results."""
    dispatch.problem.solve(pulp.HiGHS(msg=False))
    status = pulp.LpStatus[dispatch.problem.status]
    if status != "Optimal":
        raise RuntimeError(f"solver did not find an optimal solution: {status}")

    validate_solution(dispatch)
    return extract_results(dispatch, prices)


if __name__ == "__main__":
    print("Solving the joint two-market model at full scale — this takes ~25-30 minutes.")
    print("Results are printed to console only; no file is written.\n")

    battery = load_battery_params()
    prices = load_market_prices()

    dispatch = build_dispatch_model(battery, prices)
    start = time.time()
    result = solve_and_extract(dispatch, prices)
    solve_seconds = time.time() - start

    print(f"Total profit: £{result.total_profit_gbp:,.2f}")
    print(f"Solve time: {solve_seconds / 60:.1f} min")
