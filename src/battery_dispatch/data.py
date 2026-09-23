"""Load battery parameters and market price data from the provided spreadsheets."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
ATTACHMENT_1 = DATA_DIR / "Attachment 1.xlsx"
ATTACHMENT_2 = DATA_DIR / "Attachment 2.xlsx"


@dataclass(frozen=True)
class BatteryParams:
    """The battery's physical and commercial parameters, from Attachment 1."""

    max_charge_rate_mw: float
    max_discharge_rate_mw: float
    max_storage_mwh: float
    charge_loss_fraction: float
    discharge_loss_fraction: float
    lifetime_years: float
    lifetime_cycles: float
    degradation_pct_per_cycle: float
    capex_gbp: float
    fixed_opex_gbp_per_year: float


_BATTERY_PARAM_ROWS = {
    "Max charging rate": "max_charge_rate_mw",
    "Max discharging rate": "max_discharge_rate_mw",
    "Max storage volume": "max_storage_mwh",
    "Battery charging efficiency": "charge_loss_fraction",
    "Battery discharging efficiency": "discharge_loss_fraction",
    "Lifetime (1)": "lifetime_years",
    "Lifetime (2)": "lifetime_cycles",
    "Storage volume degradation rate": "degradation_pct_per_cycle",
    "Capex": "capex_gbp",
    "Fixed Operational Costs": "fixed_opex_gbp_per_year",
}


def load_battery_params(path: Path = ATTACHMENT_1) -> BatteryParams:
    """Read Attachment 1's "Data" sheet into a BatteryParams instance."""
    df = pl.read_excel(path, sheet_name="Data")
    df.columns = ["parameter", "value", "units", "description"]

    values_by_field = {
        _BATTERY_PARAM_ROWS[row["parameter"]]: row["value"]
        for row in df.iter_rows(named=True)
        if row["parameter"] in _BATTERY_PARAM_ROWS
    }
    return BatteryParams(**values_by_field)


@dataclass(frozen=True)
class MarketPrices:
    """Price series for both markets, at their native settlement resolution."""

    market_1_half_hourly: pl.DataFrame
    market_2_hourly: pl.DataFrame


def _read_price_sheet(path: Path, sheet_name: str) -> pl.DataFrame:
    df = pl.read_excel(path, sheet_name=sheet_name)
    df.columns = ["timestamp", "price_gbp_per_mwh"]
    return df.drop_nulls()


def load_market_prices(path: Path = ATTACHMENT_2) -> MarketPrices:
    """Read Attachment 2's two sheets into a MarketPrices instance.

    The "Hourly data" sheet has trailing blank rows in the source file's
    declared range, but `read_excel` (via fastexcel/calamine) already
    excludes them using the sheet's actual used range — `drop_nulls()` is
    a defensive no-op guarding that invariant, not what does the trimming.
    """
    return MarketPrices(
        market_1_half_hourly=_read_price_sheet(path, "Half-hourly data"),
        market_2_hourly=_read_price_sheet(path, "Hourly data"),
    )
