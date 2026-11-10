#!/usr/bin/env python3
"""Build publication *candidates* for Revision 2 supplementary Tables S1a/S1b
and Figures S1a/S1b, exclusively from audited Step 28/29 annual AC data.

This program never runs old historical scripts or modifies original results.

From repository root:
  python scripts/40_build_seasonal_diurnal_supplement.py
  python scripts/40_build_seasonal_diurnal_supplement.py --check-only
  python scripts/40_build_seasonal_diurnal_supplement.py --overwrite

--check-only verifies numerical artifacts and presence (not pixel identity) of plots.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    ("fixed_CET_hypothesis", "S1a", "Working fixed-CET model-clock interpretation"),
    ("civil_unshifted", "S1b", "Alternative unshifted civil-clock interpretation"),
)
SYSTEMS = ("A", "B", "C")
MODELS = ("IDA_ICE", "PVsyst")
COLORS = {"IDA_ICE": "#77AC30", "PVsyst": "#0072BD"}
SEASONS = (("DJF", "Winter (DJF)"), ("MAM", "Spring (MAM)"),
           ("JJA", "Summer (JJA)"), ("SON", "Autumn (SON)"))
SEASON_N = {"DJF": 703, "MAM": 1310, "JJA": 1537, "SON": 928}
EXPECTED_HOURS = 4478
SOURCE_FILES = {
    "fixed_CET_hypothesis": "28_annual_AC_primary_fixed_CET.csv",
    "civil_unshifted": "28_annual_AC_sensitivity_civil_unshifted.csv",
}
DIURNAL_FIELDS = ("scenario", "system", "model", "hour_start_local", "n",
                  "mean_error_W", "median_error_W", "q25_error_W", "q75_error_W",
                  "RMSE_W", "MAE_W")
FIG_EXT = ("pdf", "svg", "png")


def require(test: bool, detail: str) -> None:
    if not test:
        raise ValueError(detail)


def read_csv(path: Path) -> list[dict[str, str]]:
    require(path.is_file(), f"Missing source: {path}")
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    require(bool(rows), f"Empty source: {path}")
    return rows


def check_unique(rows: list[dict], keys: tuple[str, ...], name: str) -> dict[tuple, dict]:
    seen = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        require(key not in seen, f"Duplicate {name} key: {key}")
        seen[key] = row
    return seen


def read_hourly_inputs(root: Path) -> dict[str, list[dict]]:
    """Read the same physical matched hours and power columns as Step 29."""
    sources = {}
    for scenario, filename in SOURCE_FILES.items():
        raw = read_csv(root / "results" / "annual_audit" / filename)
        result = []
        for row in raw:
            require(row["system"] in SYSTEMS, "Unknown PV system")
            stamp = row["physical_interval_start_local"]
            date = datetime.fromisoformat(stamp)
            require(date.year in (2020, 2021), "Unexpected annual data year")
            require(int(row["power_valid_10min"]) == 6,
                    "Each selected interval must have six valid raw 10-minute measurements")
            meas = float(row["P_measured_W"])
            ida = float(row["IDA_hourly_table_end_aligned_W"])
            pv = float(row["PVsyst_EGrid_W"])
            require(all(map(math.isfinite, (meas, ida, pv))), "Non-finite power")
            result.append({"system": row["system"], "timestamp": stamp,
                           "hour": f"{date.hour:02d}", "measured": meas,
                           "IDA_ICE": ida, "PVsyst": pv})
        check_unique(result, ("system", "timestamp"), scenario)
        for system in SYSTEMS:
            n = sum(row["system"] == system for row in result)
            require(n == EXPECTED_HOURS, f"{scenario}/{system}: expected 4478, got {n}")
        sources[scenario] = result
    reference = {
        (r["system"], r["timestamp"]): r["measured"]
        for r in sources["fixed_CET_hypothesis"]
    }
    alternate = {
        (r["system"], r["timestamp"]): r["measured"]
        for r in sources["civil_unshifted"]
    }
    require(reference == alternate,
            "Clock scenarios have different physical measurements or selected timestamps")
    return sources


def format_one(value: float, *, sign: bool = False) -> str:
    # Round small signed values consistently: do not print a misleading -0.0.
    number = round(value, 1)
    if number == 0:
        number = 0.0
    return f"{number:+.1f}" if sign else f"{number:.1f}"


def table_rows(seasonal: list[dict[str, str]], scenario: str) -> list[list[str]]:
    lookup = check_unique(seasonal, ("scenario", "system", "model", "season"),
                          "Step 29 seasonal")
    table = []
    for system in SYSTEMS:
        for model in MODELS:
            record = [system, "IDA ICE" if model == "IDA_ICE" else model]
            for season, _ in SEASONS:
                k = (scenario, system, model, season)
                require(k in lookup, f"Missing Step 29 seasonal group {k}")
                row = lookup[k]
                require(int(float(row["n"])) == SEASON_N[season],
                        f"Unexpected sample count for {k}")
                cv = float(row["CVRMSE_pct"])
                bias = float(row["nMBE_pct"])
                require(math.isfinite(cv) and math.isfinite(bias) and cv >= 0,
                        f"Invalid metrics {k}")
                record.append(f"{format_one(cv)} / {format_one(bias, sign=True)}")
            table.append(record)
    require(len(table) == 6, "Expected six table rows")
    return table


def table_csv(rows: list[list[str]]) -> str:
    s = io.StringIO(newline="")
    writer = csv.writer(s, lineterminator="\n")
    writer.writerow(["System", "Software", *[name for _, name in SEASONS]])
    writer.writerows(rows)
    return s.getvalue()


def table_markdown(rows: list[list[str]], label: str, description: str) -> str:
    header = ["System", "Software", *[name for _, name in SEASONS]]
    lines = [f"# Table {label}. Seasonal hourly AC-power validation",
             "", description, "", "Each cell: **CV(RMSE) / nMBE (%)**.", "",
             "| " + " | ".join(header) + " |",
             "|:--|:--|--:|--:|--:|--:|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    lines += ["", "**Table note.** Positive nMBE indicates simulated power exceeding measured power. "
              "Sample sizes per system and model: winter (DJF) 703 hours; spring (MAM) "
              "1,310; summer (JJA) 1,537; autumn (SON) 928. The selected cohort "
              "does not contain 31 December 2020. Both software tools use the same "
              "4,478 physical selected hours per system. These are descriptive "
              "point estimates without season-specific confidence intervals.", "",
              "**Source:** `results/revision2/29_seasonal_AC.csv`, derived from "
              "the corrected Step 28 paired hourly series.", ""]
    return "\n".join(lines)


def quantile_sorted(values: list[float], p: float) -> float:
    """Type-7 linearly interpolated sample quantile (NumPy percentile default)."""
    require(bool(values) and 0 <= p <= 1, "Invalid quantile request")
    location = (len(values) - 1) * p
    low = math.floor(location)
    delta = location - low
    return values[low] * (1 - delta) + values[min(low + 1, len(values) - 1)] * delta


def residual_summary(errors: list[float]) -> dict[str, float | int]:
    require(bool(errors), "No residuals in an hour bin")
    require(all(map(math.isfinite, errors)), "Non-finite residual")
    values = sorted(errors)
    return {"n": len(errors), "mean_error_W": statistics.fmean(errors),
            "median_error_W": quantile_sorted(values, .5),
            "q25_error_W": quantile_sorted(values, .25),
            "q75_error_W": quantile_sorted(values, .75),
            "RMSE_W": math.sqrt(statistics.fmean(e * e for e in errors)),
            "MAE_W": statistics.fmean(abs(e) for e in errors)}


def build_diurnal(sources: dict[str, list[dict]],
                  step29_diurnal: list[dict[str, str]]) -> list[dict]:
    expected = check_unique(step29_diurnal,
                            ("scenario", "system", "model", "hour_start_local"),
                            "Step 29 diurnal")
    outputs = []
    for scenario, _, _ in SCENARIOS:
        rows = sources[scenario]
        for system in SYSTEMS:
            for model in MODELS:
                by_hour: dict[str, list[float]] = defaultdict(list)
                for item in rows:
                    if item["system"] == system:
                        by_hour[item["hour"]].append(item[model] - item["measured"])
                require(sum(map(len, by_hour.values())) == EXPECTED_HOURS,
                        f"Incorrect diurnal partition {scenario}/{system}")
                for hour, errors in sorted(by_hour.items()):
                    key = (scenario, system, model, hour)
                    require(key in expected, f"Missing Step 29 diurnal {key}")
                    calc = residual_summary(errors)
                    reference = expected[key]
                    require(calc["n"] == int(float(reference["n"])),
                            f"Count mismatch {key}")
                    for ours, theirs in (("mean_error_W", "MBE_W"),
                                         ("RMSE_W", "RMSE_W"),
                                         ("MAE_W", "MAE_W")):
                        require(math.isclose(float(calc[ours]), float(reference[theirs]),
                                             rel_tol=2e-9, abs_tol=2e-6),
                                f"Step 29 mismatch {key}/{ours}")
                    outputs.append({"scenario": scenario, "system": system,
                                    "model": model, "hour_start_local": hour, **calc})
    require(len(outputs) == len(expected) == 216,
            "Expected 216 composite hour/model/system/clock records")
    return outputs


def diurnal_csv(rows: list[dict]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=DIURNAL_FIELDS,
                            lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: f"{row[key]:.9f}" if isinstance(row[key], float)
                         else row[key] for key in DIURNAL_FIELDS})
    return buffer.getvalue()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifests(root: Path) -> dict:
    names = [*(root / "results" / "annual_audit" / f for f in SOURCE_FILES.values()),
             root / "results" / "revision2" / "29_seasonal_AC.csv",
             root / "results" / "revision2" / "29_diurnal_AC.csv"]
    return {"status": "REVISION2_SUPPLEMENT_CANDIDATE_NOT_APPROVED",
            "builder": "scripts/40_build_seasonal_diurnal_supplement.py",
            "reference": "Step 28 corrected matched power, cross-checked against Step 29",
            "input_sha256": {str(path.relative_to(root)).replace("\\", "/"): sha256(path)
                             for path in names},
            "season_definitions": "DJF / MAM / JJA / SON using local physical date",
            "diurnal_hour": "physical measured interval start, local wall clock",
            "bias_sign": "simulated minus measured (W or percent)",
            "diurnal_shaded_band": "25th to 75th sample percentile (type-7), not a confidence interval",
            "cohort_hours_per_system": EXPECTED_HOURS,
            "missing_selected_date": "2020-12-31 (cause not established)",
            "clock_scenarios": [label for label, _, _ in SCENARIOS],
            "limitations": ["original logger clock not independently authenticated",
                            "seasonal and diurnal point estimates lack block-bootstrap CIs",
                            "diurnal signatures do not identify causes of power error",
                            "seasonal CV(RMSE) can be inflated by low mean measured power"]}


def render_figure(diurnal: list[dict], scenario: str, label: str,
                  description: str, outdir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42,
                         "ps.fonttype": 42, "svg.fonttype": "none"})
    fig, axes = plt.subplots(3, 1, figsize=(9.6, 8.7), sharex=True, sharey=True)
    for ax, system in zip(axes, SYSTEMS):
        for model, linestyle, marker in (("IDA_ICE", "-", "o"),
                                         ("PVsyst", "--", "s")):
            selected = sorted((r for r in diurnal if r["scenario"] == scenario
                               and r["system"] == system and r["model"] == model),
                              key=lambda r: int(r["hour_start_local"]))
            x = [int(r["hour_start_local"]) for r in selected]
            center = [r["mean_error_W"] for r in selected]
            low = [r["q25_error_W"] for r in selected]
            high = [r["q75_error_W"] for r in selected]
            ax.plot(x, center, linestyle, marker=marker, markersize=3.1,
                    linewidth=1.9, color=COLORS[model],
                    label="IDA ICE" if model == "IDA_ICE" else "PVsyst")
            ax.fill_between(x, low, high, color=COLORS[model], alpha=0.14,
                            linewidth=0)
        ax.axhline(0, color="#444444", lw=0.85)
        ax.grid(True, axis="y", lw=0.55, alpha=.25)
        ax.set_title(f"System {system}", loc="left", fontsize=11, weight="bold")
        ax.set_ylabel("AC power error [W]", fontsize=9.5)
        ax.tick_params(labelsize=9)
    axes[-1].set_xlabel("Local hour at measured interval start", fontsize=10)
    axes[-1].set_xticks(list(range(5, 23, 1)))
    axes[-1].set_xlim(4.5, 22.5)
    axes[0].legend(loc="upper right", ncol=2, frameon=False)
    fig.suptitle(f"Figure {label}. Composite diurnal AC-power errors\n{description}",
                 fontsize=13, weight="bold", y=.997)
    fig.text(.5, .009,
             "Lines: mean simulated − measured  |  bands: 25th–75th percentiles  |  4,478 matched daylight hours/system",
             ha="center", fontsize=8.3)
    fig.tight_layout(rect=(.02, .035, .98, .935), h_pad=1.0)
    base = outdir / f"Figure_{label}_diurnal_{scenario}"
    for ext in FIG_EXT:
        fig.savefig(base.with_suffix(f".{ext}"), dpi=240,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)


def outputs(root: Path) -> tuple[dict[str, str], list[dict]]:
    seasonal = read_csv(root / "results/revision2/29_seasonal_AC.csv")
    require(len(seasonal) == 48, "Step 29 seasonal file must contain 48 rows")
    # Reject unexpected rows, not only missing groups.
    seasonal_keys = check_unique(seasonal,
            ("scenario", "system", "model", "season"), "Step 29 seasonal")
    require(len(seasonal_keys) == 2 * 3 * 2 * 4, "Incorrect seasonal key universe")
    existing_diurnal = read_csv(root / "results/revision2/29_diurnal_AC.csv")
    source = read_hourly_inputs(root)
    diurnal = build_diurnal(source, existing_diurnal)
    result = {}
    for scenario, label, description in SCENARIOS:
        table = table_rows(seasonal, scenario)
        stem = f"Table_{label}_seasonal_{scenario}"
        result[stem + ".csv"] = table_csv(table)
        result[stem + ".md"] = table_markdown(table, label, description)
    result["Figure_S1_diurnal_source_statistics.csv"] = diurnal_csv(diurnal)
    result["40_supplement_manifest.json"] = (json.dumps(manifests(root), indent=2,
                                                    ensure_ascii=False) + "\n")
    return result, diurnal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true",
                        help="Replace ONLY Step 40 supplemental output filenames")
    args = parser.parse_args()
    root = args.root.resolve()
    dest = (args.output_dir or root / "results/revision2/40_supplement").resolve()
    require(dest not in (root, root / "results", root / "results/revision2",
                         root / "results/annual_audit"),
            "Refusing output into a repository source/results root")
    require(not (args.overwrite and args.check_only),
            "Choose either --overwrite or --check-only")
    text_outputs, diurnal = outputs(root)
    figs = [f"Figure_{label}_diurnal_{scenario}.{ext}"
            for scenario, label, _ in SCENARIOS for ext in FIG_EXT]
    if args.check_only:
        for filename, content in text_outputs.items():
            path = dest / filename
            require(path.is_file(), f"Missing Step 40 output: {path}")
            require(path.read_text(encoding="utf-8") == content,
                    f"Step 40 output differs from current Step 28/29 source: {path}")
        for f in figs:
            path = dest / f
            require(path.is_file() and path.stat().st_size > 1000,
                    f"Missing/empty plot: {path}")
        print(f"PASS: {len(text_outputs)} exact text artifacts, {len(figs)} non-empty "
              "figures, 216 Step 29-aligned hourly summaries; no files modified")
        return
    paths = [dest / name for name in (*text_outputs.keys(), *figs)]
    if not args.overwrite:
        require(not any(p.exists() for p in paths),
                "Step 40 outputs already exist; use --check-only or explicit --overwrite")
    dest.mkdir(parents=True, exist_ok=True)
    for filename, content in text_outputs.items():
        (dest / filename).write_text(content, encoding="utf-8", newline="")
    for scenario, label, description in SCENARIOS:
        render_figure(diurnal, scenario, label, description, dest)
    print(f"PASS: wrote {len(paths)} Step 40 files into {dest}; originals untouched")


if __name__ == "__main__":
    main()
