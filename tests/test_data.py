from datetime import datetime

from battery_dispatch.data import load_battery_params, load_market_prices


def test_load_battery_params():
    """Values match Attachment 1's "Data" sheet exactly."""
    params = load_battery_params()

    assert params.max_charge_rate_mw == 2
    assert params.max_discharge_rate_mw == 2
    assert params.max_storage_mwh == 4
    assert params.charge_loss_fraction == 0.05
    assert params.discharge_loss_fraction == 0.05


def test_load_market_prices():
    """Row counts, nulls, and date range match Attachment 2's two sheets."""
    prices = load_market_prices()
    m1 = prices.market_1_half_hourly
    m2 = prices.market_2_hourly

    assert m1.shape == (52608, 2)
    assert m2.shape == (26304, 2)
    assert m1.null_count().sum_horizontal().item() == 0
    assert m2.null_count().sum_horizontal().item() == 0

    # Source data has no timezone info; polars keeps the column naive to match,
    # so these must stay naive too or the comparison would break.
    assert m1["timestamp"].min() == datetime(2018, 1, 1, 0, 0)  # noqa: DTZ001
    assert m1["timestamp"].max() == datetime(2020, 12, 31, 23, 30)  # noqa: DTZ001
    assert m2["timestamp"].min() == datetime(2018, 1, 1, 0, 0)  # noqa: DTZ001
