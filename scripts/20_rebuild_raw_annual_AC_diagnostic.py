"""Non-destructive annual raw-10-minute AC-power reconstruction DIAGNOSTIC.

Reads original RISE raw 10-minute measurements and authoritative Perez–Driesse
IDA ICE/PVsyst annual exports from the existing repository. Writes NEW files to
results/annual_audit/ only. Never changes derived_data, script 01, shading, or
annual legacy results. Do not promote one diagnostic time convention to the
primary analysis merely because it minimizes model RMSE.

Run from repo root:
    .\\.venv313\\Scripts\\python.exe scripts/20_rebuild_raw_annual_AC_diagnostic.py
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "annual_audit"
RAW = ROOT / "data" / "measured" / "annual" / "RISE_raw10min_389.xlsx"
LEGACY_READER = ROOT / "scripts" / "01_build_canonical_data.py"
STUDY_START = pd.Timestamp("2020-06-01 00:00:00")
STUDY_END = pd.Timestamp("2021-06-01 00:00:00")
TARGETS = {
    "A": (4478, 3648.541, 249.50, 252.46),
    "B": (4478, 4230.835, 335.11, 311.47),
    "C": (4478, 2809.808, 263.39, 245.00),
}
SHEET_NAMES = {"A": "system_3", "B": "system_8", "C": "system_9"}
RISE_IDS = {"A": "3", "B": "8", "C": "9"}


def physical_to_synthetic(ts):
    """Real Jun2020–May2021 timestamps -> synthetic 2021 wall clock (NO UTC)."""
    ts = pd.DatetimeIndex(ts)
    return pd.DatetimeIndex([t.replace(year=2021) for t in ts])


def synthetic_to_physical(ts):
    ts = pd.DatetimeIndex(ts)
    return pd.DatetimeIndex([t.replace(year=(2020 if t.month >= 6 else 2021)) for t in ts])


def convert_excel_time(series):
    """Read both native Excel datetimes and numerical Excel serial days."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_datetime(series, unit="D", origin="1899-12-30", errors="coerce").dt.round("min")
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=False)
    nonnull = series.dropna()
    if len(nonnull) and parsed.notna().sum() < len(nonnull) * 0.90:
        raise ValueError("Cannot confidently interpret raw RISE Time values; inspect workbook directly.")
    if getattr(parsed.dt, "tz", None) is not None:
        raise ValueError("Raw RISE timestamp has timezone; do not silently remove it.")
    return parsed.dt.round("min")


def load_raw(system, xls):
    name = SHEET_NAMES[system]
    if name not in xls.sheet_names:
        possibilities = [s for s in xls.sheet_names if s.lower() == name.lower()]
        if not possibilities:
            raise ValueError(f"No {name!r} sheet. Available: {xls.sheet_names}")
        name = possibilities[0]
    d = pd.read_excel(xls, sheet_name=name)
    d.columns = [str(x).strip() for x in d.columns]
    suffix = RISE_IDS[system]
    required = ["Time", f"Power_{suffix}", f"GTI_{suffix}"]
    if not set(required).issubset(d.columns):
        raise ValueError(f"Raw sheet {name}: expected {required}; found {d.columns.tolist()[:25]}")
    d = d[required].copy()
    d["physical_sample_time"] = convert_excel_time(d["Time"])
    for col in required[1:]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d[d["physical_sample_time"].notna()].copy()
    d = d[(d["physical_sample_time"] >= STUDY_START - pd.Timedelta(hours=2))
          & (d["physical_sample_time"] <= STUDY_END + pd.Timedelta(hours=2))].copy()
    if d.empty:
        raise ValueError(f"{name}: no raw records overlapping the physical study period")
    if d["physical_sample_time"].duplicated().any():
        duplicate = d[d["physical_sample_time"].duplicated(keep=False)].head(8)
        # Repeated physical civil hours can be meaningful at autumn DST. Preserve,
        # but document; don't silently deduplicate or infer an occurrence.
        print(f"  {system}: repeated raw civil timestamps (possible DST):\n{duplicate[['physical_sample_time']].to_string(index=False)}")
    if d[f"Power_{suffix}"].dropna().abs().quantile(0.99) > 15000:
        raise ValueError(f"{name} power magnitude unexpectedly > 15 kW; verify W units")
    d = d.rename(columns={f"Power_{suffix}": "P_measured_W", f"GTI_{suffix}": "GTI_measured_Wm2"})
    return d[["physical_sample_time", "P_measured_W", "GTI_measured_Wm2"]]


