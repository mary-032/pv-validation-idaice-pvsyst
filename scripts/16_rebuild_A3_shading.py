"""Rebuild RISE System 3 (A) partial-shading AC power from original exports.

Inputs expected under the repository root:
  derived_data/shading_analysis.csv   (archived, immutable A/B/C measured layer)
  simulation_models/shaded/IDAICE/System_A_3/
      Syst3_PD_Shadow_middle/energy/electrical system.EL-STRING-POWERS.prn
      Syst3_PD_Shadow_corner/energy/electrical system.EL-STRING-POWERS.prn
  data/pvsyst/shaded/PVsyst_3_SH1_h.CSV  (user-verified middle pole)
  data/pvsyst/shaded/PVsyst_3_SH2_h.CSV  (user-verified corner pole)

Outputs (distinct from frozen originals):
  derived_data/shading_analysis_rebuilt_A3.csv  (3,600 rows)
  results/Shading_A3_geometry_energy.csv
  results/Shading_A3_geometry_hourly.csv
  results/Shading_A3_source_reconciliation.csv

Method:
- Local civil-hour ENDING timestamps for May/June 2023.
- The geometry change was 2023-05-10 approximately 13:10 local time.
- 13:00-14:00 is a MIXED hour, excluded from primary validation.
- IDA ICE source is inverter_o (AC) from hourly 'energy/...EL-STRING-POWERS.prn'.
  The original comparison's exact index is elapsed hour = 2023-hour-ending index - 1.
- PVsyst source is E_Grid in kW from 8.0.2 hourly exports. PVsyst row
  0 is Jan 1 00:00 hour START in its arbitrary year; row 2880 is May 1 00:00.
- Clamp PVsyst E_Grid < 0 to zero solely for AC PRODUCTION comparison;
  inverter stand-by consumption is not part of this comparison.
- No residual-based exclusions, smoothing, or fitting to measurement.
- Reassert exact equality with the archived IDA column and OLD May 11 switch.

Use:
  python scripts/16_rebuild_A3_shading.py
  python scripts/16_rebuild_A3_shading.py --pvsyst-dir /path/to/my/csv/files
"""
from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timedelta
from pathlib import Path

MOVED_AT = datetime(2023, 5, 10, 13, 10)
MIXED_END = datetime(2023, 5, 10, 14, 0)
PRE_END = datetime(2023, 5, 10, 13, 0)
OLD_SWITCH_LAST_MIDDLE = datetime(2023, 5, 11, 12, 0)
REFERENCE_YEAR_START = datetime(2023, 1, 1)
PRIMARY_FIELD_NAMES = ["timestamp", "system", "rise_system", "kWp", "GTI_measured_Wm2", "P_measured_W", "P_IDA_W", "P_PVsyst_W"]


def hour_index_end(t: datetime) -> int:
    delta = (t - REFERENCE_YEAR_START).total_seconds() / 3600.0
    if abs(delta - round(delta)) > 1e-8:
        raise ValueError(f"Non-hourly timestamp: {t}")
    return round(delta)


def read_prn_inverter(path: Path) -> dict[int, float]:
    """Read AC inverter_o (3rd column), NOT EL-POWERS.produced_p."""
    if not path.exists():
        raise FileNotFoundError(path)
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    if not lines or "inverter_o" not in lines[0].lower():
        raise ValueError(f"Missing inverter_o heading in {path}")
    res = {}
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 3:
            raise ValueError(f"Unexpected IDA ICE PRN columns in {path}: {line[:100]}")
        idx = float(parts[0]); power = float(parts[2])
        if abs(idx-round(idx)) > 1e-5:
            raise ValueError(f"Expected hourly PRN index, got {idx}")
        key = round(idx)
        if key in res:
            raise ValueError(f"Duplicate PRN index {key}: {path}")
        res[key] = power
    return res


def read_pvsyst_egrid(path: Path) -> list[float]:
    """Return E_Grid [W], with negative nighttime consumption excluded."""
    if not path.exists():
        raise FileNotFoundError(path)
    # PVsyst 8.0.2 CSV is encoded in Western European characters (degree symbol).
    lines = path.read_text(encoding="cp1252").splitlines()
    header = next((i for i, line in enumerate(lines) if line.strip().lower().startswith("date;e_grid;")), None)
    if header is None:
        raise ValueError(f"Cannot find date;E_Grid CSV header in {path}")
    if not any("kw" in s.lower() for s in lines[header+1:header+3]):
        raise ValueError(f"Cannot verify E_Grid is in kW: {path}")
    rows = []
    for s in lines[header+1:]:
        fields = s.split(";")
        if len(fields) < 2:
            continue
        try:
            dt = datetime.strptime(fields[0].strip(), "%d/%m/%y %H:%M")
        except ValueError:
            continue
        rows.append((dt,float(fields[1]) * 1000.0))
    if len(rows) != 8760:
        raise ValueError(f"Expected 8760 PVsyst hourly rows in {path}, found {len(rows)}")
    if (rows[0][0].month,rows[0][0].day,rows[0][0].hour)!=(1,1,0) or (rows[-1][0].month,rows[-1][0].day,rows[-1][0].hour)!=(12,31,23):
        raise ValueError(f"Unexpected PVsyst row timestamps in {path}")
    for i,(t,_) in enumerate(rows):
        if t!=rows[0][0]+timedelta(hours=i):
            raise ValueError(f"Discontinuous PVsyst hourly rows at {t}")
    return [max(0.0,p) for _,p in rows]


