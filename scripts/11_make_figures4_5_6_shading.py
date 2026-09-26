"""Produce Figures 4–6: measured / IDA ICE / PVsyst shading-day power.

Input: authoritative 02_canonical_data/shading_analysis.csv (from script 01).
Output: three two-panel figures (six plots total), and six individual panels.

Hour-ending convention is identical to 02_run_analysis.py:
    start < timestamp <= start + 1 day
The next-day 00:00 timestamp is the hour ending 24:00 of the selected day.
No interpolation, smoothing, outlier filtering or resimulation is performed.
The original power values are in W; plotted values are converted to kW.
"""

from __future__ import annotations

from pathlib import Path
import math

import matplotlib
matplotlib.use("Agg")  # reliable when running locally in PyCharm without a GUI
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "02_canonical_data" / "shading_analysis.csv"
DEST = ROOT / "03_analysis_output" / "shading_figures"

# All three curves use the same exact hourly power records.
SERIES = {
    "Measured": "P_measured_W",
    "IDA ICE": "P_IDA_W",
    "PVsyst": "P_PVsyst_W",
}

# Match Figure 3's and Figures 4–6's intended color scheme.
# Markers + line styles distinguish the model curves in monochrome printing.
STYLES = {
    "Measured": dict(color="#555555", linestyle="-", marker=None,
                     linewidth=1.75, zorder=2),
    "IDA ICE": dict(color="#0072BD", linestyle="--", marker="o",
                    markersize=4.8, markevery=1, markerfacecolor="white",
                    markeredgewidth=1.0, linewidth=1.70, zorder=4),
    "PVsyst": dict(color="#77AC30", linestyle=":", marker="s",
                   markersize=4.7, markevery=1, markerfacecolor="white",
                   markeredgewidth=1.0, linewidth=1.85, zorder=3),
}

# Typography is deliberately larger because the user places an IDA ICE
# screenshot BETWEEN the two time-series plots in the final manuscript figure.
# When individual panels are resized to fit that three-column layout, all text
# should remain readable. Change the constants here to tune font sizes.
FONT_PANEL_TITLE = 14.0
FONT_AXIS_LABEL = 14.0
FONT_TICK_LABEL = 12.5
FONT_LEGEND = 13.0

# These are the already-finalized illustrative dates; never choose new dates.
DAYS = [
    ("clear", pd.Timestamp("2023-06-05"), "5 June 2023 · Clear"),
    ("partly_cloudy", pd.Timestamp("2023-05-15"),
     "15 May 2023 · Partly cloudy"),
]

FIGURE_SYSTEMS = [(4, "A"), (5, "B"), (6, "C")]

# For a fair day-to-day comparison, both panels for one system share the same
# y-axis (but separate systems may have different scales).
SAME_Y_SCALE_WITHIN_SYSTEM = True

# Files are exported both as 600 dpi PNG and vector PDF/SVG.
DPI = 600
UNIT = "kW"  # Change to "W" if the journal requests watts on the axis.


def read_source() -> pd.DataFrame:
    if not SOURCE.is_file():
        raise FileNotFoundError(
            "Required canonical shading input is missing:\n"
            f"  {SOURCE}\n"
            "Run script 01 to build 02_canonical_data/shading_analysis.csv. "
            "Do not substitute older raw/staging data or historical figure values."
        )

    d = pd.read_csv(SOURCE, parse_dates=["timestamp"])
    needed = {"timestamp", "system", *SERIES.values()}
    missing = needed.difference(d.columns)
    if missing:
        raise ValueError(f"Missing canonical columns: {sorted(missing)}")

    d["system"] = d["system"].astype(str).str.strip().str.upper()
    if d.duplicated(["timestamp", "system"]).any():
        raise ValueError("Duplicate timestamp/system pairs in shading canonical data.")

    for col in SERIES.values():
        d[col] = pd.to_numeric(d[col], errors="raise")

    if not np.isfinite(d[list(SERIES.values())].to_numpy(dtype=float)).all():
        raise ValueError("Measured and simulated shading power contain nonfinite values.")

    return d


def get_day(d: pd.DataFrame, system: str, day: pd.Timestamp) -> pd.DataFrame:
    # Hour-ending, exactly as in 02_run_analysis.py.
    end = day + pd.Timedelta(days=1)
    out = d.loc[
        d["system"].eq(system)
        & d["timestamp"].gt(day)
        & d["timestamp"].le(end)
    ].copy().sort_values("timestamp")

    expected = pd.date_range(day + pd.Timedelta(hours=1), end, freq="h")
    if len(out) != 24 or not out["timestamp"].reset_index(drop=True).equals(
        pd.Series(expected, name="timestamp")
    ):
        raise ValueError(
            f"System {system}, {day.date()}: expected precisely 24 consecutive "
            "hour-ending records from 01:00 through next-day 00:00. "
            f"Found {len(out)}; first/last: "
            f"{out['timestamp'].min()} / {out['timestamp'].max()}"
        )

    # 00:00 on the FOLLOWING day is displayed as hour ending 24:00.
    out["hour_ending"] = np.arange(1, 25, dtype=int)
    return out


def p_to_plot(watts: pd.Series) -> np.ndarray:
    arr = watts.to_numpy(dtype=float)
    return arr / 1000.0 if UNIT == "kW" else arr


