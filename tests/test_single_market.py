from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from battery_dispatch.data import BatteryParams
from battery_dispatch.single_market import (
    build_single_market_model,
    solve_single_market,
    validate_single_market_solution,
)

_BATTERY = BatteryParams(
    max_charge_rate_mw=1,
    max_discharge_rate_mw=1,
    max_storage_mwh=10,
    charge_loss_fraction=0.05,
    discharge_loss_fraction=0.05,
    lifetime_years=10,
    lifetime_cycles=5000,
    degradation_pct_per_cycle=0.001,
    capex_gbp=500_000,
    fixed_opex_gbp_per_year=5_000,
)


def _prices(values: list[float], dt_hours: float) -> pl.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    step = timedelta(hours=dt_hours)
    return pl.DataFrame(
        {
            "timestamp": [start + step * i for i in range(len(values))],
            "price_gbp_per_mwh": values,
        }
    )


def test_no_arbitrage_at_flat_price():
    """Flat price everywhere: cycling always loses money to losses, so profit is 0."""
    prices = _prices([50, 50, 50, 50], dt_hours=0.5)
    result, _ = solve_single_market(_BATTERY, prices, dt_hours=0.5)

    assert result.total_profit_gbp == 0


def test_arbitrage_charges_cheap_and_discharges_expensive():
    """Cheap-then-expensive price: profit and dispatch match a hand-calculated value."""
    prices = _prices([5, 100], dt_hours=0.5)
    result, _ = solve_single_market(_BATTERY, prices, dt_hours=0.5)

    # Charge 1 MW at t=0: cost = 5 * 1 * 0.5 = 2.5, storing 1 * 0.5 * 0.95 = 0.475 MWh.
    # Storage-limited discharge at t=1: delivered = 0.475 * 0.95 = 0.45125 MWh,
    # revenue = 100 * 0.45125 = 45.125. Profit = 45.125 - 2.5 = 42.625.
    assert result.total_profit_gbp == pytest.approx(42.625)
    assert result.dispatch["charge_mw"].to_list() == pytest.approx([1, 0])
    assert result.dispatch["discharge_mw"].to_list() == pytest.approx([0, 0.9025])
    assert result.soc["soc_mwh"].to_list() == pytest.approx([0, 0.475, 0])


def test_validate_solution_raises_on_simultaneous_charge_and_discharge():
    prices = _prices([5, 100], dt_hours=0.5)
    dispatch = build_single_market_model(_BATTERY, prices, dt_hours=0.5)

    dispatch.charge[0].varValue = 1
    dispatch.discharge[0].varValue = 1

    with pytest.raises(AssertionError, match="simultaneous"):
        validate_single_market_solution(dispatch)


def test_validate_solution_raises_on_rate_violation():
    prices = _prices([5, 100], dt_hours=0.5)
    dispatch = build_single_market_model(_BATTERY, prices, dt_hours=0.5)

    dispatch.charge[0].varValue = _BATTERY.max_charge_rate_mw + 1
    dispatch.discharge[0].varValue = 0

    with pytest.raises(AssertionError, match="outside"):
        validate_single_market_solution(dispatch)