def load_archived(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rdr=csv.DictReader(f)
        rows=list(rdr)
    if len(rows)!=3600:
        raise ValueError(f"Expected 3600 rows, got {len(rows)}: {path}")
    for field in PRIMARY_FIELD_NAMES:
        if field not in rows[0]:
            raise ValueError(f"Missing {field}: {path}")
    counts={s:sum(r["system"]==s for r in rows) for s in ("A","B","C")}
    if counts!={"A":1200,"B":1200,"C":1200}:
        raise ValueError(f"Unexpected system counts: {counts}")
    return rows


def classify(t: datetime) -> str:
    if t <= PRE_END:
        return "Middle"
    if t == MIXED_END:
        return "Transition"
    return "Corner"


def serialize_number(v: float | None) -> str:
    if v is None or not math.isfinite(v):
        return ""
    return repr(float(v))


def stats(selected: list[dict], software: str, *, daytime_only: bool=False) -> dict:
    col = "P_IDA_W" if software == "IDA ICE" else "P_PVsyst_W"
    pairs=[]
    for r in selected:
        if daytime_only and float(r["GTI_measured_Wm2"]) <= 0:
            continue
        try:
            m=float(r["P_measured_W"]); s=float(r[col])
        except (ValueError,TypeError):
            continue
        if math.isfinite(m) and math.isfinite(s):
            pairs.append((m,s))
    if not pairs:
        raise ValueError("Empty comparison selection")
    n=len(pairs)
    total_meas=sum(m for m,_ in pairs)
    total_model=sum(s for _,s in pairs)
    deltas=[s-m for m,s in pairs]
    rmse=math.sqrt(sum(d*d for d in deltas)/n)
    return {
        "Software":software,
        "n_intervals":n,
        "measured_kWh":total_meas/1000,
        "simulated_kWh":total_model/1000,
        "difference_kWh":(total_model-total_meas)/1000,
        "difference_percent":100*(total_model-total_meas)/total_meas if total_meas else None,
        "RMSE_W":rmse,
        "MAE_W":sum(abs(d) for d in deltas)/n,
        "CVRMSE_percent":100*rmse/(total_meas/n) if total_meas else None,
    }


def write_csv(path:Path,rows:list[dict],fields:list[str]):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader();w.writerows(rows)


def run(root:Path,pvsyst_dir:Path):
    main=root/"derived_data"/"shading_analysis.csv"
    original=load_archived(main)
    ida_dir=root/"simulation_models"/"shaded"/"IDAICE"/"System_A_3"
    ida_middle=read_prn_inverter(ida_dir/"Syst3_PD_Shadow_middle"/"energy"/"electrical system.EL-STRING-POWERS.prn")
    ida_corner=read_prn_inverter(ida_dir/"Syst3_PD_Shadow_corner"/"energy"/"electrical system.EL-STRING-POWERS.prn")
    pv_mid=read_pvsyst_egrid(pvsyst_dir/"PVsyst_3_SH1_h.CSV")
    pv_corner=read_pvsyst_egrid(pvsyst_dir/"PVsyst_3_SH2_h.CSV")
    output=[]
    audits=[]
    seen=set()
    for r in original:
        r=r.copy()
        r["shading_geometry_phase"]="not_applicable"
        r["exclude_primary_shading"]="0"
        for col in ("P_IDA_archived_W","P_PVsyst_archived_W","P_IDA_middle_W","P_IDA_corner_W","P_PVsyst_SH1_W","P_PVsyst_SH2_W"):
            r[col]=""
        if r["system"] == "A":
            t=datetime.strptime(r["timestamp"],"%Y-%m-%d %H:%M:%S")
            if t in seen:
                raise ValueError(f"Duplicate A timestamp: {t}")
            seen.add(t)
            idx=hour_index_end(t)-1
            if idx not in ida_middle or idx not in ida_corner or idx<0 or idx>=8760:
                raise ValueError(f"IDA/PVsyst time index {idx} not covered")
            im=ida_middle[idx]; ic=ida_corner[idx]; pm=pv_mid[idx]; pc=pv_corner[idx]
            archived=float(r["P_IDA_W"])
            archived_selected=im if t<=OLD_SWITCH_LAST_MIDDLE else ic
            # Audit independently confirms historical A power was exactly inverter_o.
            if abs(archived-archived_selected) > 0.02:
                raise ValueError(f"Historical IDA mismatch at {t}, archived={archived}, original inverter_o={archived_selected}")
            r["P_IDA_archived_W"]=serialize_number(archived)
            r["P_PVsyst_archived_W"]=r["P_PVsyst_W"]
            r["P_IDA_middle_W"]=serialize_number(im)
            r["P_IDA_corner_W"]=serialize_number(ic)
            r["P_PVsyst_SH1_W"]=serialize_number(pm)
            r["P_PVsyst_SH2_W"]=serialize_number(pc)
            phase=classify(t)
            r["shading_geometry_phase"]=phase
            if phase=="Middle":
                r["P_IDA_W"]=serialize_number(im)
                r["P_PVsyst_W"]=serialize_number(pm)
            elif phase=="Corner":
                r["P_IDA_W"]=serialize_number(ic)
                r["P_PVsyst_W"]=serialize_number(pc)
            else:
                r["P_IDA_W"]=""
                r["P_PVsyst_W"]=""
                r["exclude_primary_shading"]="1"
            audits.append({"timestamp":r["timestamp"],"original_IDA_W":archived,
                           "reconstructed_old_IDA_W":archived_selected,
                           "old_minus_reconstructed_W":archived-archived_selected,
                           "new_IDA_W":r["P_IDA_W"],"phase":phase})
        output.append(r)
    if len(seen)!=1200:
        raise ValueError(f"Found only {len(seen)} A timestamps")
    if sum(x["exclude_primary_shading"]=="1" for x in output)!=1:
        raise ValueError("Exactly one A transition hour required")
    fields=PRIMARY_FIELD_NAMES+["shading_geometry_phase","exclude_primary_shading","P_IDA_archived_W","P_PVsyst_archived_W","P_IDA_middle_W","P_IDA_corner_W","P_PVsyst_SH1_W","P_PVsyst_SH2_W"]
    # Canonical output includes B/C unchanged, with added traceability columns.
    out_canon=root/"derived_data"/"shading_analysis_rebuilt_A3.csv"
    write_csv(out_canon,output,fields)
    a=[r for r in output if r["system"]=="A"]
    pre=[r for r in a if r["shading_geometry_phase"]=="Middle"]
    post=[r for r in a if r["shading_geometry_phase"]=="Corner"]
    eligible=pre+post
    clear=[r for r in eligible if "2023-06-05 00:00:00"<r["timestamp"]<="2023-06-06 00:00:00"]
    partly=[r for r in eligible if "2023-05-15 00:00:00"<r["timestamp"]<="2023-05-16 00:00:00"]
    periods={"Middle_before_move":pre,"Corner_after_move":post,"Full_excluding_transition":eligible,"Clear_day_2023-06-05":clear,"Partly_cloudy_day_2023-05-15":partly}
    energy=[];hourly=[]
    for name,part in periods.items():
        for sw in ("IDA ICE","PVsyst"):
            row=stats(part,sw)
            energy.append({"period":name,"System":"A",**row})
            day=stats(part,sw,daytime_only=True)
            hourly.append({"period":name,"System":"A",**day})
    root_results=root/"results"
    metric_fields=["period","System","Software","n_intervals","measured_kWh","simulated_kWh","difference_kWh","difference_percent","RMSE_W","MAE_W","CVRMSE_percent"]
    write_csv(root_results/"Shading_A3_geometry_energy.csv",energy,metric_fields)
    write_csv(root_results/"Shading_A3_geometry_hourly.csv",hourly,metric_fields)
    write_csv(root_results/"Shading_A3_source_reconciliation.csv",audits,["timestamp","original_IDA_W","reconstructed_old_IDA_W","old_minus_reconstructed_W","new_IDA_W","phase"])
    print("PASS: 1200 System A inverter_o values reproduce archived series exactly under old switch")
    print("PASS: middle->corner switch on May 10, with 13:00-14:00 mixed hour excluded")
    print("PASS: 3600 canonical rows retained, including unaltered B/C comparisons")
    for row in energy:
        if row["period"] in ("Middle_before_move","Corner_after_move","Full_excluding_transition"):
            print(f"{row['period']:<28} {row['Software']:<8} {row['simulated_kWh']:.3f} kWh vs {row['measured_kWh']:.3f} kWh ({row['difference_percent']:+.2f}%)")
    print("Output:",out_canon)
    print("Output:",root_results/"Shading_A3_geometry_energy.csv")
    print("Output:",root_results/"Shading_A3_geometry_hourly.csv")
    print("Output:",root_results/"Shading_A3_source_reconciliation.csv")

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument("--pvsyst-dir",type=Path,default=None)
    args=ap.parse_args()
    root=args.root.resolve()
    pvsyst_dir=(args.pvsyst_dir or root/"data"/"pvsyst"/"shaded").resolve()
    run(root,pvsyst_dir)
