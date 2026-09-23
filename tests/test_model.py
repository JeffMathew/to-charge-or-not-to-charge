from datetime import UTC, datetime, timedelta

import polars as pl
import pulp
import pytest

from battery_dispatch.data import BatteryParams, MarketPrices
from battery_dispatch.model import build_dispatch_model

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


def _solve(prices: MarketPrices):
    dispatch = build_dispatch_model(_BATTERY, prices)
    dispatch.problem.solve(pulp.HiGHS(msg=False))
    return dispatch


def test_no_arbitrage_at_flat_price():
    """Flat price everywhere: cycling always loses money to losses, so profit is 0."""
    prices = _prices(price_m1=[50, 50, 50, 50], price_m2=[50, 50])
    dispatch = _solve(prices)

    assert pulp.LpStatus[dispatch.problem.status] == "Optimal"
    assert dispatch.problem.objective.value() == 0


def test_arbitrage_charges_cheap_and_discharges_expensive():
    """Cheap-then-expensive Market 1 price: profit matches a hand-calculated value."""
    prices = _prices(price_m1=[10, 10, 100, 100], price_m2=[10, 100])
    dispatch = _solve(prices)

    assert pulp.LpStatus[dispatch.problem.status] == "Optimal"

    # Charge 1 MW for both cheap half-hours: cost = 10 * 1 * 0.5 * 2 = 10.
    # Stored energy: 1 * 0.5 * 0.95 * 2 = 0.95 MWh.
    # All of it gets discharged at the expensive price: delivered = 0.95 * 0.95 = 0.9025 MWh.
    # Revenue = 100 * 0.9025 = 90.25. Profit = 90.25 - 10 = 80.25.
    assert dispatch.problem.objective.value() == pytest.approx(80.25)


def test_wash_trade_temptation_is_not_exploited():
    """Market 2 offers a huge spread against Market 1 within the same hour.

    Using it would require charging at t=0 (is_charging[0]=1) and discharging
    at t=1 (is_charging[1]=0) via the *same* hourly Market 2 commitment — the
    complementarity constraint makes that contradictory, so it must stay
    completely unused despite the temptation.
    """
    prices = _prices(price_m1=[5, 100], price_m2=[200])
    dispatch = _solve(prices)

    assert pulp.LpStatus[dispatch.problem.status] == "Optimal"
    assert dispatch.charge_m2[0].value() == 0
    assert dispatch.discharge_m2[0].value() == 0

    # Charge 1 MW at t=0: cost = 5 * 1 * 0.5 = 2.5, storing 1 * 0.5 * 0.95 = 0.475 MWh.
    # Storage-limited discharge at t=1: delivered = 0.475 * 0.95 = 0.45125 MWh,
    # revenue = 100 * 0.45125 = 45.125. Profit = 45.125 - 2.5 = 42.625 — far
    # short of the >£190 a wash trade through Market 2 would otherwise offer.
    assert dispatch.problem.objective.value() == pytest.approx(42.625)


def test_solution_never_charges_and_discharges_at_once_and_respects_soc_bounds():
    """Structural check on a solved (non-trivial) scenario."""
    prices = _prices(price_m1=[10, 10, 100, 100], price_m2=[10, 100])
    dispatch = _solve(prices)

    for t in range(dispatch.n_half_hours):
        h = t // 2
        total_charge = dispatch.charge_m1[t].value() + dispatch.charge_m2[h].value()
        total_discharge = dispatch.discharge_m1[t].value() + dispatch.discharge_m2[h].value()
        assert total_charge == 0 or total_discharge == 0

    for t in range(dispatch.n_half_hours + 1):
        soc = dispatch.soc[t].value()
        assert 0 <= soc <= _BATTERY.max_storage_mwh
