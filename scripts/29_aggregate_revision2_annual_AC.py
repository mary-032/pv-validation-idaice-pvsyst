#!/usr/bin/env python3
"""Reproduce Step 29 Revision 2 annual AC aggregates from the *audited Step 28* paired series.

This script does NOT recreate the Step 28 cohort, infer clock offsets, validate
irradiance transposition or change the historical 01–11 workflow. It is a
deterministic read-only derivation of monthly energy and error statistics,
seasonal and clock-hour diagnostics, on BOTH Step 28 clock scenarios.

Usage, from repository root:
    python scripts/29_aggregate_revision2_annual_AC.py
    python scripts/29_aggregate_revision2_annual_AC.py --check-only

Writes ONLY results/revision2/29_*.csv when not checking. The --check-only
mode compares each computed CSV cell with the existing committed result.
"""
from __future__ import annotations

import argparse
import csv
import io
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results" / "annual_audit"
DEST = ROOT / "results" / "revision2"
INPUTS = {
    "fixed_CET_hypothesis": "28_annual_AC_primary_fixed_CET.csv",
    "civil_unshifted": "28_annual_AC_sensitivity_civil_unshifted.csv",
}
CAPACITY_KWP = {"A": 3.9, "B": 4.8, "C": 3.3}
EXPECTED_N = 4478
# Immutable Step 28 point-estimate gate from 28_annual_AC_primary_and_sensitivity_metrics.csv
EXPECTED_RMSE_W = {
    ("fixed_CET_hypothesis", "A"): (149.980755052, 252.463083042),
    ("fixed_CET_hypothesis", "B"): (242.506640693, 311.465502732),
    ("fixed_CET_hypothesis", "C"): (190.032274505, 244.999560228),
    ("civil_unshifted", "A"): (390.930525171, 288.019864654),
    ("civil_unshifted", "B"): (521.091138909, 398.410301850),
    ("civil_unshifted", "C"): (378.769104667, 294.870663272),
}
FIELDS = {
    "29_monthly_energy_AC.csv": [
        "scenario", "system", "physical_month", "model", "kWp", "n",
        "measured_kWh", "simulated_kWh", "energy_difference_kWh",
        "RMSE_W", "MAE_W", "MBE_W", "CVRMSE_pct", "nMBE_pct",
        "energy_bias_pct", "mean_measured_W",
    ],
    "29_monthly_RMSE_AC.csv": [
        "scenario", "system", "model", "kWp", "n_months",
        "RMSE_month_kWh", "RMSE_month_kWh_per_kWp", "calendar",
    ],
    "29_seasonal_AC.csv": [
        "scenario", "system", "season", "model", "n", "measured_kWh",
        "simulated_kWh", "RMSE_W", "MAE_W", "MBE_W",
        "CVRMSE_pct", "nMBE_pct", "energy_bias_pct", "mean_measured_W",
    ],
    "29_diurnal_AC.csv": [
        "scenario", "system", "hour_start_local", "model", "n",
        "measured_kWh", "simulated_kWh", "RMSE_W", "MAE_W",
        "MBE_W", "CVRMSE_pct", "nMBE_pct", "energy_bias_pct", "mean_measured_W",
    ],
    "29_source_QC.csv": [
        "scenario", "system", "n", "monthly_groups", "seasonal_groups",
        "physical_days", "measured_kWh", "IDA_RMSE_W", "PVsyst_RMSE_W",
    ],
}


def load(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "system", "physical_interval_start_local", "power_valid_10min",
            "P_measured_W", "IDA_hourly_table_end_aligned_W", "PVsyst_EGrid_W",
        }
        assert required.issubset(set(reader.fieldnames or [])), (
            f"Missing required columns in {path}"
        )
        data = []
        for row in reader:
            item = {
                "sys": row["system"],
                "date": row["physical_interval_start_local"],
                "n10": int(row["power_valid_10min"]),
                "m": float(row["P_measured_W"]),
                "ida": float(row["IDA_hourly_table_end_aligned_W"]),
                "pv": float(row["PVsyst_EGrid_W"]),
            }
            assert item["sys"] in CAPACITY_KWP
            assert item["n10"] == 6, "Missing raw 10-minute reference samples"
            assert all(math.isfinite(item[k]) for k in ("m", "ida", "pv"))
            data.append(item)
    assert len(data) == 3 * EXPECTED_N, (path, len(data))
    return data


def metrics(rows: list[dict], key: str) -> dict:
    n = len(rows)
    assert n > 0
    meas = sum(x["m"] for x in rows)
    pred = sum(x[key] for x in rows)
    residuals = [x[key] - x["m"] for x in rows]
    rmse = math.sqrt(sum(d * d for d in residuals) / n)
    mae = sum(abs(d) for d in residuals) / n
    mbe = (pred - meas) / n
    assert meas > 0
    return {
        "n": n,
        "measured_kWh": meas / 1000,
        "simulated_kWh": pred / 1000,
        "RMSE_W": rmse,
        "MAE_W": mae,
        "MBE_W": mbe,
        "CVRMSE_pct": rmse / (meas / n) * 100,
        "nMBE_pct": mbe / (meas / n) * 100,
        "energy_bias_pct": 100 * (pred - meas) / meas,
        "mean_measured_W": meas / n,
    }


def season(month: int) -> str:
    if month == 12 or month <= 2:
        return "DJF"
    if month <= 5:
        return "MAM"
    if month <= 8:
        return "JJA"
    return "SON"


def group(rows: list[dict], key_fn) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for x in rows:
        k = key_fn(x)
        out.setdefault(k, []).append(x)
    return out