def to_hourly(d, group_convention):
    """Two independently specified interpretations of 10-minute logger labels.

    start_label: hh:00,...hh:50 describe the hour [hh:00,hh+1:00),
                 whose END timestamp is hh+1:00.
    end_label: hh:10,...hh+1:00 describe (hh:00,hh+1:00],
               whose END timestamp is hh+1:00.
    """
    x = d.copy()
    if group_convention == "sample_start":
        x["physical_timestamp"] = x["physical_sample_time"].dt.floor("h") + pd.Timedelta(hours=1)
    elif group_convention == "sample_end":
        x["physical_timestamp"] = x["physical_sample_time"].dt.ceil("h")
    else:
        raise ValueError(group_convention)
    x = x[(x["physical_timestamp"] > STUDY_START) & (x["physical_timestamp"] <= STUDY_END)].copy()
    g = x.groupby("physical_timestamp", sort=True)
    out = g.agg(P_measured_W=("P_measured_W", "mean"),
                GTI_measured_Wm2=("GTI_measured_Wm2", "mean"),
                sample_count=("physical_sample_time", "size"),
                power_valid_10min=("P_measured_W", "count"),
                GTI_valid_10min=("GTI_measured_Wm2", "count")).reset_index()
    out["timestamp"] = physical_to_synthetic(out["physical_timestamp"])
    if out["timestamp"].duplicated().any():
        raise ValueError("Raw hourly source becomes duplicate on the synthetic clock")
    return out


# Cache physical solar-position calls across all three systems and lag cases.
SOLAR_CACHE = {}


def solar_masks(physical_time, cfg):
    import pvlib
    site = cfg["site"]
    result = {}
    times = pd.DatetimeIndex(physical_time)
    for moment, offset in (("hour_end", 0), ("hour_midpoint", -30)):
        missing = [t for t in times.unique() if (moment, t) not in SOLAR_CACHE]
        if missing:
            wall = pd.DatetimeIndex(missing) + pd.to_timedelta(offset, unit="m")
            # Civil DST ambiguity: use standard time in the autumn fold.
            local = wall.tz_localize(site["timezone"], ambiguous=False, nonexistent="shift_forward")
            solar = pvlib.solarposition.get_solarposition(
                local, float(site["latitude"]), float(site["longitude"]),
                altitude=float(site["altitude_m"]))
            for t, sun in zip(missing, solar["apparent_elevation"].to_numpy(float) > 0):
                SOLAR_CACHE[(moment, t)] = bool(sun)
        result[f"astronomical_day_{moment}"] = np.array(
            [SOLAR_CACHE[(moment, t)] for t in times], dtype=bool)
    return result


