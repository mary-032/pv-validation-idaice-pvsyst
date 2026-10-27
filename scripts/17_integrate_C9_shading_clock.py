"""Integrate System C/RISE 9 measurement-clock sensitivity into rebuilt A/3 shading data.

Repository inputs (never edited):
  derived_data/shading_analysis_rebuilt_A3.csv
  simulation_models/shaded/IDAICE/System_C_9/Syst9_PD_Shadow/
    energy/electrical system.EL-STRING-POWERS.prn (inverter_o, ORIGINAL)

Outputs (new files only):
  derived_data/shading_analysis_final_A3_C9.csv
  results/Shading_C9_clock_daily_lag_evidence.csv
  results/Shading_C9_original_vs_reindexed_metrics.csv
  results/Shading_C9_clock_hourly_audit.csv

Methodology:
- Hour-ending timestamps; physical day of hour ending 00:00 belongs to previous day.
- Independent cross-system measured B/C lag evidence defines candidate shifts:
    2023-06-12..14: System C recorded measured series 2 h EARLY,
    2023-06-15..19: System C recorded measured series 1 h EARLY.
    Other days: 0 h.
- To reindex a measured value forward by h hours, at target t read the
  ORIGINAL measured value recorded at t - h (never shift modeled results).
- Restore original C/9 IDA ICE inverter_o output; the archived historical
  C IDA series included 43 inconsistent shifts. Do not perpetuate those.
- Preserve PVsyst and all A/B columns; retain original C measured and
  historical IDA values in explicit audit columns.
- Fail closed if source mapping, sample count, energy conservation,
  A3 transition exclusion, or historical C source validation fails.
- All model comparisons are sim - measured, without residual filtering.

Run (repository root):
  python scripts/17_integrate_C9_shading_clock.py
Then apply the separate 02/11 patch and run script 02 shading only.
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from datetime import datetime, timedelta, date
from pathlib import Path
from statistics import fmean

START = datetime(2023, 5, 1, 1)
END = datetime(2023, 6, 20, 0)
TRANSITION = datetime(2023, 5, 10, 14)
ORIGIN = datetime(2023, 1, 1)
SOURCE_NAME = "shading_analysis_rebuilt_A3.csv"
OUTPUT_NAME = "shading_analysis_final_A3_C9.csv"


def operating_day(t: datetime) -> date:
    """Hour-ending local civil convention, e.g. June 13 00:00 -> June 12."""
    return (t - timedelta(microseconds=1)).date()


def lag_hours(day: date) -> int:
    if date(2023, 6, 12) <= day <= date(2023, 6, 14):
        return 2
    if date(2023, 6, 15) <= day <= date(2023, 6, 19):
        return 1
    return 0


def read_original_inverter(path: Path) -> dict[int, float]:
    """Read C inverter_o output, not aggregate produced_p or shifted workbook."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        head = f.readline().lower()
        if "inverter_o" not in head:
            raise ValueError(f"Wrong IDA ICE power channel (expected inverter_o): {path}")
        records = {}
        for line in f:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 3:
                raise ValueError(f"Unexpected IDA PRN format: {path}: {line[:85]}")
            t, _order, p = map(float, parts)
            if not math.isfinite(t) or abs(t - round(t)) > 1e-5:
                raise ValueError(f"Non-hourly index in {path}: {t}")
            idx = round(t)
            if idx in records:
                raise ValueError(f"Duplicate IDA PRN index {idx}")
            if not math.isfinite(p):
                raise ValueError(f"Non-finite IDA power at {idx}")
            records[idx] = p
    return records


