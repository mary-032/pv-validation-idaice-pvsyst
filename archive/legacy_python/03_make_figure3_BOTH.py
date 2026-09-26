from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "03_analysis_output" / "Figure3_weather_bins_recomputed.csv"
FIG_DIR = ROOT / "03_analysis_output" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# Display order
# ------------------------------------------------------------
SKY_ORDER = [
    "Overcast/very cloudy",
    "Cloudy",
    "Mixed/broken",
    "Mostly clear",
    "Clear",
]

SYSTEM_ORDER = ["A", "B", "C"]
SOFTWARE_ORDER = ["IDA ICE", "PVsyst"]


def prepare_data():
    df = pd.read_csv(DATA_PATH)

    required = {
        "System",
        "Sky_condition",
        "Software",
        "nMBE_percent",
        "CVRMSE_percent",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{DATA_PATH.name} is missing columns: {sorted(missing)}"
        )

    df = df[
        df["System"].isin(SYSTEM_ORDER)
        & df["Sky_condition"].isin(SKY_ORDER)
        & df["Software"].isin(SOFTWARE_ORDER)
    ].copy()

    expected_rows = len(SKY_ORDER) * len(SYSTEM_ORDER) * len(SOFTWARE_ORDER)
    if len(df) != expected_rows:
        print(
            f"WARNING: found {len(df)} plotting rows; "
            f"expected {expected_rows}."
        )

    return df


def build_plot(df, metric, ylabel, filename, y_limits=None, y_ticks=None):
    """
    One plot with:
      - five sky-condition groups,
      - systems A/B/C within each group,
      - paired IDA ICE/PVsyst bars at each system position.
    """

    # 15 x positions = 5 sky conditions × 3 systems
    x = np.arange(len(SKY_ORDER) * len(SYSTEM_ORDER), dtype=float)

    bar_width = 0.36
    offsets = {
        "IDA ICE": -bar_width / 2,
        "PVsyst": +bar_width / 2,
    }

    fig, ax = plt.subplots(figsize=(12.0, 5.8))

    for software in SOFTWARE_ORDER:
        values = []

        for condition in SKY_ORDER:
            for system in SYSTEM_ORDER:
                row = df[
                    (df["Sky_condition"] == condition)
                    & (df["System"] == system)
                    & (df["Software"] == software)
                ]

                if len(row) != 1:
                    values.append(np.nan)
                else:
                    values.append(float(row.iloc[0][metric]))

        ax.bar(
            x + offsets[software],
            values,
            width=bar_width,
            label=software,
        )

    # System labels at every x position.
    ax.set_xticks(x)
    ax.set_xticklabels(SYSTEM_ORDER * len(SKY_ORDER))

    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)

    if y_limits is not None:
        ax.set_ylim(*y_limits)

    if y_ticks is not None:
        ax.set_yticks(y_ticks)

    # Zero line is useful for nMBE.
    if metric == "nMBE_percent":
        ax.axhline(0, linewidth=0.8)

    # Add separators between sky-condition groups.
    for separator in (2.5, 5.5, 8.5, 11.5):
        ax.axvline(separator, linewidth=0.8, alpha=0.6)

    # Add sky-condition labels below A/B/C.
    group_centers = [1, 4, 7, 10, 13]

    for center, condition in zip(group_centers, SKY_ORDER):
        short = {
            "Overcast/very cloudy": "Overcast/\nvery cloudy",
            "Cloudy": "Cloudy",
            "Mixed/broken": "Mixed/\nbroken",
            "Mostly clear": "Mostly\nclear",
            "Clear": "Clear",
        }[condition]

        ax.text(
            center,
            -0.13,
            short,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=10,
            fontweight="bold",
        )

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.13),
        ncol=2,
        frameon=False,
    )

    # Leave room for condition labels under the x-axis.
    fig.subplots_adjust(
        left=0.08,
        right=0.99,
        top=0.84,
        bottom=0.24,
    )

    # Export both raster and vector versions.
    png_path = FIG_DIR / f"{filename}.png"
    pdf_path = FIG_DIR / f"{filename}.pdf"

    fig.savefig(
        png_path,
        dpi=300,
        bbox_inches="tight",
    )
    fig.savefig(
        pdf_path,
        bbox_inches="tight",
    )

    print(f"Wrote {png_path.relative_to(ROOT)}")
    print(f"Wrote {pdf_path.relative_to(ROOT)}")

    # Close this figure so the script immediately continues to Figure 3b.
    # plt.show() here blocks execution in many PyCharm configurations until
    # the first plot window is manually closed.
    plt.close(fig)


def main():
    df = prepare_data()

    print("\nFIGURE 3 - WEATHER-BIN RESULTS")
    print("=" * 50)
    print(f"Input: {DATA_PATH.relative_to(ROOT)}")

    # Figure 3a: normalized mean bias error
    build_plot(
        df=df,
        metric="nMBE_percent",
        ylabel="nMBE [%]",
        filename="Figure3a_nMBE_by_sky_condition",
    )

    # Figure 3b: coefficient of variation of RMSE
    build_plot(
        df=df,
        metric="CVRMSE_percent",
        ylabel="CV(RMSE) [%]",
        filename="Figure3b_CVRMSE_by_sky_condition",
    )


if __name__ == "__main__":
    main()