def panel(ax, day_data: pd.DataFrame, title: str, panel_letter: str,
          y_upper: float | None) -> None:
    x = day_data["hour_ending"].to_numpy(dtype=int)
    for label in ("Measured", "IDA ICE", "PVsyst"):
        ax.plot(x, p_to_plot(day_data[SERIES[label]]),
                label=label, **STYLES[label])

    ax.set_title(f"({panel_letter})  {title}", fontsize=FONT_PANEL_TITLE, pad=10)
    ax.set_xlim(0, 24)
    ax.set_xticks([0, 4, 8, 12, 16, 20, 24])
    ax.set_xlabel("Hour ending [local time]", fontsize=FONT_AXIS_LABEL, labelpad=7)
    ax.set_ylabel(f"AC power [{UNIT}]", fontsize=FONT_AXIS_LABEL, labelpad=7)
    ax.set_ylim(bottom=0, top=y_upper)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, min_n_ticks=4))
    ax.grid(axis="both", color="#D8D8D8", linewidth=0.55)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=FONT_TICK_LABEL, direction="out", length=4)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)


def upper_limit(days: list[pd.DataFrame]) -> float:
    max_p = max(
        float(p_to_plot(x[col]).max())
        for x in days for col in SERIES.values()
    )
    step = 0.5 if UNIT == "kW" else 500.0
    return max(step, math.ceil(max_p * 1.10 / step) * step)


def shared_legend(fig):
    # Measured: continuous grey; IDA: dashed circles; PVsyst: dotted squares.
    handles = [
        Line2D([0], [0], label=label, **STYLES[label])
        for label in ("Measured", "IDA ICE", "PVsyst")
    ]
    fig.legend(
        handles=handles, loc="upper center", ncol=3,
        bbox_to_anchor=(0.5, 0.987), fontsize=FONT_LEGEND,
        frameon=True, fancybox=False, edgecolor="#888888",
        handlelength=2.9, handletextpad=0.6, columnspacing=2.0,
    )


def save_all(fig, stem: str):
    for extension in ("png", "pdf", "svg"):
        kwargs = {"dpi": DPI} if extension == "png" else {}
        fig.savefig(
            DEST / f"{stem}.{extension}",
            bbox_inches="tight", facecolor="white", **kwargs
        )


def make_combined(figure_no: int, system: str, days: list[pd.DataFrame],
                  y_upper: float):
    fig, axes = plt.subplots(1, 2, figsize=(10.3, 4.25), sharey=True)
    for ax, (letter, (_, _, title), data) in zip(
        axes, zip("ab", DAYS, days)
    ):
        panel(ax, data, title, letter, y_upper)

    shared_legend(fig)
    # Two panels remain legible at journal double-column width.
    fig.subplots_adjust(left=0.09, right=0.985, bottom=0.20,
                        top=0.75, wspace=0.18)
    stem = f"Figure{figure_no}_System{system}_clear_and_partly_cloudy"
    save_all(fig, stem)
    plt.close(fig)
    print(f"  {stem}.png / .pdf / .svg")


def make_individual(figure_no: int, system: str, idx: int,
                    data: pd.DataFrame, y_upper: float):
    key, _, title = DAYS[idx]
    fig, ax = plt.subplots(figsize=(4.75, 3.75))
    panel(ax, data, title, "ab"[idx], y_upper)
    shared_legend(fig)
    fig.subplots_adjust(left=0.18, right=0.97, bottom=0.20, top=0.72)
    stem = f"Figure{figure_no}_System{system}_panel_{'ab'[idx]}_{key}"
    save_all(fig, stem)
    plt.close(fig)


def main():
    d = read_source()
    DEST.mkdir(parents=True, exist_ok=True)
    print("FIGURES 4–6: SIX SHADING-DAY POWER PLOTS")
    print("Source:", SOURCE)
    print("Hour ending convention: 01:00–24:00; no smoothing or outlier removal.")
    print(f"Large fonts: title={FONT_PANEL_TITLE:g} pt, axis={FONT_AXIS_LABEL:g} pt, "
          f"ticks={FONT_TICK_LABEL:g} pt, legend={FONT_LEGEND:g} pt.")
    print("Measured = solid gray; IDA ICE = dashed blue circles; "
          "PVsyst = dotted green squares.")

    plotted_rows = []
    audit = []
    for figure_no, system in FIGURE_SYSTEMS:
        days = [get_day(d, system, date) for _, date, _ in DAYS]
        y_top = upper_limit(days) if SAME_Y_SCALE_WITHIN_SYSTEM else None
        print(f"\nFigure {figure_no}: System {system}")
        make_combined(figure_no, system, days, y_top)
        for idx, one_day in enumerate(days):
            make_individual(figure_no, system, idx, one_day, y_top)
            tag, date, _ = DAYS[idx]
            plot_data = one_day[["timestamp", "hour_ending", *SERIES.values()]].copy()
            plot_data.insert(0, "figure", figure_no)
            plot_data.insert(1, "system", system)
            plot_data.insert(2, "day_type", tag)
            plotted_rows.append(plot_data)
            record = {
                "figure": figure_no, "system": system, "day_type": tag,
                "calendar_date": str(date.date()), "n_hours": len(one_day)
            }
            for label, col in SERIES.items():
                record[f"{label}_daily_energy_kWh"] = one_day[col].sum() / 1000
            audit.append(record)

    pd.concat(plotted_rows, ignore_index=True).to_csv(
        DEST / "Figures4_5_6_plotted_hourly_power.csv", index=False
    )
    pd.DataFrame(audit).to_csv(
        DEST / "Figures4_5_6_daily_energy_check.csv", index=False
    )
    print("\nPlot-data and daily-energy check CSVs written.")
    print("Output folder:", DEST)
    print("For a three-column figure with an IDA ICE screenshot in the middle, "
          "use the individual panel PNG/PDF files rather than cropping the "
          "two-panel figure, to retain maximum type size and resolution.")
    print("Note: hourly POWER is plotted in", UNIT,
          "(not hourly energy in Wh). 24:00 means 00:00 the next day.")
    print("DONE")


if __name__ == "__main__":
    main()