def read_shading(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    if not fields or len(rows) != 3600:
        raise ValueError(f"Expected 3,600 canonical rows; {len(rows)} at {path}")
    required = {"timestamp", "system", "P_measured_W", "P_IDA_W", "P_PVsyst_W",
                "GTI_measured_Wm2", "exclude_primary_shading", "shading_geometry_phase"}
    if not required.issubset(fields):
        raise ValueError(f"Missing columns from A3-rebuilt file: {required - set(fields)}")
    counts = Counter(x["system"] for x in rows)
    if counts != {"A": 1200, "B": 1200, "C": 1200}:
        raise ValueError(f"Unexpected system sample counts: {counts}")
    return fields, rows


def ieee_float(s: str, where: str) -> float:
    try:
        x = float(s)
    except (TypeError, ValueError) as err:
        raise ValueError(f"Non-numeric value at {where}: {s!r}") from err
    if not math.isfinite(x):
        raise ValueError(f"Non-finite value at {where}: {s!r}")
    return x


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def metrics(rows, simulation_key: str, measurement_key: str) -> dict:
    pairs = []
    for r in rows:
        if ieee_float(r["GTI_measured_Wm2"], r["timestamp"]) <= 0:
            continue
        m = ieee_float(r[measurement_key], r["timestamp"])
        s = ieee_float(r[simulation_key], r["timestamp"])
        pairs.append((m, s))
    if not pairs:
        raise ValueError("No daytime records in metric calculation")
    n = len(pairs)
    msum = sum(m for m, _ in pairs)
    ssum = sum(s for _, s in pairs)
    errors = [s - m for m, s in pairs]
    rmse = math.sqrt(sum(e*e for e in errors) / n)
    mae = sum(abs(e) for e in errors) / n
    return {
        "n_daylight": n, "measured_kWh_daylight": msum/1000,
        "simulated_kWh_daylight": ssum/1000,
        "RMSE_W": rmse, "MAE_W": mae,
        "CVRMSE_percent": 100*rmse/(msum/n),
        "bias_percent": 100*(ssum-msum)/msum,
    }


def scale_fit_lag(samples: dict, tlist: list[datetime], lag: int):
    """C_measured[t] ≈ alpha * B_measured[t+lag], DATA ONLY."""
    pairs = []
    for t in tlist:
        r_c = samples.get(("C", t))
        r_b = samples.get(("B", t+timedelta(hours=lag)))
        if r_c is None or r_b is None:
            continue
        m_c = float(r_c["P_measured_W"])
        m_b = float(r_b["P_measured_W"])
        if m_c <= 200 or m_b <= 200:
            continue
        pairs.append((m_b, m_c))
    if len(pairs) < 6:
        return {"n": len(pairs), "scale": "", "RMSE_W": "", "correlation": ""}
    alpha = sum(b*c for b,c in pairs)/sum(b*b for b,c in pairs)
    error = [c-alpha*b for b,c in pairs]
    rms = math.sqrt(sum(e*e for e in error)/len(error))
    avg_b = fmean(b for b,_ in pairs)
    avg_c = fmean(c for _,c in pairs)
    cov = sum((b-avg_b)*(c-avg_c) for b,c in pairs)
    sd_b = math.sqrt(sum((b-avg_b)**2 for b,_ in pairs))
    sd_c = math.sqrt(sum((c-avg_c)**2 for _,c in pairs))
    corr = cov/(sd_b*sd_c) if sd_b and sd_c else float("nan")
    return {"n": len(pairs), "scale": alpha, "RMSE_W": rms, "correlation": corr}


def run(root: Path, c_prn: Path | None = None):
    path = root/"derived_data"/SOURCE_NAME
    fields, records = read_shading(path)
    by_system_time = {}
    for rec in records:
        t = datetime.strptime(rec["timestamp"], "%Y-%m-%d %H:%M:%S")
        key=(rec["system"],t)
        if key in by_system_time:
            raise ValueError(f"Duplicate timestamp: {key}")
        by_system_time[key]=rec
    times = [START+timedelta(hours=i) for i in range(1200)]
    if any(("C",t) not in by_system_time or ("B",t) not in by_system_time for t in times):
        raise ValueError("Not all System B/C reference hours are present in expected 1,200-hour window")
    transition_rows=[r for r in records if r["exclude_primary_shading"]=="1"]
    if len(transition_rows)!=1 or transition_rows[0]["system"]!="A" or transition_rows[0]["timestamp"]!="2023-05-10 14:00:00":
        raise ValueError("A3 transition marker must remain exactly one hour: 2023-05-10 14:00")

    prn = c_prn or (root/"simulation_models"/"shaded"/"IDAICE"/"System_C_9"/
          "Syst9_PD_Shadow"/"energy"/"electrical system.EL-STRING-POWERS.prn")
    original_ida=read_original_inverter(prn)
    original_energy = sum(float(by_system_time[("C",t)]["P_measured_W"]) for t in times)
    old_pv_energy = sum(float(by_system_time[("C",t)]["P_PVsyst_W"]) for t in times)
    old_ida_energy = sum(float(by_system_time[("C",t)]["P_IDA_W"]) for t in times)
    newrows=[]
    audits=[]
    n_reindexed=0
    historical_ida_changed=0
    for record in records:
        r=record.copy()
        r["C_measured_archived_W"]=""
        r["C_IDA_historical_aligned_W"]=""
        r["C_reference_clock_shift_hours"]=""
        r["C_reference_source_timestamp"]=""
        r["C_reference_status"]=""
        if r["system"]=="C":
            t=datetime.strptime(r["timestamp"],"%Y-%m-%d %H:%M:%S")
            lag=lag_hours(operating_day(t))
            source_t=t-timedelta(hours=lag)
            source=by_system_time.get(("C",source_t))
            if source is None:
                raise ValueError(f"No original measured System C record at {source_t} required for {t}")
            idx=round((t-ORIGIN).total_seconds()/3600)-1
            if idx not in original_ida:
                raise ValueError(f"Missing original IDA C inverter_o index {idx}")
            old_meas=ieee_float(r["P_measured_W"],r["timestamp"])
            measured=ieee_float(source["P_measured_W"],source_t.isoformat())
            old_ida=ieee_float(r["P_IDA_W"],r["timestamp"])
            original=original_ida[idx]
            if abs(original-old_ida)>0.02:
                historical_ida_changed+=1
            if abs(old_meas-measured)>1e-10:
                n_reindexed+=1
            r["C_measured_archived_W"]=r["P_measured_W"]
            r["C_IDA_historical_aligned_W"]=r["P_IDA_W"]
            r["C_reference_clock_shift_hours"]=str(lag)
            r["C_reference_source_timestamp"]=source_t.strftime("%Y-%m-%d %H:%M:%S")
            r["C_reference_status"]="reindexed_inferred_from_B_C_measurements" if lag else "as_recorded"
            r["P_measured_W"]=repr(measured)
            r["P_IDA_W"]=repr(original)
            audits.append({"timestamp":r["timestamp"],"operating_day":operating_day(t).isoformat(),
                "shift_hours":lag,"original_measured_W":old_meas,"corrected_measured_W":measured,
                "source_original_timestamp":r["C_reference_source_timestamp"],
                "IDA_original_inverter_W":original,"IDA_historical_aligned_W":old_ida,
                "IDA_historical_minus_native_W":old_ida-original,
                "PVsyst_unchanged_W":float(r["P_PVsyst_W"]),"measured_GT_I_Wm2":float(r["GTI_measured_Wm2"])})
        newrows.append(r)
    if len(newrows)!=3600 or len(audits)!=1200:
        raise ValueError("Internal row-count failure")
    for x,y in zip(records,newrows):
        if x["system"] in ("A","B"):
            if any(x[k]!=y[k] for k in fields):
                raise ValueError(f"Non-System C canonical data modified: {x['system']} {x['timestamp']}")
        elif x["P_PVsyst_W"]!=y["P_PVsyst_W"] or x["GTI_measured_Wm2"]!=y["GTI_measured_Wm2"]:
            raise ValueError("C PVsyst or measured GTI unexpectedly modified")
    cnew=[r for r in newrows if r["system"]=="C"]
    new_energy=sum(float(r["P_measured_W"]) for r in cnew)
    new_pv_energy=sum(float(r["P_PVsyst_W"]) for r in cnew)
    new_ida_energy=sum(float(r["P_IDA_W"]) for r in cnew)
    if abs(new_energy-original_energy)>0.02:
        raise ValueError(f"Shifting changed measured energy: {original_energy} -> {new_energy} Wh")
    if abs(old_pv_energy-new_pv_energy)>0.02:
        raise ValueError("PVsyst energy changed unexpectedly")
    if abs(new_ida_energy-old_ida_energy)>0.1:
        raise ValueError("IDA ICE C energy changed: old shifted series was not a pure time displacement")
    if historical_ida_changed!=43:
        raise ValueError(f"Expected 43 historically shifted C model hours; found {historical_ida_changed}. Stop and inspect provenance")
    if n_reindexed!=123:
        raise ValueError(f"Expected 123 C measured values to change at original hourly indices; found {n_reindexed}")

    lagrows=[]
    for day in [date(2023,6,d) for d in range(10,20)]:
        daily=[t for t in times if operating_day(t)==day]
        for lag in (0,1,2,3):
            evidence=scale_fit_lag(by_system_time,daily,lag)
            lagrows.append({"operating_day":str(day),"tested_C_early_hours":lag,
                "selected_reference_shift_hours":lag_hours(day),**evidence})
    for day in [date(2023,6,d) for d in range(12,20)]:
        candidates=[r for r in lagrows if r["operating_day"]==str(day) and r["RMSE_W"]!=""]
        if len(candidates)<3:
            raise ValueError(f"Too few independent B/C lag tests for {day}")
        chosen=min(candidates,key=lambda r:r["RMSE_W"])
        if chosen["tested_C_early_hours"]!=lag_hours(day):
            raise ValueError(f"Independent B/C measured lag did not support expected shift for {day}: {chosen}")

    original_C=[r for r in records if r["system"]=="C"]
    comparisons=[]
    scenarios=[
        ("as_recorded_original_IDA", original_C,"P_IDA_W","P_measured_W","IDA ICE"),
        ("as_recorded", original_C,"P_PVsyst_W","P_measured_W","PVsyst"),
        ("reindexed_measured_native_IDA", cnew,"P_IDA_W","P_measured_W","IDA ICE"),
        ("reindexed_measured", cnew,"P_PVsyst_W","P_measured_W","PVsyst"),
        ("reindexed_measured_historical_IDA_sensitivity", cnew,"C_IDA_historical_aligned_W","P_measured_W","IDA ICE"),
    ]
    # The first scenario above uses historical shifted IDA, so overwrite with native export via old measurement.
    orig_raw=[dict(r,P_IDA_native_W=repr(original_ida[round((datetime.strptime(r["timestamp"],"%Y-%m-%d %H:%M:%S")-ORIGIN).total_seconds()/3600)-1])) for r in original_C]
    scenarios[0]=("as_recorded_native_IDA",orig_raw,"P_IDA_native_W","P_measured_W","IDA ICE")
    scenarios.insert(1,("as_recorded_historical_shifted_IDA_sensitivity",original_C,"P_IDA_W","P_measured_W","IDA ICE"))
    for label,selected,sim,meas,software in scenarios:
        comparisons.append({"scenario":label,"software":software,**metrics(selected,sim,meas)})

    fieldnames=fields+["C_measured_archived_W","C_IDA_historical_aligned_W",
                       "C_reference_clock_shift_hours","C_reference_source_timestamp","C_reference_status"]
    output=root/"derived_data"/OUTPUT_NAME
    rdir=root/"results"
    write(output,fieldnames,newrows)
    write(rdir/"Shading_C9_clock_daily_lag_evidence.csv",["operating_day","tested_C_early_hours",
         "selected_reference_shift_hours","n","scale","RMSE_W","correlation"],lagrows)
    write(rdir/"Shading_C9_original_vs_reindexed_metrics.csv",
          ["scenario","software","n_daylight","measured_kWh_daylight","simulated_kWh_daylight",
           "RMSE_W","MAE_W","CVRMSE_percent","bias_percent"],comparisons)
    write(rdir/"Shading_C9_clock_hourly_audit.csv", list(audits[0]),audits)
    print("PASS: 3,600 canonical rows; A/B untouched, including 10 May mixed-geometry exclusion")
    print(f"PASS: System C measurement energy unchanged: {original_energy/1000:.3f} kWh")
    print(f"PASS: System C PVsyst and native inverter_o energy unchanged: {new_pv_energy/1000:.3f}, {new_ida_energy/1000:.3f} kWh")
    print(f"PASS: independently measured B/C lag selected all eight June 12–19 shifts")
    print(f"PASS: C model restored from original inverter_o; {historical_ida_changed} historical model differences")
    print(f"PASS: {n_reindexed} System C hourly measured values were reindexed")
    for r in comparisons:
        print(f"  {r['scenario']:<51} {r['software']:<8} n={r['n_daylight']:<4} RMSE={r['RMSE_W']:.2f} W; CV(RMSE)={r['CVRMSE_percent']:.2f}%")
    for p in [output,rdir/"Shading_C9_clock_daily_lag_evidence.csv",rdir/"Shading_C9_original_vs_reindexed_metrics.csv",rdir/"Shading_C9_clock_hourly_audit.csv"]:
        print("Output:",p)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument("--c-prn",type=Path,default=None,help="Override original System C native inverter_o PRN for tests")
    args=ap.parse_args()
    run(args.root.resolve(),args.c_prn)
