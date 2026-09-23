"""Render each market's price history to a PNG under artifacts/."""

from pathlib import Path

import matplotlib.pyplot as plt

from battery_dispatch.data import MarketPrices, load_market_prices

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"

_LINE_COLOR = "#2a78d6"
_SURFACE_COLOR = "#fcfcfb"
_PRIMARY_INK = "#0b0b0b"
_MUTED_INK = "#898781"
_GRIDLINE = "#e1e0d9"
_BASELINE = "#c3c2b7"


def _plot_series(df, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 4), dpi=150, facecolor=_SURFACE_COLOR)
    ax.set_facecolor(_SURFACE_COLOR)

    ax.plot(df["timestamp"], df["price_gbp_per_mwh"], color=_LINE_COLOR, linewidth=0.8)

    ax.set_title(title, color=_PRIMARY_INK, fontsize=13, loc="left")
    ax.set_ylabel("£/MWh", color=_MUTED_INK)
    ax.tick_params(colors=_MUTED_INK)
    ax.grid(True, color=_GRIDLINE, linewidth=0.8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(_BASELINE)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_price_series(prices: MarketPrices, output_dir: Path = ARTIFACTS_DIR) -> None:
    """Save each market's full price history as a PNG line chart."""
    output_dir.mkdir(exist_ok=True)
    _plot_series(
        prices.market_1_half_hourly,
        "Market 1 — Half-Hourly Price",
        output_dir / "market_1_price_series.png",
    )
    _plot_series(
        prices.market_2_hourly,
        "Market 2 — Hourly Price",
        output_dir / "market_2_price_series.png",
    )


if __name__ == "__main__":
    plot_price_series(load_market_prices())
