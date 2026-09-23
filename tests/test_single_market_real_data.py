"""Regression guard: confirms code changes haven't moved the headline numbers.

Marked slow (solves against the real 3-year dataset, ~40s) — excluded from
the default `make test` run, run explicitly via `make test-slow`.
"""

import pytest

from battery_dispatch.data import load_battery_params, load_market_prices
from battery_dispatch.single_market import solve_single_market

# Observed values, logged in artifacts/results.md — see single_market.py's
# TWO_MARKET_PROFIT_GBP for the joint-model equivalent.
EXPECTED_MARKET_1_PROFIT_GBP = 153_354.08
EXPECTED_MARKET_2_PROFIT_GBP = 174_540.65

pytestmark = pytest.mark.slow


def test_market_1_profit_matches_known_value():
    battery = load_battery_params()
    prices = load_market_prices()

    result, _ = solve_single_market(battery, prices.market_1_half_hourly, dt_hours=0.5)

    assert result.total_profit_gbp == pytest.approx(EXPECTED_MARKET_1_PROFIT_GBP, abs=0.01)


def test_market_2_profit_matches_known_value():
    battery = load_battery_params()
    prices = load_market_prices()

    result, _ = solve_single_market(battery, prices.market_2_hourly, dt_hours=1.0)

    assert result.total_profit_gbp == pytest.approx(EXPECTED_MARKET_2_PROFIT_GBP, abs=0.01)
