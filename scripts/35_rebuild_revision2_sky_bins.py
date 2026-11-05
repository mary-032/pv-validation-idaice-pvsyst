#!/usr/bin/env python3
"""Rebuild Revision 2 sky-index statistics/Figure 3 from authoritative Step 28 AC.

No Step 30 or Step 31 intermediate is read. Inputs (never modified):
  results/annual_audit/28_annual_AC_primary_fixed_CET.csv
  results/annual_audit/28_annual_AC_sensitivity_civil_unshifted.csv
  derived_data/annual_unshaded_analysis.csv  (ONLY pre-established Eext/AOI)
  config.json                           (site/bin bounds)

The original canonical geometry was built on *physical* 2020/2021 dates
and subsequently stored with synthetic 2021 labels. Re-map June-Dec to
physical year 2020 to join on the physical START of the measured interval.
Use Step 28 measured GTI, not legacy GTI/power, and do not infer the clock
from model errors. No residual-dependent exclusions are applied.

nMBE definition matches Revision2_clean_20261104.pdf equations 3-5:
  MBE = mean(P_sim - P_meas)
  nMBE[%] = 100 * MBE / mean(P_meas)
           = 100 * sum(P_sim - P_meas) / sum(P_meas)
Both models use identical measured hours for a given bin.

Run in project root:
  python scripts/35_rebuild_revision2_sky_bins.py
  python scripts/35_rebuild_revision2_sky_bins.py --check-only

--check-only validates committed CSVs against freshly derived values without
rewriting files. Rendering is done only on a normal run (not check-only).
The deterministic CSVs constitute the numerical release; plot bytes can vary
with installed matplotlib/font versions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STEP28_FILES = {
    "fixed_CET_hypothesis": "28_annual_AC_primary_fixed_CET.csv",
    "civil_unshifted": "28_annual_AC_sensitivity_civil_unshifted.csv",
}
MODELS = {"IDA ICE": "IDA_hourly_table_end_aligned_W", "PVsyst": "PVsyst_EGrid_W"}
SYSTEMS = ("A", "B", "C")
SELECTIONS = ("Eext_positive", "Eext_positive_AOI_lt80", "Eext_gt100_AOI_lt80")
PRIMARY_SCENARIO = "fixed_CET_hypothesis"
PRIMARY_SELECTION = "Eext_positive_AOI_lt80"
# Original MATLAB / Step 32 convention: IDA = green, PVsyst = blue.
COLORS = {"IDA ICE": "#77AC30", "PVsyst": "#0072BD"}
SAMPLE_N = 4478
ALL_STATS_FIELDS = [
    "scenario", "system", "selection", "model", "sky_bin",
    "kt_lower_inclusive", "kt_upper_exclusive", "n", "mean_measured_W",
    "mean_simulated_W", "RMSE_W", "MAE_W", "MBE_W", "CVRMSE_pct",
    "nMBE_pct", "energy_bias_pct", "measured_kWh", "simulated_kWh",
]
QC_FIELDS = [
    "scenario", "system", "n_annual_AC_hours", "n_Eext_positive",
    "n_AOI_lt80_Eext_positive", "n_Eext_gt100_AOI_lt80",
    "n_Eext_zero_or_nonpositive", "n_ineligible_AOI_gte80_among_Eext_positive",
    "n_kt_gt1", "n_kt_gt2", "n_unclassified_Eext_positive",
    "n_physical_dates_with_AC_hours", "n_physical_days_without_AC_hours",
    "missing_day_labels", "measured_kWh_annual_AC",
    "pct_annual_measured_energy_in_primary_sky_bins",
]
DATE_FIELDS = ["system", "physical_date", "n_selected_AC_hours", "measured_kWh_selected_AC", "has_selected_AC_hour"]
OUTPUT_FILES = {
    "35_sky_bin_statistics_all_scenarios.csv": ALL_STATS_FIELDS,
    "35_Figure3_primary_source_statistics.csv": ALL_STATS_FIELDS,
    "35_sky_bin_QC.csv": QC_FIELDS,
    "35_annual_AC_date_coverage.csv": DATE_FIELDS,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_inputs(root: Path):
    config_path = root / "config.json"
    canonical_path = root / "derived_data/annual_unshaded_analysis.csv"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    boundaries = [
        (x["name"], float(x["min"]), math.inf if x["max"] is None else float(x["max"]))
        for x in config["sky_bins"]
    ]
    require(len(boundaries) == 5 and boundaries[0][1] == 0.0,
            "Expected five specified sky-index bins")
    require(boundaries[-1][2] == math.inf, "Last bin must have no upper bound")
    require(all(math.isclose(boundaries[i][2], boundaries[i+1][1]) for i in range(4)),
            "Gap or overlap in index bins")
    require(config["site"]["timezone"] == "Europe/Stockholm", "Unexpected site timezone")

    # Read *only* original established geometry, never historical GTI or AC.
    geometry = pd.read_csv(canonical_path, usecols=["timestamp", "system", "Eext_tilt_Wm2", "AOI_deg"])
    synthetic = pd.to_datetime(geometry.pop("timestamp"), errors="raise")
    require(synthetic.dt.year.eq(2021).all(), "Legacy geometry has unexpected year")
    physical = synthetic.copy()
    mask_year = physical.dt.month.ge(6)
    physical.loc[mask_year] = physical.loc[mask_year] - pd.DateOffset(years=1)
    geometry["physical_interval_start_local"] = physical
    require(not geometry.duplicated(["system", "physical_interval_start_local"]).any(),
            "Duplicate canonical geometry keys")
    require(set(geometry.system) == set(SYSTEMS), "Unexpected canonical systems")
    # Same instrument position/plane is used for all systems.
    spread = geometry.groupby("physical_interval_start_local")[["Eext_tilt_Wm2", "AOI_deg"]].agg(
        lambda v: v.max() - v.min())
    require(np.nanmax(spread.to_numpy(float)) < 1e-6,
            "Legacy geometry should be identical across all three systems")
    require(np.isfinite(geometry[["Eext_tilt_Wm2", "AOI_deg"]]).all().all(),
            "Nonfinite canonical geometry")
    require((geometry.Eext_tilt_Wm2 >= -1e-8).all(), "Negative Eext denominator")

    datasets = {}
    for scenario, basename in STEP28_FILES.items():
        path = root / "results/annual_audit" / basename
        d = pd.read_csv(path, parse_dates=["physical_interval_start_local"])
        needed = {"system", "physical_interval_start_local", "power_valid_10min",
                  "P_measured_W", "GTI_measured_Wm2", *MODELS.values()}
        require(needed.issubset(d.columns), f"Missing Step 28 columns: {path}")
        require(not d.duplicated(["system", "physical_interval_start_local"]).any(),
                f"Duplicate Step 28 reference hours: {scenario}")
        for system in SYSTEMS:
            block = d.loc[d.system.eq(system)]
            require(len(block) == SAMPLE_N, f"Unexpected Step 28 sample size: {scenario}/{system}")
            require(block.power_valid_10min.eq(6).all(), "Incomplete original 10-minute AC hour")
        require(np.isfinite(d[["P_measured_W", "GTI_measured_Wm2", *MODELS.values()]]).all().all(),
                f"Nonfinite Step 28 measured/model values: {scenario}")
        merged = d.merge(geometry, on=["system", "physical_interval_start_local"],
                         how="left", validate="one_to_one", indicator=True)
        require(merged._merge.eq("both").all(), f"Incomplete geometry join: {scenario}")
        merged = merged.drop(columns=["_merge"])
        denom = merged.Eext_tilt_Wm2.to_numpy(float)
        gti = merged.GTI_measured_Wm2.to_numpy(float)
        merged["kt_tilt"] = np.divide(gti, denom,
            out=np.full(len(merged), np.nan), where=denom > 0)
        datasets[scenario] = merged.sort_values(
            ["system", "physical_interval_start_local"]).reset_index(drop=True)
    columns = ["system", "physical_interval_start_local", "P_measured_W", "GTI_measured_Wm2"]
    first = datasets[PRIMARY_SCENARIO][columns]
    second = datasets["civil_unshifted"][columns]
    require(first.equals(second), "Clock sensitivity changes measured physical rows")
    return datasets, boundaries, {"source_files": {
        str(p.relative_to(root)): sha256(p)
        for p in [config_path, canonical_path] + [
            root / "results/annual_audit" / name for name in STEP28_FILES.values()
        ]
    }}


def group_metrics(m: np.ndarray, p: np.ndarray) -> dict:
    """Sign and denominator match the revised manuscript, not MATLAB n-1."""
    require(len(m) == len(p) and len(m) > 1, "Invalid paired data")
    require(np.isfinite(m).all() and np.isfinite(p).all(), "Invalid paired values")
    msum = float(m.sum())
    require(msum > 0, "Cannot normalise a zero-measured-power bin")
    d = p - m
    n = len(m)
    mean_m = msum / n
    rmse = float(np.sqrt(np.mean(d * d)))
    mbe = float(d.mean())
    nmb = float(100 * d.sum() / msum)
    return {
        "n": n, "mean_measured_W": mean_m,
        "mean_simulated_W": float(p.mean()),
        "RMSE_W": rmse, "MAE_W": float(np.mean(np.abs(d))),
        "MBE_W": mbe, "CVRMSE_pct": 100 * rmse / mean_m,
        "nMBE_pct": nmb, "energy_bias_pct": nmb,
        "measured_kWh": msum / 1000,
        "simulated_kWh": float(p.sum() / 1000),
    }


def build_tables(datasets: dict, boundaries: list):
    all_rows = []
    qc_rows = []
    date_rows = []
    full_dates = pd.date_range("2020-06-01", "2021-05-31", freq="D")
    for scenario, d in datasets.items():
        for system in SYSTEMS:
            block = d.loc[d.system.eq(system)].copy()
            require(len(block) == SAMPLE_N, f"Unexpected source cohort {scenario}/{system}")
            e = block.Eext_tilt_Wm2.to_numpy(float)
            aoi = block.AOI_deg.to_numpy(float)
            kt = block.kt_tilt.to_numpy(float)
            m = block.P_measured_W.to_numpy(float)
            positive = e > 0
            primary = positive & (aoi < 80)
            selections = {
                "Eext_positive": positive,
                "Eext_positive_AOI_lt80": primary,
                "Eext_gt100_AOI_lt80": (e > 100) & (aoi < 80),
            }
            coverage = block.groupby(block.physical_interval_start_local.dt.normalize()).agg(
                n=("P_measured_W", "size"), power_sum=("P_measured_W", "sum"))
            missing_days = []
            for day in full_dates:
                if day in coverage.index:
                    n = int(coverage.loc[day, "n"])
                    kwh = float(coverage.loc[day, "power_sum"] / 1000)
                else:
                    n, kwh = 0, 0.0
                    missing_days.append(day.date().isoformat())
                if scenario == PRIMARY_SCENARIO:
                    date_rows.append({"system": system, "physical_date": day.date().isoformat(),
                                      "n_selected_AC_hours": n, "measured_kWh_selected_AC": kwh,
                                      "has_selected_AC_hour": int(n > 0)})
            if scenario == PRIMARY_SCENARIO:
                require(sum(x["n_selected_AC_hours"] for x in date_rows
                            if x["system"] == system) == SAMPLE_N,
                        f"Date counts do not sum to annual cohort: {system}")
            for sel_name, sel in selections.items():
                assert np.isfinite(kt[sel]).all(), "Invalid positive-Eext index"
                assert (kt[sel] >= 0).all(), "Negative tilted index not classified"
                classified = np.zeros(len(block), dtype=bool)
                for label, lo, hi in boundaries:
                    idx = sel & (kt >= lo) & (kt < hi)
                    classified |= idx
                    for model, column in MODELS.items():
                        out = group_metrics(m[idx], block[column].to_numpy(float)[idx])
                        all_rows.append({"scenario": scenario, "system": system,
                                         "selection": sel_name, "model": model,
                                         "sky_bin": label, "kt_lower_inclusive": lo,
                                         "kt_upper_exclusive": "" if math.isinf(hi) else hi,
                                         **out})
                require(int(classified.sum()) == int(sel.sum()),
                        f"Unclassified index for {scenario}/{system}/{sel_name}")
            qc_rows.append({
                "scenario": scenario, "system": system,
                "n_annual_AC_hours": len(block),
                "n_Eext_positive": int(positive.sum()),
                "n_AOI_lt80_Eext_positive": int(primary.sum()),
                "n_Eext_gt100_AOI_lt80": int(selections["Eext_gt100_AOI_lt80"].sum()),
                "n_Eext_zero_or_nonpositive": int((~positive).sum()),
                "n_ineligible_AOI_gte80_among_Eext_positive": int((positive & (aoi >= 80)).sum()),
                "n_kt_gt1": int((kt > 1).sum()),
                "n_kt_gt2": int((kt > 2).sum()),
                "n_unclassified_Eext_positive": 0,
                "n_physical_dates_with_AC_hours": len(coverage),
                "n_physical_days_without_AC_hours": len(missing_days),
                "missing_day_labels": ";".join(missing_days),
                "measured_kWh_annual_AC": float(m.sum() / 1000),
                "pct_annual_measured_energy_in_primary_sky_bins": float(100 * m[primary].sum()/m.sum()),
            })
    all_stats = pd.DataFrame(all_rows)[ALL_STATS_FIELDS]
    primary_stats = all_stats.loc[(all_stats.scenario == PRIMARY_SCENARIO) &
                                  (all_stats.selection == PRIMARY_SELECTION)].copy()
    qc = pd.DataFrame(qc_rows)[QC_FIELDS]
    dates = pd.DataFrame(date_rows)[DATE_FIELDS]
    require(len(all_stats) == 180 and len(primary_stats) == 30 and len(qc) == 6,
            "Unexpected output shape")
    for (scenario, sys, selection, bin_name), g in all_stats.groupby(
            ["scenario", "system", "selection", "sky_bin"]):
        require(len(g) == 2 and g.n.nunique() == 1,
                f"Models do not share bin rows: {scenario}/{sys}/{selection}/{bin_name}")
    for sys in SYSTEMS:
        sel = qc.loc[qc.scenario.eq(PRIMARY_SCENARIO) & qc.system.eq(sys)].iloc[0]
        require(int(sel.n_AOI_lt80_Eext_positive) == 3593,
                f"Unexpected AOI<80 count for {sys}")
        require(int(sel.n_Eext_positive) == 3932,
                f"Unexpected positive-Eext count for {sys}")
        require(int(sel.n_physical_days_without_AC_hours) == 1 and
                sel.missing_day_labels == "2020-12-31",
                f"Unexpected physical date coverage for {sys}")
    return all_stats, primary_stats, qc, dates


def render_csv(fields: list[str], rows: pd.DataFrame) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(fields)
    for row in rows.itertuples(index=False, name=None):
        row_map = dict(zip(rows.columns, row))
        writer.writerow([format(float(row_map[k]), ".9f") if isinstance(row_map[k],
                         (float, np.floating)) else row_map[k] for k in fields])
    return buffer.getvalue()


def check_csv(path: Path, expected: str) -> None:
    require(path.is_file(), f"Expected output missing: {path}")
    generated = list(csv.DictReader(io.StringIO(expected)))
    with path.open(encoding="utf-8", newline="") as f:
        actual = list(csv.DictReader(f))
    require(len(generated) == len(actual), f"Row-count mismatch: {path}")
    for i, (a, b) in enumerate(zip(generated, actual), start=2):
        require(a.keys() == b.keys(), f"Column mismatch at {path}:{i}")
        for key in a:
            if a[key] == b[key]:
                continue
            try:
                require(math.isclose(float(a[key]), float(b[key]),
                       rel_tol=1e-9, abs_tol=2e-7),
                       f"Metric discrepancy: {path}:{i}/{key}: {a[key]} vs {b[key]}")
            except ValueError:
                raise AssertionError(f"Text mismatch: {path}:{i}/{key}")


def figure(df: pd.DataFrame, outdir: Path, basename: str,
           scenario: str, bins: list, status: str) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    chart = df.loc[(df.scenario == scenario) & (df.selection == PRIMARY_SELECTION)]
    require(len(chart) == 30, "Expected exactly 30 figure rows")
    n = {sys: chart.loc[chart.model.eq("IDA ICE") & chart.system.eq(sys), "n"].sum()
         for sys in SYSTEMS}
    require(all(x == 3593 for x in n.values()), "Figure population changed")
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42,
                         "ps.fonttype": 42, "svg.fonttype": "none"})
    fig, axs = plt.subplots(1, 2, figsize=(12.6, 5.35))
    fig.subplots_adjust(left=0.08, right=0.99, top=0.85, bottom=0.24, wspace=0.25)
    centers = np.arange(15, dtype=float)
    offset, width = 0.175, 0.33
    ylabel = (("CVRMSE_pct", "CV(RMSE) [%]", "(a)"),
              ("nMBE_pct", "nMBE [%]", "(b)"))
    for ax, (key, label, panel) in zip(axs, ylabel):
        for model, shift in (("IDA ICE", -offset), ("PVsyst", offset)):
            data = chart.loc[chart.model.eq(model)].set_index(["sky_bin", "system"])
            values = [float(data.loc[(b[0], sys), key]) for b in bins for sys in SYSTEMS]
            ax.bar(centers + shift, values, width=width,
                   color=COLORS[model], edgecolor="#222222", linewidth=0.6, zorder=3)
        ax.set_xlim(-.65, 14.65)
        ax.set_xticks(centers)
        ax.set_xticklabels(SYSTEMS * len(bins), fontsize=10)
        ax.set_ylabel(label, fontsize=12)
        ax.grid(axis="y", alpha=.24, linewidth=.6)
        ax.set_axisbelow(True)
        for v in (2.5,5.5,8.5,11.5):
            ax.axvline(v, color="#444444", linewidth=.7)
        for i, (bin_name, lo, hi) in enumerate(bins):
            text = (f"{lo:g}–<{hi:g}" if math.isfinite(hi) else f"≥{lo:g}")
            ax.text(3 * i + 1, -.145, text, transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=9.3, clip_on=False)
        ax.text(.015,.98,panel,transform=ax.transAxes,va="top",ha="left",
                weight="bold",fontsize=12)
        for spine in ax.spines.values():
            spine.set_linewidth(.8)
    # Dynamic limits ensure both scenarios can be shown without clipping.
    y_max = max(180, math.ceil(chart.CVRMSE_pct.max() / 20 + 1) * 20)
    axs[0].set_ylim(0, y_max)
    vals = chart.nMBE_pct
    rng_min = math.floor(min(-5, vals.min() - 5) / 10) * 10
    rng_max = math.ceil(max(5, vals.max() + 5) / 10) * 10
    axs[1].set_ylim(rng_min, rng_max)
    axs[1].axhline(0, color="#333333", linewidth=.9)
    fig.legend(handles=[Patch(facecolor=COLORS[m], edgecolor="#222222", label=m)
                        for m in MODELS], loc="upper center", ncol=2,
               bbox_to_anchor=(.5,.985),frameon=False,fontsize=11)
    fig.text(.5,.065, "Tilted irradiance-index regime, kₜ,tilt  |  A/B/C = PV system",
             ha="center",fontsize=9)
    fig.text(.5,.025, status, ha="center",fontsize=8.0,color="#555555")
    paths = []
    for ext in ("pdf", "svg", "png"):
        dst = outdir / f"{basename}.{ext}"
        fig.savefig(dst, dpi=260, bbox_inches="tight", facecolor="white")
        paths.append(dst.name)
    plt.close(fig)
    return paths


def run(root: Path, outdir: Path, check_only: bool) -> None:
    datasets, bins, provenance = read_inputs(root)
    stats, primary, qc, dates = build_tables(datasets, bins)
    outputs = [stats, primary, qc, dates]
    if not check_only:
        outdir.mkdir(parents=True, exist_ok=True)
    for (filename, fields), table in zip(OUTPUT_FILES.items(), outputs):
        content = render_csv(fields, table)
        if check_only:
            check_csv(outdir / filename, content)
            print(f"CHECK PASS {filename}: {len(table)} rows")
        else:
            (outdir / filename).write_text(content, encoding="utf-8", newline="")
            print(f"WROTE {filename}: {len(table)} rows")
    if check_only:
        print("PASS: source-matched sky statistics and date coverage")
        return
    paths = []
    paths.extend(figure(stats, outdir, "35_Figure3_fixed_CET_AOI_lt80_CANDIDATE",
                        PRIMARY_SCENARIO, bins,
                        "Working clock hypothesis; kₜ,tilt is not observed cloud cover"))
    paths.extend(figure(stats, outdir, "35_Figure3_civil_unshifted_AOI_lt80_SENSITIVITY",
                        "civil_unshifted", bins,
                        "Alternative clock changes the relative accuracy ranking"))
    for name in OUTPUT_FILES:
        paths.append(name)
    manifest = {
        "status": "REVISION2_FIGURE3_CANDIDATE_NOT_FINAL",
        "script": "scripts/35_rebuild_revision2_sky_bins.py",
        "source_sha256": provenance["source_files"],
        "primary_clock": PRIMARY_SCENARIO,
        "alternative_clock": "civil_unshifted",
        "primary_selection": PRIMARY_SELECTION,
        "n_primary_selected_hours_per_system": 3593,
        "n_annual_matched_AC_hours_per_system": 4478,
        "nMBE_definition": "100 * sum(P_sim_W - P_meas_W) / sum(P_meas_W); denominator n; positive overproduction",
        "GTI_source": "Step28 GTI_measured_Wm2 (original RISE 10-min reconstruction)",
        "Eext_source": "existing legacy canonical Eext_tilt_Wm2, geometry only (physical interval start)",
        "AOI_rule": "AOI < 80 deg, Eext_tilt > 0 for primary plot",
        "sky_bins": [dict(name=name,lower_inclusive=lo,upper_exclusive=(None if math.isinf(hi) else hi))
                     for name,lo,hi in bins],
        "colors": COLORS,
        "missing_day": "2020-12-31 (no daylight-matched Step28 model output; do not impute)",
        "output_files": paths,
        "limitations": ["original RISE logger clock not independently verified",
                        "sky index is tilted GTI / extraterrestrial beam projection, not measured sky-cover class",
                        "original MATLAB TT_IDA.Eextt not authenticated",
                        "no formal within-bin paired model significance tests"],
    }
    (outdir / "35_Figure3_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("PASS: 180 scenario/filter/model/bin statistics, primary + clock-sensitivity figures")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="project root with config/data sources")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    outdir = (args.output_dir or root / "results/revision2").resolve()
    run(root, outdir, args.check_only)


if __name__ == "__main__":
    main()
