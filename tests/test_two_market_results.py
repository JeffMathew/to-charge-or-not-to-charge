from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from battery_dispatch.data import BatteryParams, MarketPrices
from battery_dispatch.two_market_model import build_dispatch_model
from battery_dispatch.two_market_results import solve_and_extract, validate_solution

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


def _prices(price_m1: list[float], price_m2: list[float]) -> MarketPrices:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    m1 = pl.DataFrame(
        {
            "timestamp": [start + timedelta(minutes=30 * i) for i in range(len(price_m1))],
            "price_gbp_per_mwh": price_m1,
        }
    )
    m2 = pl.DataFrame(
        {
            "timestamp": [start + timedelta(hours=i) for i in range(len(price_m2))],
            "price_gbp_per_mwh": price_m2,
        }
    )
    return MarketPrices(market_1_half_hourly=m1, market_2_hourly=m2)


def test_no_arbitrage_extracts_zero_profit():
    prices = _prices(price_m1=[50, 50, 50, 50], price_m2=[50, 50])
    dispatch = build_dispatch_model(_BATTERY, prices)
    result = solve_and_extract(dispatch, prices)

    assert result.total_profit_gbp == 0


def test_extracts_correct_values_for_a_deterministic_scenario():
    """Same wash-trade-temptation scenario as test_model.py: Market 2 is
    provably forced to zero here (no solver tie-breaking involved), so exact
    per-market values can be asserted, not just the total profit.
    """
    prices = _prices(price_m1=[5, 100], price_m2=[200])
    dispatch = build_dispatch_model(_BATTERY, prices)
    result = solve_and_extract(dispatch, prices)

    assert result.total_profit_gbp == pytest.approx(42.625)

    assert result.market_1["charge_mw"].to_list() == pytest.approx([1, 0])
    assert result.market_1["discharge_mw"].to_list() == pytest.approx([0, 0.9025])
    assert result.market_2["charge_mw"].to_list() == pytest.approx([0])
    assert result.market_2["discharge_mw"].to_list() == pytest.approx([0])
    assert result.soc["soc_mwh"].to_list() == pytest.approx([0, 0.475, 0])

    assert result.market_1["timestamp"][0] == datetime(2024, 1, 1, tzinfo=UTC)
    assert result.soc["timestamp"][2] == datetime(2024, 1, 1, 1, 0, tzinfo=UTC)


def test_validate_solution_raises_on_simultaneous_charge_and_discharge():
    """Hand-set variable values to simulate a bad solve, without needing to
    actually break the solver — confirms the check itself works."""
    prices = _prices(price_m1=[5, 100], price_m2=[200])
    dispatch = build_dispatch_model(_BATTERY, prices)

    dispatch.charge_m1[0].varValue = 1
    dispatch.discharge_m1[0].varValue = 1
    dispatch.charge_m2[0].varValue = 0
    dispatch.discharge_m2[0].varValue = 0

    with pytest.raises(AssertionError, match="half-hour 0"):
        validate_solution(dispatch)
