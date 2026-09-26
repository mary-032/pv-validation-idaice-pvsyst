from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


# =============================================================================
# 11 - COMBINED FIGURE 3: WEATHER-BIN CV(RMSE) + nMBE
# =============================================================================
#
# Creates one two-panel Figure 3 in the style of the original combined figure:
#
#   (a) CV(RMSE) [%]
#   (b) nMBE [%]
#
# Each weather-condition group contains Systems A, B and C, with paired bars
# for IDA ICE and PVsyst.
#
# Colors are intentionally aligned with the later shading figures:
#
#   IDA ICE = blue
#   PVsyst  = green
#
# The RGB values are the familiar MATLAB default blue/green:
#
#   IDA ICE: #0072BD
#   PVsyst:  #77AC30
#
# The script uses the finalized Perez-Driesse Figure 3 results and does not
# recalculate any metrics.
# =============================================================================


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "03_analysis_output"

# Try the current/recomputed Figure 3 table first, then common alternatives.
INPUT_CANDIDATES = [
    OUT_DIR / "Figure3_weather_bins_recomputed.csv",
    OUT_DIR / "Figure3_weather_bins.csv",
    OUT_DIR / "Figure3_weather_bins_PD.csv",
]

OUTPUT_PNG = OUT_DIR / "Figure3_combined_weather_bins.png"
OUTPUT_PDF = OUT_DIR / "Figure3_combined_weather_bins.pdf"
OUTPUT_SVG = OUT_DIR / "Figure3_combined_weather_bins.svg"

# Match later Figures 4–6.
COLORS = {
    "IDA ICE": "#0072BD",   # blue
    "PVsyst": "#77AC30",    # green
}

SOFTWARE_ORDER = ["IDA ICE", "PVsyst"]
SYSTEM_ORDER = ["A", "B", "C"]

# Full names expected in the analysis output, with shorter display labels.
WEATHER_ORDER = [
    "Overcast/very cloudy",
    "Cloudy",
    "Mixed/broken",
    "Mostly clear",
    "Clear",
]

WEATHER_DISPLAY = {
    "Overcast/very cloudy": "Overcast",
    "Cloudy": "Cloudy",
    "Mixed/broken": "Mixed",
    "Mostly clear": "Mostly clear",
    "Clear": "Clear",
}

# This matches the visual order in the old combined figure.
PANEL_SPECS = [
    {
        "metric": "CVRMSE_percent",
        "ylabel": "CV(RMSE) [%]",
        "panel": "(a)",
        "zero_line": False,
    },
    {
        "metric": "nMBE_percent",
        "ylabel": "nMBE [%]",
        "panel": "(b)",
        "zero_line": True,
    },
]

# Figure dimensions suitable for a double-column journal figure.
FIGSIZE = (7.25, 3.25)
DPI = 600

BAR_WIDTH = 0.32
SYSTEM_STEP = 0.92
GROUP_GAP = 0.80


# =============================================================================
# Input handling
# =============================================================================

def first_existing(paths):
    for p in paths:
        if p.exists():
            return p

    attempted = "\n".join(
        f"  - {p.relative_to(ROOT)}"
        for p in paths
    )

    raise FileNotFoundError(
        "Could not find a Figure 3 weather-bin results table.\n"
        "Tried:\n"
        f"{attempted}"
    )


def find_column(df, aliases, required=True):
    """
    Case/format-insensitive column lookup.
    """
    normalized = {
        str(c).strip().lower().replace(" ", "").replace("_", "").replace("(", "").replace(")", ""):
        c
        for c in df.columns
    }

    for alias in aliases:
        key = (
            alias.strip()
            .lower()
            .replace(" ", "")
            .replace("_", "")
            .replace("(", "")
            .replace(")", "")
        )

        if key in normalized:
            return normalized[key]

    if required:
        raise KeyError(
            "Could not identify required column. "
            f"Tried aliases: {aliases}\n"
            f"Available columns: {list(df.columns)}"
        )

    return None


def normalize_software(value):
    s = str(value).strip().lower()

    if "ida" in s:
        return "IDA ICE"

    if "pvsyst" in s or "pv syst" in s:
        return "PVsyst"

    return str(value).strip()


def normalize_weather(value):
    """
    Normalize common spellings while preserving the finalized five categories.
    """
    s = str(value).strip().lower()

    if "overcast" in s or "very cloudy" in s:
        return "Overcast/very cloudy"

    if s == "cloudy":
        return "Cloudy"

    if "mixed" in s or "broken" in s:
        return "Mixed/broken"

    if "mostly clear" in s:
        return "Mostly clear"

    if s == "clear":
        return "Clear"

    return str(value).strip()