def read_models(system):
    """Reuse EXISTING read functions, never modify their canonical outputs."""
    spec = importlib.util.spec_from_file_location("legacy_annual_readers_for_diagnostic", LEGACY_READER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    ida = module.read_ida(system)[["timestamp", "P_IDA_W"]].copy()
    pv = module.read_pvsyst(system)[["timestamp", "P_PVsyst_W"]].copy()
    for label, f in (("IDA ICE", ida), ("PVsyst", pv)):
        if f["timestamp"].duplicated().any():
            raise ValueError(f"Duplicate {label} timestamps")
    return ida.merge(pv, on="timestamp", how="inner", validate="one_to_one")


def stats(d, mask):
    selected = d.loc[mask].copy()
    fields = ["P_measured_W", "P_IDA_W", "P_PVsyst_W"]
    selected[fields] = selected[fields].apply(pd.to_numeric, errors="coerce")
    selected = selected.dropna(subset=fields)
    if selected.empty:
        return {"n":0, "measured_kWh":np.nan, "RMSE_IDA_W":np.nan,"RMSE_PVsyst_W":np.nan}
    m = selected["P_measured_W"].to_numpy(float)
    ida = selected["P_IDA_W"].to_numpy(float)
    pv = selected["P_PVsyst_W"].to_numpy(float)
    return {"n":len(selected), "measured_kWh":float(m.sum()/1000),
            "RMSE_IDA_W":float(np.sqrt(np.mean((ida-m)**2))),
            "RMSE_PVsyst_W":float(np.sqrt(np.mean((pv-m)**2))),
            "power_10min_coverage_min":int(selected["power_valid_10min"].min()),
            "power_10min_coverage_max":int(selected["power_valid_10min"].max())}


def main():
    for p in (RAW, LEGACY_READER, ROOT/"config.json"):
        if not p.is_file():
            raise FileNotFoundError(p)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
    rows=[]
    inventory=[]
    with pd.ExcelFile(RAW) as xls:
        for system in ("A", "B", "C"):
            print(f"\nSYSTEM {system}")
            raw = load_raw(system, xls)
            inventory.append({"system":system,"raw_rows":len(raw),
                "first_raw":raw["physical_sample_time"].min(),
                "last_raw":raw["physical_sample_time"].max(),
                "missing_raw_power":int(raw["P_measured_W"].isna().sum()),
                "duplicate_civil_labels":int(raw["physical_sample_time"].duplicated().sum())})
            models = read_models(system)
            for convention in ("sample_start", "sample_end"):
                base = to_hourly(raw, convention)
                for shift_h in (-1,0,1):
                    temp = base.copy()
                    # Shift measured source END timestamps, *not* simulations.
                    temp["timestamp"] = temp["timestamp"] + pd.Timedelta(hours=shift_h)
                    temp["physical_timestamp"] = temp["physical_timestamp"] + pd.Timedelta(hours=shift_h)
                    merged = models.merge(temp, on="timestamp", how="inner", validate="one_to_one")
                    if merged.empty:
                        raise ValueError("Annual measured/model merge returned zero rows")
                    sky = solar_masks(merged["physical_timestamp"], cfg)
                    for key,value in sky.items():
                        merged[key] = value
                    masks = {
                        "astro_hour_end":merged["astronomical_day_hour_end"],
                        "astro_midpoint":merged["astronomical_day_hour_midpoint"],
                        "measured_GTI_positive":merged["GTI_measured_Wm2"]>0,
                    }
                    for filter_name, selected in masks.items():
                        for coverage_name, coverage in (("any_valid",merged["power_valid_10min"]>0),
                                                        ("six_valid",merged["power_valid_10min"]==6)):
                            st = stats(merged, selected & coverage)
                            target = TARGETS[system]
                            rows.append({"system":system,"ten_min_timestamp_interpretation":convention,
                                "measurement_shift_hours":shift_h,"daytime_rule":filter_name,
                                "coverage_rule":coverage_name,"common_allhours":len(merged),
                                **st,"target_n":target[0],"target_measured_kWh":target[1],
                                "target_IDA_RMSE_W":target[2],"target_PVsyst_RMSE_W":target[3],
                                "delta_n":st["n"]-target[0],
                                "delta_measured_kWh":st["measured_kWh"]-target[1]})
    results = pd.DataFrame(rows)
    results.to_csv(OUTPUT/"20_raw_AC_alignment_candidates.csv", index=False)
    pd.DataFrame(inventory).to_csv(OUTPUT/"20_raw_measurement_inventory.csv", index=False)
    # This report deliberately does not select the smallest RMSE or
    # claim that the numerical targets have been recovered.
    nominal = results[(results["measurement_shift_hours"]==0)
                      & (results["coverage_rule"]=="any_valid")
                      & (results["daytime_rule"]=="astro_midpoint")]
    report=["# Step 20 — annual raw AC alignment diagnostic", "",
            "This is a diagnostic grid, NOT a finalized raw-reference dataset.",
            "Two physical ten-minute labeling conventions and three independently",
            "declared model-relative hour shifts were evaluated without optimization.",
            "The astronomical masks are determined from the RISE civil clock",
            "and physical 2020–2021 solar geometry; historical results remain untouched.","",
            "## Unshifted, midpoint-daylight, any-valid-hour candidates", "",
            "|System|10-minute interpretation|n|Measured kWh|IDA RMSE W|PVsyst RMSE W|",
            "|---|---|---:|---:|---:|---:|"]
    for rec in nominal.to_dict("records"):
        report.append(f"|{rec['system']}|{rec['ten_min_timestamp_interpretation']}|{rec['n']:,}|{rec['measured_kWh']:.3f}|{rec['RMSE_IDA_W']:.2f}|{rec['RMSE_PVsyst_W']:.2f}|")
    report += ["", "## Release gates", "",
       "- Establish the logger's 10-minute sampling semantics independently of model errors.",
       "- Reconcile physical DST, full-hour coverage and the intended daylight mask.",
       "- Replicate the earlier audited 4,478-hour reference and measured energies.",
       "- Resolve differences before generating primary annual CI or rewriting manuscript results.",
       "- Do not select an hour shift or preprocessing rule solely to fit simulated outputs.",
       "- Do not rerun unmodified scripts 01, 04, 05 or 08.",""]
    (OUTPUT/"20_raw_AC_alignment_report.md").write_text("\n".join(report),encoding="utf-8")
    print("\nREAD-ONLY DIAGNOSTIC COMPLETE")
    for f in ("20_raw_measurement_inventory.csv","20_raw_AC_alignment_candidates.csv","20_raw_AC_alignment_report.md"):
        print(" ",OUTPUT/f)

if __name__ == "__main__":
    main()
