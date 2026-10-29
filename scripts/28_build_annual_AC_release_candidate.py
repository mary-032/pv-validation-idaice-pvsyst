#!/usr/bin/env python3
"""Stage 28: read-only-source annual AC release-candidate packaging.

Uses exact Step 26 hourly measurements/model outputs and Step 27 clock evidence.
Writes new 28_* files only. NEVER changes the historical annual canonical data
or the frozen shading analysis. Fixed-CET is a CONDITIONAL working hypothesis.

Run from project root:
  .\\.venv313\\Scripts\\python.exe .\\scripts\\28_build_annual_AC_release_candidate.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_N = 4478
EXPECTED_ENERGY = {"A": 3648.540780, "B": 4230.834711, "C": 2809.8078}
PRIMARY = "fixed_CET_hypothesis"
SENSITIVITY = "civil_unshifted"
TABLE = "IDA ICE hourly Table, interval-end"
PV = "PVsyst E_Grid"
FILES = [
    "23_annual_AC_channel_comparison_hourly.csv",
    "26_annual_AC_all_systems_hourly.csv",
    "26_annual_AC_all_systems_metrics.csv",
    "26_annual_AC_all_systems_paired_CI30d.csv",
    "26_annual_AC_source_QC.csv",
    "26_IDA_hourly_mean_normalized.csv",
    "27_RISE_GTIsolar_noon_summary.csv",
]
NUMERIC = ["P_measured_W", "GTI_measured_Wm2", "IDA_hourly_table_end_aligned_W", "PVsyst_EGrid_W"]


def insist(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def metrics_one(x: pd.DataFrame, value: str) -> dict:
    m = x["P_measured_W"].to_numpy(float)
    y = x[value].to_numpy(float)
    e = y - m
    denom = m.mean()
    ss_res = np.sum(e * e)
    ss_tot = np.sum((m - denom) ** 2)
    return {
        "n": len(m),
        "measured_kWh": m.sum() / 1000,
        "simulated_kWh": y.sum() / 1000,
        "RMSE_W": float(np.sqrt(np.mean(e * e))),
        "MAE_W": float(np.mean(np.abs(e))),
        "MBE_W": float(e.mean()),
        "CVRMSE_pct": float(100 * np.sqrt(np.mean(e * e)) / denom),
        "energy_bias_pct": float(100 * e.sum() / m.sum()),
        "R2": float(1 - ss_res / ss_tot),
    }


def assert_metric_reproduced(ref: pd.Series, new: dict, sys: str, scn: str, label: str):
    for k, v in new.items():
        old = float(ref[k])
        insist(np.isclose(old, v, rtol=1e-7, atol=0.00002),
               f"Mismatch {sys} {scn} {label} {k}: expected {old}, got {v}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    source = args.root / "results" / "annual_audit"
    insist(source.is_dir(), f"Annual audit directory not found: {source}")
    paths = {x: source / x for x in FILES}
    for name, path in paths.items():
        insist(path.exists(), f"Missing source file: {path}")
    df = pd.read_csv(paths["26_annual_AC_all_systems_hourly.csv"])
    tab = pd.read_csv(paths["26_annual_AC_all_systems_metrics.csv"])
    ci = pd.read_csv(paths["26_annual_AC_all_systems_paired_CI30d.csv"])
    qc = pd.read_csv(paths["26_annual_AC_source_QC.csv"])
    noon = pd.read_csv(paths["27_RISE_GTIsolar_noon_summary.csv"])

    insist(len(df) == 2 * 3 * EXPECTED_N, f"Unexpected row count {len(df)}")
    insist(set(df.system) == {"A", "B", "C"}, "Unexpected systems")
    insist(set(df.scenario) == {PRIMARY, SENSITIVITY}, "Unexpected clock scenarios")
    insist(not df.duplicated(["scenario", "system", "physical_interval_start_local"]).any(),
           "Duplicate physical hour within a system/scenario")
    insist(df[NUMERIC].notna().all().all(), "Missing comparison values")
    insist((df["power_valid_10min"] == 6).all(), "Not every hour has six measured samples")
    insist((df["ida_time_h_table_end"] >= 1).all(), "Invalid table end indices")
    insist(len(qc) == 6 and (qc.table_values_missing == 0).all(), "Step 26 source QC failure")
    insist((qc.adjacent_sample_crosscheck_max_abs_W <= 0.051).all(), "IDA Table export/QC mismatch")
    insist(set(noon.season) == {"CET", "CEST"}, "Missing Step 27 seasonal evidence")
    insist(int(noon.n_days_with_positive_GTI.sum()) >= 360, "Unusually sparse GTI noon audit")
    insist(set(ci.IDA_channel).issuperset({TABLE}), "Missing Table bootstrap rows")

    dt_start = pd.to_datetime(df["physical_interval_start_local"])
    dt_end = pd.to_datetime(df["physical_interval_end_local"])
    r = pd.to_datetime(df["reference_synthetic_time"])
    lookup = pd.to_datetime(df["model_lookup_synthetic_time"])
    insist((dt_end - dt_start == pd.Timedelta(hours=1)).all(), "Inconsistent hour durations")
    lookup_diff = ((lookup - r) / pd.Timedelta(hours=1)).to_numpy(float)
    summer = df.clock_CEST.astype(str).str.lower().eq("true").to_numpy(bool)
    primary = (df.scenario == PRIMARY).to_numpy(bool)
    expected = np.where(primary & summer, -1.0, 0.0)
    insist(np.array_equal(lookup_diff, expected), "Clock mapping differs from 0 winter / -1 summer")
    table_idx_expected = 1 + ((lookup - pd.Timestamp("2021-01-01")) / pd.Timedelta(hours=1)).to_numpy(float)
    insist(np.array_equal(df.ida_time_h_table_end.to_numpy(float), table_idx_expected),
           "IDA Table interval-end index no longer equals model lookup + 1")

    keys = ["system", "physical_interval_start_local"]
    a = df.loc[df.scenario == PRIMARY].sort_values(keys).reset_index(drop=True)
    b = df.loc[df.scenario == SENSITIVITY].sort_values(keys).reset_index(drop=True)
    insist(a[keys].equals(b[keys]), "Primary and sensitivity have different observed-hour cohorts")
    for v in ["P_measured_W", "GTI_measured_Wm2", "reference_synthetic_time"]:
        if v == "reference_synthetic_time":
            insist(a[v].equals(b[v]), "Reference synthetic time differs")
        else:
            insist(np.array_equal(a[v].to_numpy(), b[v].to_numpy()),
                   f"Measured source differs between scenarios: {v}")

    calculations = []
    primary_ci = []
    for scn in [PRIMARY, SENSITIVITY]:
        for s in ["A", "B", "C"]:
            z = df[(df.scenario == scn) & (df.system == s)]
            insist(len(z) == EXPECTED_N, f"{s} {scn} has {len(z)} hours instead of 4478")
            energy = z.P_measured_W.sum() / 1000
            insist(np.isclose(energy, EXPECTED_ENERGY[s], atol=0.001),
                   f"Measured energy changed for {s}: {energy:.6f}")
            row_measured = z[["physical_interval_start_local"]].drop_duplicates()
            insist(len(row_measured) == EXPECTED_N, "Unexpected number of unique observed hours")
            for label, col in [(TABLE, "IDA_hourly_table_end_aligned_W"), (PV, "PVsyst_EGrid_W")]:
                item = tab[(tab.system == s) & (tab.scenario == scn) & (tab.output == label)]
                insist(len(item) == 1, f"Missing unique reported metrics for {s}/{scn}/{label}")
                computed = metrics_one(z, col)
                assert_metric_reproduced(item.iloc[0], computed, s, scn, label)
                calculations.append({"system": s, "scenario": scn, "output": label, **computed})
            bb = ci[(ci.system == s) & (ci.scenario == scn) & (ci.IDA_channel == TABLE)]
            insist(len(bb) == 1, f"Missing paired CI for {s}/{scn}")
            ide = metrics_one(z, "IDA_hourly_table_end_aligned_W")["RMSE_W"]
            pve = metrics_one(z, "PVsyst_EGrid_W")["RMSE_W"]
            insist(np.isclose(bb.iloc[0].delta_RMSE_IDA_minus_PVsyst_W, ide-pve, atol=0.0001),
                   f"Bootstrap point estimate inconsistent for {s}/{scn}")
            if scn == PRIMARY:
                primary_ci.append(bb.iloc[0].to_dict())

    release_cols = ["system", "physical_interval_start_local", "physical_interval_end_local",
                    "reference_synthetic_time", "model_lookup_synthetic_time", "clock_CEST",
                    "power_valid_10min", "GTI_measured_Wm2", "P_measured_W",
                    "ida_time_h_table_end", "IDA_hourly_table_end_aligned_W", "PVsyst_EGrid_W"]
    a[release_cols].to_csv(source / "28_annual_AC_primary_fixed_CET.csv", index=False, float_format="%.9f")
    b[release_cols].to_csv(source / "28_annual_AC_sensitivity_civil_unshifted.csv", index=False, float_format="%.9f")
    out_stats = pd.DataFrame(calculations)
    out_stats.to_csv(source / "28_annual_AC_primary_and_sensitivity_metrics.csv", index=False, float_format="%.9f")
    pd.DataFrame(primary_ci).to_csv(source / "28_annual_AC_primary_CI30d.csv", index=False, float_format="%.9f")

    fingerprints = {name: {"sha256": sha(path), "bytes": path.stat().st_size}
                    for name, path in paths.items()}
    manifest = {
        "status": "RELEASE_CANDIDATE_NOT_FINAL_OR_LOCKED",
        "primary_clock_hypothesis": PRIMARY,
        "mandatory_alternative": SENSITIVITY,
        "series": {"IDA": "Hourly Table produced_p, preceding hour (interval end)",
                   "PVsyst": "E_Grid, interval-start source", "RISE": "Six 10-min samples/hour"},
        "cohort": {"per_system_hours": EXPECTED_N, "systems": ["A", "B", "C"],
                    "mask": "solar elevation >0 at measured interval START",
                    "physical_period": "June 2020 - May 2021"},
        "clock_interpretation": "RISE source labels assessed as CET/CEST; simulation standard time; independently suggested by measured GTI centroid, not authenticated by logger documentation",
        "important_caveats": [
            "No original RISE logger time or sampling documentation was available.",
            "Ten-minute raw workbook contains 52,560 regular records per system and no duplicate civil timestamps; its time handling may already have been regularized.",
            "PVsyst imported .MET has HourShift=-1; do not apply it again to exported E_Grid.",
            "GTI-weighted solar-noon centroid is a weather-dependent sanity check, not exact noon observation.",
            "Model ranking reverses under alternative unshifted civil clock; both scenarios must be disclosed.",
            "IDA hourly Table closely matches adjacent sampled output mean; this does not prove native subhourly numerical integration.",
            "IDA produced_p versus inverter_o physical meter boundary remains a sensitivity limitation.",
            "This step does not update historical annual master outputs or frozen shading results."
        ],
        "pvsyst_weather_import_sources_missing": ["Meteo_89_PD.csv", "pvsyst Rise project.MEF"],
        "primary_30day_bootstrap": "Resampled CI carried from verified Step 26, not rerun in Step 28",
        "step26_table_export_sha256": qc.groupby("system").source_sha256.first().to_dict(),
        "source_fingerprints": fingerprints,
        "created_by": "scripts/28_build_annual_AC_release_candidate.py",
        "audit_date": "2026-10-29",
    }
    (source / "28_annual_AC_release_candidate_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Step 28 — annual AC release candidate (not final)", "",
        "The selected working primary comparison is fixed-CET model lookup relative to",
        "a CET/CEST RISE measurement clock. **It is not independently verified from original logger records.**", "",
        "## Numerically reproduced release-candidate results", "",
        "|System|IDA hourly Table RMSE W|PVsyst RMSE W|IDA−PVsyst W|95% bootstrap CI W|",
        "|---|---:|---:|---:|---|",
    ]
    for s in ["A", "B", "C"]:
        x = out_stats[(out_stats.system == s) & (out_stats.scenario == PRIMARY)]
        idrm = x.loc[x.output == TABLE, "RMSE_W"].iloc[0]
        pvrm = x.loc[x.output == PV, "RMSE_W"].iloc[0]
        c = next(i for i in primary_ci if i["system"] == s)
        lines.append(f"|{s}|{idrm:.2f}|{pvrm:.2f}|{idrm-pvrm:+.2f}|[{c['CI95_low_W']:+.2f}, {c['CI95_high_W']:+.2f}]|")
    lines += ["", "## Quality gates passed", "",
              "- 4,478 shared and fully observed measured hourly records per system; measured energy unchanged.",
              "- Two clock scenarios operate on exactly the same physical reference rows.",
              "- IDA Table values use interval-end indices; power metrics reproduce Step 26.",
              "- Step 26 30-day paired uncertainty reproduces the reported RMSE differences.",
              "- No shading or historical annual datasets were modified.", "",
              "## Scientific qualifications", "",
              "- Fixed CET is the supported **working** interpretation only. The ranking reverses under the civil-unshifted sensitivity; present both.",
              "- The raw RISE 10-minute workbook contains regular records across DST with no duplicates, which prevents identifying the original logger behavior directly.",
              "- Step 27 GTI solar centroid has CET residual +3.6 min and CEST residual −0.9 min relative to expected civil solar noon, but depends on weather and reconstructed timestamps.",
              "- PVsyst MET has a recorded one-hour import shift which is already applied to the meteorological labels; the missing original CSV and MEF prevent a full import audit.",
              "- IDA hourly Table `produced_p` is retained as the provisional electrical-system meter comparison boundary; document the `inverter_o` sensitivity.",
              "- Solar elevation evaluated at the START of each selected measured interval; a midpoint convention changes the cohort.", "",
              "## Before calling results final", "",
              "- Verify source fingerprints and inspect the generated primary/sensitivity tables.",
              "- Keep Step 26 and 27 source outputs; stage only 28_* files in version control.",
              "- Document the remaining clock and AC metering uncertainties in Methods/Limitations.",
              "- Do not replace or rerun the frozen shading analysis.", ""]
    (source / "28_annual_AC_release_candidate_note.md").write_text("\n".join(lines), encoding="utf-8")
    print("Step 28 PASS — all source, clock, interval-end, cohort and metric checks passed")
    print("Generated six 28_* files in:", source)
    for s in ["A", "B", "C"]:
        z = out_stats[(out_stats.system == s) & (out_stats.scenario == PRIMARY)]
        idrm = z[z.output == TABLE].RMSE_W.iloc[0]
        pvrm = z[z.output == PV].RMSE_W.iloc[0]
        print(f"  {s}: measured {EXPECTED_N} h, IDA {idrm:.2f} W; PVsyst {pvrm:.2f} W")
    print("Status: release candidate; clock and measurement-boundary assumptions remain disclosed")


if __name__ == "__main__":
    main()