def load_results(path):
    raw = pd.read_csv(path)

    system_col = find_column(
        raw,
        ["System", "system"],
    )

    software_col = find_column(
        raw,
        ["Software", "software", "Tool", "Model"],
    )

    weather_col = find_column(
        raw,
        [
            "Sky_condition",
            "Weather_condition",
            "weather_bin",
            "sky_bin",
            "Condition",
            "Weather",
        ],
    )

    cvrmse_col = find_column(
        raw,
        [
            "CVRMSE_percent",
            "CV_RMSE_percent",
            "CV(RMSE) [%]",
            "CVRMSE",
        ],
        required=False,
    )

    nmbe_col = find_column(
        raw,
        [
            "nMBE_percent",
            "nMBE [%]",
            "nMBE",
        ],
        required=False,
    )

    # Support either wide format or long Metric/Value format.
    if cvrmse_col is None or nmbe_col is None:
        metric_col = find_column(
            raw,
            ["Metric", "metric"],
            required=False,
        )
        value_col = find_column(
            raw,
            ["Value", "value", "Estimate"],
            required=False,
        )

        if metric_col is None or value_col is None:
            raise KeyError(
                "The input does not contain recognizable CVRMSE/nMBE columns "
                "and is not a recognizable long-format Metric/Value table."
            )

        base = raw.rename(
            columns={
                system_col: "System",
                software_col: "Software",
                weather_col: "Sky_condition",
                metric_col: "Metric",
                value_col: "Value",
            }
        )

        base["Metric_normalized"] = (
            base["Metric"]
            .astype(str)
            .str.lower()
            .str.replace(" ", "", regex=False)
            .str.replace("_", "", regex=False)
            .str.replace("(", "", regex=False)
            .str.replace(")", "", regex=False)
            .str.replace("[", "", regex=False)
            .str.replace("]", "", regex=False)
            .str.replace("%", "percent", regex=False)
        )

        def metric_name(x):
            if "cvrmse" in x:
                return "CVRMSE_percent"
            if "nmbe" in x:
                return "nMBE_percent"
            return None

        base["Metric_plot"] = base["Metric_normalized"].map(metric_name)
        base = base[base["Metric_plot"].notna()].copy()

        data = (
            base.pivot_table(
                index=["System", "Software", "Sky_condition"],
                columns="Metric_plot",
                values="Value",
                aggfunc="first",
            )
            .reset_index()
        )

    else:
        data = raw.rename(
            columns={
                system_col: "System",
                software_col: "Software",
                weather_col: "Sky_condition",
                cvrmse_col: "CVRMSE_percent",
                nmbe_col: "nMBE_percent",
            }
        )[
            [
                "System",
                "Software",
                "Sky_condition",
                "CVRMSE_percent",
                "nMBE_percent",
            ]
        ].copy()

    data["System"] = (
        data["System"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    data["Software"] = data["Software"].map(normalize_software)
    data["Sky_condition"] = data["Sky_condition"].map(normalize_weather)

    for col in ["CVRMSE_percent", "nMBE_percent"]:
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce",
        )

    # There should be one value per weather/system/software combination.
    # If duplicates are present, use their mean and report it.
    dup = data.duplicated(
        subset=["System", "Software", "Sky_condition"],
        keep=False,
    )

    if dup.any():
        print(
            "WARNING: duplicate weather/system/software rows detected; "
            "averaging duplicates."
        )

        data = (
            data.groupby(
                ["System", "Software", "Sky_condition"],
                as_index=False,
            )[
                ["CVRMSE_percent", "nMBE_percent"]
            ]
            .mean()
        )

    return data


def validate_complete(data):
    missing = []

    for weather in WEATHER_ORDER:
        for system in SYSTEM_ORDER:
            for software in SOFTWARE_ORDER:
                row = data[
                    (data["Sky_condition"] == weather)
                    & (data["System"] == system)
                    & (data["Software"] == software)
                ]

                if len(row) != 1:
                    missing.append(
                        f"{weather} / {system} / {software}: {len(row)} rows"
                    )

    if missing:
        raise ValueError(
            "Figure input is incomplete or contains unexpected duplicates:\n"
            + "\n".join(f"  - {x}" for x in missing)
        )


# =============================================================================
# Plot helpers
# =============================================================================

def build_x_positions():
    """
    Return x position for each weather/system combination, group centers,
    separator locations and all system-tick labels.
    """
    positions = {}
    group_centers = {}
    separators = []

    current = 0.0

    for wi, weather in enumerate(WEATHER_ORDER):
        system_x = []

        for system in SYSTEM_ORDER:
            positions[(weather, system)] = current
            system_x.append(current)
            current += SYSTEM_STEP

        group_centers[weather] = float(np.mean(system_x))

        if wi < len(WEATHER_ORDER) - 1:
            # Midpoint of the gap between weather groups.
            separators.append(
                current - SYSTEM_STEP / 2 + GROUP_GAP / 2
            )
            current += GROUP_GAP

    return positions, group_centers, separators


def metric_value(data, weather, system, software, metric):
    row = data[
        (data["Sky_condition"] == weather)
        & (data["System"] == system)
        & (data["Software"] == software)
    ]

    return float(row.iloc[0][metric])


def set_reasonable_ylim(ax, metric, values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    if len(values) == 0:
        return

    if metric == "CVRMSE_percent":
        upper = max(10.0, float(values.max()) * 1.10)
        # Round upward to a visually clean 10 percentage-point boundary.
        upper = np.ceil(upper / 10.0) * 10.0
        ax.set_ylim(0, upper)

    else:
        max_abs = max(abs(float(values.min())), abs(float(values.max())))
        lim = max(5.0, max_abs * 1.15)
        # Clean 5 percentage-point symmetric boundary.
        lim = np.ceil(lim / 5.0) * 5.0
        ax.set_ylim(-lim, lim)


def plot_panel(
    ax,
    data,
    spec,
    positions,
    group_centers,
    separators,
):
    metric = spec["metric"]

    plotted_values = []

    # Draw paired bars.
    for weather in WEATHER_ORDER:
        for system in SYSTEM_ORDER:
            x = positions[(weather, system)]

            for si, software in enumerate(SOFTWARE_ORDER):
                value = metric_value(
                    data,
                    weather,
                    system,
                    software,
                    metric,
                )

                offset = (
                    -BAR_WIDTH / 2
                    if si == 0
                    else BAR_WIDTH / 2
                )

                ax.bar(
                    x + offset,
                    value,
                    width=BAR_WIDTH,
                    color=COLORS[software],
                    edgecolor="black",
                    linewidth=0.55,
                    zorder=3,
                )

                plotted_values.append(value)

    # System labels A/B/C repeated beneath each weather group.
    xticks = []
    xticklabels = []

    for weather in WEATHER_ORDER:
        for system in SYSTEM_ORDER:
            xticks.append(
                positions[(weather, system)]
            )
            xticklabels.append(system)

    ax.set_xticks(xticks)
    ax.set_xticklabels(
        xticklabels,
        fontsize=8,
    )

    # Weather labels as a second line below the system labels.
    # xaxis_transform: x=data coordinates, y=axes fraction.
    for weather in WEATHER_ORDER:
        ax.text(
            group_centers[weather],
            -0.145,
            WEATHER_DISPLAY[weather],
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=8.2,
            clip_on=False,
        )

    # Thin separators between weather groups.
    for xsep in separators:
        ax.axvline(
            xsep,
            color="black",
            linewidth=0.65,
            alpha=0.8,
            zorder=2,
        )

    if spec["zero_line"]:
        ax.axhline(
            0,
            color="black",
            linewidth=0.8,
            zorder=2,
        )

    ax.set_ylabel(
        spec["ylabel"],
        fontsize=9,
    )

    # Panel label.
    ax.text(
        0.01,
        0.98,
        spec["panel"],
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        fontweight="bold",
    )

    set_reasonable_ylim(
        ax,
        metric,
        plotted_values,
    )

    ax.grid(
        axis="y",
        color="0.82",
        linewidth=0.55,
        zorder=0,
    )

    ax.tick_params(
        axis="both",
        labelsize=8,
        width=0.8,
        length=3,
    )

    for spine in ax.spines.values():
        spine.set_linewidth(0.8)


# =============================================================================
# Main
# =============================================================================

def main():
    input_path = first_existing(INPUT_CANDIDATES)

    print("\nCOMBINED FIGURE 3")
    print("=" * 72)
    print(f"Input: {input_path.relative_to(ROOT)}")

    data = load_results(input_path)
    validate_complete(data)

    positions, group_centers, separators = build_x_positions()

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 8,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    fig, axes = plt.subplots(
        1,
        2,
        figsize=FIGSIZE,
        constrained_layout=False,
    )

    for ax, spec in zip(axes, PANEL_SPECS):
        plot_panel(
            ax,
            data,
            spec,
            positions,
            group_centers,
            separators,
        )

    # One shared legend centered above both panels.
    handles = [
        Patch(
            facecolor=COLORS["IDA ICE"],
            edgecolor="black",
            linewidth=0.55,
            label="IDA ICE",
        ),
        Patch(
            facecolor=COLORS["PVsyst"],
            edgecolor="black",
            linewidth=0.55,
            label="PVsyst",
        ),
    ]

    fig.legend(
        handles=handles,
        labels=["IDA ICE", "PVsyst"],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=2,
        frameon=True,
        fancybox=False,
        edgecolor="black",
        columnspacing=1.0,
        handletextpad=0.4,
        borderpad=0.25,
    )

    # Extra bottom space is needed for the weather-group labels.
    fig.subplots_adjust(
        left=0.075,
        right=0.995,
        bottom=0.23,
        top=0.88,
        wspace=0.27,
    )

    fig.savefig(
        OUTPUT_PNG,
        dpi=DPI,
        bbox_inches="tight",
        facecolor="white",
    )

    fig.savefig(
        OUTPUT_PDF,
        bbox_inches="tight",
        facecolor="white",
    )

    fig.savefig(
        OUTPUT_SVG,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(fig)

    print(f"Wrote: {OUTPUT_PNG.relative_to(ROOT)}")
    print(f"Wrote: {OUTPUT_PDF.relative_to(ROOT)}")
    print(f"Wrote: {OUTPUT_SVG.relative_to(ROOT)}")
    print("\nColors:")
    print("  IDA ICE = blue  #0072BD")
    print("  PVsyst  = green #77AC30")
    print("\nDONE")


if __name__ == "__main__":
    main()
