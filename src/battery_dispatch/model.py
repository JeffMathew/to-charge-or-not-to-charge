"""Build the battery dispatch MILP: decision variables, constraints, objective."""

from dataclasses import dataclass

import pulp

from battery_dispatch.data import BatteryParams, MarketPrices


@dataclass
class DispatchModel:
    """A built (unsolved) dispatch problem, with its variables for later extraction."""

    problem: pulp.LpProblem
    charge_m1: dict[int, pulp.LpVariable]
    discharge_m1: dict[int, pulp.LpVariable]
    charge_m2: dict[int, pulp.LpVariable]
    discharge_m2: dict[int, pulp.LpVariable]
    is_charging: dict[int, pulp.LpVariable]
    soc: dict[int, pulp.LpVariable]
    n_half_hours: int
    n_hours: int


def build_dispatch_model(
    battery: BatteryParams,
    prices: MarketPrices,
    n_half_hours: int | None = None,
) -> DispatchModel:
    """Build the MILP that maximises trading profit across both markets.

    `n_half_hours` truncates the price series to the first N half-hours (and
    the corresponding N//2 hours), for fast tests or scale experiments — the
    full dataset is used by default.
    """
    m1 = prices.market_1_half_hourly
    m2 = prices.market_2_hourly
    if n_half_hours is not None:
        m1 = m1.head(n_half_hours)
        m2 = m2.head(n_half_hours // 2)
    price_m1 = m1["price_gbp_per_mwh"].to_list()
    price_m2 = m2["price_gbp_per_mwh"].to_list()

    n_half_hours = len(price_m1)
    n_hours = len(price_m2)
    half_hours = range(n_half_hours)
    hours = range(n_hours)

    problem = pulp.LpProblem("battery_dispatch", pulp.LpMaximize)

    charge_m1 = problem.add_variable_dicts(
        "charge_m1", half_hours, lowBound=0, upBound=battery.max_charge_rate_mw
    )
    discharge_m1 = problem.add_variable_dicts(
        "discharge_m1", half_hours, lowBound=0, upBound=battery.max_discharge_rate_mw
    )
    charge_m2 = problem.add_variable_dicts(
        "charge_m2", hours, lowBound=0, upBound=battery.max_charge_rate_mw
    )
    discharge_m2 = problem.add_variable_dicts(
        "discharge_m2", hours, lowBound=0, upBound=battery.max_discharge_rate_mw
    )
    is_charging = problem.add_variable_dicts("is_charging", half_hours, cat="Binary")
    soc = problem.add_variable_dicts(
        "soc", range(n_half_hours + 1), lowBound=0, upBound=battery.max_storage_mwh
    )

    problem += pulp.lpSum(
        (discharge_m1[t] - charge_m1[t]) * price_m1[t] * 0.5 for t in half_hours
    ) + pulp.lpSum(
        (discharge_m2[h] - charge_m2[h]) * price_m2[h] * 1.0 for h in hours
    )

    problem += soc[0] == 0
    for t in half_hours:
        h = t // 2
        problem += (
            charge_m1[t] + charge_m2[h] <= battery.max_charge_rate_mw * is_charging[t]
        )
        problem += discharge_m1[t] + discharge_m2[h] <= battery.max_discharge_rate_mw * (
            1 - is_charging[t]
        )
        problem += soc[t + 1] == soc[t] + (charge_m1[t] + charge_m2[h]) * 0.5 * (
            1 - battery.charge_loss_fraction
        ) - (discharge_m1[t] + discharge_m2[h]) * 0.5 / (
            1 - battery.discharge_loss_fraction
        )

    return DispatchModel(
        problem=problem,
        charge_m1=charge_m1,
        discharge_m1=discharge_m1,
        charge_m2=charge_m2,
        discharge_m2=discharge_m2,
        is_charging=is_charging,
        soc=soc,
        n_half_hours=n_half_hours,
        n_hours=n_hours,
    )