def build(data: dict[str, list[dict]]) -> dict[str, list[dict]]:
    out = {filename: [] for filename in FIELDS}
    for scenario, all_rows in data.items():
        for sys in ("A", "B", "C"):
            rows = [x for x in all_rows if x["sys"] == sys]
            assert len(rows) == EXPECTED_N, (scenario, sys, len(rows))
            times = [x["date"] for x in rows]
            assert len(set(times)) == EXPECTED_N, "Duplicate physical interval"
            monthly = group(rows, lambda x: x["date"][:7])
            seasonal = group(rows, lambda x: season(int(x["date"][5:7])))
            diurnal = group(rows, lambda x: x["date"][11:13])
            assert len(monthly) == 12 and len(seasonal) == 4
            ida = metrics(rows, "ida")
            pv = metrics(rows, "pv")
            exp_ida, exp_pv = EXPECTED_RMSE_W[(scenario, sys)]
            assert math.isclose(ida["RMSE_W"], exp_ida, abs_tol=1e-6)
            assert math.isclose(pv["RMSE_W"], exp_pv, abs_tol=1e-6)
            out["29_source_QC.csv"].append({
                "scenario": scenario, "system": sys, "n": len(rows),
                "monthly_groups": len(monthly), "seasonal_groups": len(seasonal),
                "physical_days": len(set(t[:10] for t in times)),
                "measured_kWh": ida["measured_kWh"],
                "IDA_RMSE_W": ida["RMSE_W"],
                "PVsyst_RMSE_W": pv["RMSE_W"],
            })
            differences = {"IDA_ICE": [], "PVsyst": []}
            for month, subset in sorted(monthly.items()):
                for label, field in (("IDA_ICE", "ida"), ("PVsyst", "pv")):
                    v = metrics(subset, field)
                    delta = v["simulated_kWh"] - v["measured_kWh"]
                    differences[label].append(delta)
                    out["29_monthly_energy_AC.csv"].append({
                        "scenario": scenario, "system": sys,
                        "physical_month": month, "model": label,
                        "kWp": CAPACITY_KWP[sys], **v,
                        "energy_difference_kWh": delta,
                    })
            for label, differences_kwh in differences.items():
                assert len(differences_kwh) == 12
                rmse_kwh = math.sqrt(
                    sum(d * d for d in differences_kwh) / len(differences_kwh)
                )
                out["29_monthly_RMSE_AC.csv"].append({
                    "scenario": scenario, "system": sys, "model": label,
                    "kWp": CAPACITY_KWP[sys], "n_months": len(differences_kwh),
                    "RMSE_month_kWh": rmse_kwh,
                    "RMSE_month_kWh_per_kWp": rmse_kwh / CAPACITY_KWP[sys],
                    "calendar": "physical_month_Jun2020_to_May2021",
                })
            for key, subset in sorted(seasonal.items()):
                for label, field in (("IDA_ICE", "ida"), ("PVsyst", "pv")):
                    out["29_seasonal_AC.csv"].append({
                        "scenario": scenario, "system": sys, "season": key,
                        "model": label, **metrics(subset, field),
                    })
            for hour, subset in sorted(diurnal.items()):
                for label, field in (("IDA_ICE", "ida"), ("PVsyst", "pv")):
                    out["29_diurnal_AC.csv"].append({
                        "scenario": scenario, "system": sys,
                        "hour_start_local": hour, "model": label,
                        **metrics(subset, field),
                    })
            # Monthly and seasonal energy must exactly partition the annual cohort.
            for chunks in (monthly, seasonal, diurnal):
                assert sum(len(part) for part in chunks.values()) == len(rows)
                assert math.isclose(
                    sum(sum(x["m"] for x in part) for part in chunks.values()),
                    sum(x["m"] for x in rows), rel_tol=1e-12
                )
    return out


def render(fields: list[str], rows: list[dict]) -> str:
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(fields)
    for record in rows:
        writer.writerow([
            format(record[k], ".9f") if isinstance(record[k], float)
            else record[k]
            for k in fields
        ])
    return out.getvalue()


def check_existing(path: Path, expected_text: str):
    assert path.exists(), f"Output missing: {path}"
    a = list(csv.DictReader(io.StringIO(expected_text)))
    b = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert len(a) == len(b), (path, len(a), len(b))
    for i, (new, old) in enumerate(zip(a, b), start=2):
        assert new.keys() == old.keys(), (path, i, "columns")
        for col, value in new.items():
            orig = old[col]
            if value == orig:
                continue
            try:
                assert math.isclose(float(value), float(orig),
                                    rel_tol=1e-10, abs_tol=1e-7), (
                    path, i, col, value, orig
                )
            except ValueError:
                raise AssertionError((path, i, col, value, orig))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    data = {name: load(SOURCE / path) for name, path in INPUTS.items()}
    # Ensure both clock hypotheses use exactly the SAME physical measured cohort.
    for sys in CAPACITY_KWP:
        first = {x["date"]: x["m"] for x in data["fixed_CET_hypothesis"]
                 if x["sys"] == sys}
        second = {x["date"]: x["m"] for x in data["civil_unshifted"]
                  if x["sys"] == sys}
        assert first == second, f"Clock scenario changed reference rows: {sys}"
    tables = build(data)
    if not args.check_only:
        DEST.mkdir(parents=True, exist_ok=True)
    for filename, fields in FIELDS.items():
        text = render(fields, tables[filename])
        if args.check_only:
            check_existing(DEST / filename, text)
            print(f"CHECK PASS: {filename} ({len(tables[filename])} rows)")
        else:
            (DEST / filename).write_text(text, encoding="utf-8", newline="")
            print(f"WROTE: {filename} ({len(tables[filename])} rows)")
    print("PASS: both 4,478-hour cohorts and Step 28 annual RMSE anchors")


if __name__ == "__main__":
    main()
