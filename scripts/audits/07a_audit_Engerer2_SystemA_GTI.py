from pathlib import Path
import hashlib
import json
import warnings

import numpy as np
import pandas as pd


# =============================================================================
# 07a - AUDIT SYSTEM A GTI: ENGERER2 vs PEREZ-DRIESSE
# =============================================================================
#
# PURPOSE
# -------
# Diagnose the very large System A GTI difference observed in the Engerer2
# sensitivity analysis WITHOUT changing, shifting, scaling, or correcting
# any data.
#
# The audit asks:
#
# 1. Are the intended PD and E2 source files being used?
# 2. Are the same sheets/columns being parsed from both generations?
# 3. Do the parsed raw-source series exactly reproduce the canonical columns?
# 4. Are PD and E2 canonical timestamps, measured GTI, AOI, Eext_tilt and
#    kt_tilt identical?
# 5. Is zero lag the best alignment for the four simulated GTI series?
# 6. Does the large Engerer2 Delta RMSE come from:
#       - IDA ICE improving,
#       - PVsyst worsening,
#       - or both?
# 7. Is the difference concentrated by month, irradiance level, AOI, or a
#    limited set of timestamps?
# 8. Is System A qualitatively different from Systems B and C?
#
# IMPORTANT
# ---------
# This is DIAGNOSTIC ONLY.
# It never modifies source, canonical, or analysis files.
# It never introduces an automatic shift or scaling.
#
# OUTPUT FOLDER
# -------------
# results/reverse_transposition/audits/SystemA_GTI/
#
# Main outputs:
#   00_audit_checks.csv
#   01_source_file_fingerprints.csv
#   02_source_structure.csv
#   03_raw_to_canonical_agreement.csv
#   04_A_GTI_metric_decomposition.csv
#   05_A_GTI_lag_test.csv
#   06_A_GTI_monthly_audit.csv
#   07_A_GTI_largest_E2_residuals.csv
#   08_A_GTI_largest_PD_to_E2_changes.csv
#   09_cross_system_PD_vs_E2_GTI_summary.csv
#   10_A_GTI_distribution_summary.csv
#   SystemA_GTI_AUDIT.xlsx
#
# Optional figures:
#   A_GTI_monthly_RMSE_audit.png
#   A_GTI_largest_discrepancy_window.png
# =============================================================================


# This script lives under scripts/audits/, so the repository root is two
# directory levels above the script directory.
ROOT = Path(__file__).resolve().parents[2]

IDA_PD_DIR = ROOT / "data" / "ida_ice" / "annual" / "Perez_Driesse"
IDA_E2_DIR = ROOT / "data" / "ida_ice" / "annual" / "Engerer2"
PVS_PD_DIR = ROOT / "data" / "pvsyst" / "annual" / "Perez_Driesse"
PVS_E2_DIR = ROOT / "data" / "pvsyst" / "annual" / "Engerer2"

PD_CANON_PATH = ROOT / "derived_data" / "annual_unshaded_analysis.csv"
E2_CANON_PATH = ROOT / "derived_data" / "annual_unshaded_analysis_Engerer2.csv"

OUT = (
    ROOT
    / "results"
    / "reverse_transposition"
    / "audits"
    / "SystemA_GTI"
)
OUT.mkdir(parents=True, exist_ok=True)

SYSTEM_FILE = {
    "A": "3",
    "B": "8",
    "C": "9",
}

IDA_PD = {
    s: IDA_PD_DIR / f"Syst{num}_PD.xlsx"
    for s, num in SYSTEM_FILE.items()
}
IDA_E2 = {
    s: IDA_E2_DIR / f"Syst{num}_E2.xlsx"
    for s, num in SYSTEM_FILE.items()
}
PVS_PD = {
    s: PVS_PD_DIR / f"PVsyst_{num}_PD_h.xlsx"
    for s, num in SYSTEM_FILE.items()
}
PVS_E2 = {
    s: PVS_E2_DIR / f"PVsyst_{num}_E2_h.xlsx"
    for s, num in SYSTEM_FILE.items()
}

ANALYSIS_START = pd.Timestamp("2021-01-01 00:00:00")
LAGS = range(-3, 4)
TOP_N = 50


# =============================================================================
# Utilities
# =============================================================================

def sha256(path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def require_inputs():
    required = [
        PD_CANON_PATH,
        E2_CANON_PATH,
        IDA_PD["A"],
        IDA_E2["A"],
        PVS_PD["A"],
        PVS_E2["A"],
    ]

    # Cross-system source files are required for the contextual audit too.
    required += [
        IDA_PD["B"], IDA_PD["C"],
        IDA_E2["B"], IDA_E2["C"],
        PVS_PD["B"], PVS_PD["C"],
        PVS_E2["B"], PVS_E2["C"],
    ]

    missing = [p for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required audit input(s):\n"
            + "\n".join(
                f"  - {p.relative_to(ROOT)}"
                for p in missing
            )
        )


def reconstruct_physical_timestamp(ts):
    """
    Synthetic Jan-Dec 2021 analysis clock -> physical Jun2020-May2021 date.
    """
    ts = pd.DatetimeIndex(pd.to_datetime(ts))
    return pd.DatetimeIndex([
        t.replace(year=2021 if t.month <= 5 else 2020)
        for t in ts
    ])


def numeric_equal(a, b, atol=1e-9, rtol=1e-9):
    a = pd.to_numeric(a, errors="coerce").to_numpy(float)
    b = pd.to_numeric(b, errors="coerce").to_numpy(float)

    same_nan = np.isnan(a) & np.isnan(b)
    valid = np.isfinite(a) & np.isfinite(b)

    okay = np.zeros(len(a), dtype=bool)
    okay[same_nan] = True
    okay[valid] = np.isclose(
        a[valid],
        b[valid],
        atol=atol,
        rtol=rtol,
    )

    mismatch = ~okay
    max_abs = (
        float(np.nanmax(np.abs(a[valid] - b[valid])))
        if valid.any()
        else np.nan
    )

    return {
        "n": len(a),
        "n_mismatch": int(mismatch.sum()),
        "fraction_equal": float(okay.mean()),
        "max_abs_difference": max_abs,
        "all_equal": bool(okay.all()),
    }


def calc_metrics(measured, simulated):
    m = pd.to_numeric(measured, errors="coerce")
    s = pd.to_numeric(simulated, errors="coerce")

    valid = m.notna() & s.notna()
    m = m[valid].to_numpy(float)
    s = s[valid].to_numpy(float)

    if len(m) == 0:
        return {
            "n": 0,
            "mean_measured": np.nan,
            "mean_simulated": np.nan,
            "RMSE": np.nan,
            "MAE": np.nan,
            "MBE": np.nan,
            "nMBE_percent": np.nan,
            "CVRMSE_percent": np.nan,
            "R2": np.nan,
            "Pearson_r": np.nan,
        }

    e = s - m
    mean_m = float(np.mean(m))
    rmse = float(np.sqrt(np.mean(e**2)))
    mae = float(np.mean(np.abs(e)))
    mbe = float(np.mean(e))
    nmbe = (
        float(np.sum(e) / np.sum(m) * 100)
        if np.sum(m) != 0
        else np.nan
    )
    cvrmse = (
        float(rmse / mean_m * 100)
        if mean_m != 0
        else np.nan
    )

    ss_res = float(np.sum((s - m)**2))
    ss_tot = float(np.sum((m - np.mean(m))**2))
    r2 = (
        float(1 - ss_res / ss_tot)
        if ss_tot != 0
        else np.nan
    )

    pearson = (
        float(np.corrcoef(m, s)[0, 1])
        if len(m) > 1
        and np.std(m) > 0
        and np.std(s) > 0
        else np.nan
    )

    return {
        "n": len(m),
        "mean_measured": mean_m,
        "mean_simulated": float(np.mean(s)),
        "RMSE": rmse,
        "MAE": mae,
        "MBE": mbe,
        "nMBE_percent": nmbe,
        "CVRMSE_percent": cvrmse,
        "R2": r2,
        "Pearson_r": pearson,
    }


def distribution_stats(x):
    x = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)

    if len(x) == 0:
        return {
            "n": 0,
            "mean": np.nan,
            "median": np.nan,
            "P05": np.nan,
            "P25": np.nan,
            "P75": np.nan,
            "P95": np.nan,
            "max": np.nan,
            "sum_Wh_per_m2": np.nan,
        }

    return {
        "n": len(x),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "P05": float(np.percentile(x, 5)),
        "P25": float(np.percentile(x, 25)),
        "P75": float(np.percentile(x, 75)),
        "P95": float(np.percentile(x, 95)),
        "max": float(np.max(x)),
        # Hourly W/m² summed across samples numerically corresponds to Wh/m².
        "sum_Wh_per_m2": float(np.sum(x)),
    }


# =============================================================================
# Raw-source parsers
# =============================================================================

def parse_ida_gti(path):
    """
    Parse only the IDA GTI series from the IRRADIANCE sheet using exactly the
    same rule as scripts 01/07: average all Panel effective irradiance columns,
    discard Time 0, map Time h to synthetic analysis timestamp.
    """
    d = pd.read_excel(
        path,
        sheet_name="IRRADIANCE",
    )
    d.columns = [
        str(c).strip()
        for c in d.columns
    ]

    if "Time" not in d.columns:
        raise ValueError(
            f"{path.name}/IRRADIANCE has no Time column."
        )

    gcols = [
        c for c in d.columns
        if c.lower().startswith(
            "panel effective irradiance"
        )
    ]

    if not gcols:
        raise ValueError(
            f"No Panel effective irradiance columns found in {path.name}."
        )

    time_h = pd.to_numeric(
        d["Time"],
        errors="coerce",
    )

    gti = d[gcols].apply(
        pd.to_numeric,
        errors="coerce",
    ).mean(axis=1)

    out = pd.DataFrame({
        "ida_time_h": time_h,
        "GTI_Wm2": gti,
    })

    out = out[
        out["ida_time_h"].notna()
        & (out["ida_time_h"] > 0)
    ].copy()

    out["timestamp"] = (
        ANALYSIS_START
        + pd.to_timedelta(
            out["ida_time_h"],
            unit="h",
        )
    ).dt.floor("s")

    structure = {
        "file": path.name,
        "software": "IDA ICE",
        "sheet": "IRRADIANCE",
        "header_row_zero_based": 0,
        "n_raw_rows": len(d),
        "n_parsed_rows": len(out),
        "selected_columns": " | ".join(gcols),
        "selected_column_count": len(gcols),
        "timestamp_rule": "Time>0; timestamp=2021-01-01 00:00 + Time[h]",
        "value_rule": "row mean of all Panel effective irradiance* columns",
        "min_value": float(pd.to_numeric(out["GTI_Wm2"], errors="coerce").min()),
        "max_value": float(pd.to_numeric(out["GTI_Wm2"], errors="coerce").max()),
    }

    return out, structure


def find_pvsyst_header(path):
    raw = pd.read_excel(
        path,
        header=None,
    )

    for i in range(min(60, len(raw))):
        vals = [
            str(v).strip().lower()
            if pd.notna(v)
            else ""
            for v in raw.iloc[i].tolist()
        ]

        if (
            "date" in vals
            and "e_grid" in vals
            and "globeff" in vals
        ):
            return i

    raise ValueError(
        f"Could not identify PVsyst table header in {path.name}."
    )


def parse_pvsyst_gti(path):
    """
    Parse only PVsyst GlobEff using the same row-order timestamp rule as
    scripts 01/07. Calendar years written inside PVsyst are deliberately
    ignored.
    """
    header_row = find_pvsyst_header(path)

    d = pd.read_excel(
        path,
        header=header_row,
    )
    d.columns = [
        str(c).strip()
        for c in d.columns
    ]

    date_col = next(
        c for c in d.columns
        if c.lower() == "date"
    )

    d = d[
        pd.to_datetime(
            d[date_col],
            errors="coerce",
        ).notna()
    ].reset_index(drop=True)

    glob_cols = [
        c for c in d.columns
        if "globeff" in c.lower()
    ]

    if not glob_cols:
        raise ValueError(
            f"No GlobEff column found in {path.name}."
        )

    # Script 07 uses the first matching GlobEff column.
    glob_col = glob_cols[0]

    out = pd.DataFrame({
        "pvsyst_hour_index": np.arange(len(d)),
        "GTI_Wm2": pd.to_numeric(
            d[glob_col],
            errors="coerce",
        ),
    })

    out["timestamp"] = (
        ANALYSIS_START
        + pd.to_timedelta(
            out["pvsyst_hour_index"],
            unit="h",
        )
    ).dt.floor("s")

    structure = {
        "file": path.name,
        "software": "PVsyst",
        "sheet": "first sheet / hourly export",
        "header_row_zero_based": header_row,
        "n_raw_rows": len(d),
        "n_parsed_rows": len(out),
        "selected_columns": glob_col,
        "selected_column_count": 1,
        "timestamp_rule": "ignore PVsyst calendar year; retain row order from 2021-01-01 00:00",
        "value_rule": "GlobEff",
        "min_value": float(pd.to_numeric(out["GTI_Wm2"], errors="coerce").min()),
        "max_value": float(pd.to_numeric(out["GTI_Wm2"], errors="coerce").max()),
    }

    return out, structure


# =============================================================================
# Source-file / structure audit
# =============================================================================

def source_file_fingerprints():
    rows = []

    for system in ("A", "B", "C"):
        for method, path in (
            ("PD_IDA", IDA_PD[system]),
            ("E2_IDA", IDA_E2[system]),
            ("PD_PVsyst", PVS_PD[system]),
            ("E2_PVsyst", PVS_E2[system]),
        ):
            stat = path.stat()

            rows.append({
                "System": system,
                "generation": method,
                "file": path.name,
                "relative_path": str(path.relative_to(ROOT)),
                "size_bytes": stat.st_size,
                "modified_time": pd.Timestamp(
                    stat.st_mtime,
                    unit="s",
                ),
                "sha256": sha256(path),
            })

    return pd.DataFrame(rows)


def source_structure_audit():
    structures = []
    parsed = {}

    for label, path, parser in (
        ("IDA_PD", IDA_PD["A"], parse_ida_gti),
        ("IDA_E2", IDA_E2["A"], parse_ida_gti),
        ("PVsyst_PD", PVS_PD["A"], parse_pvsyst_gti),
        ("PVsyst_E2", PVS_E2["A"], parse_pvsyst_gti),
    ):
        series, struct = parser(path)
        struct["series_label"] = label
        structures.append(struct)
        parsed[label] = series

    return parsed, pd.DataFrame(structures)


# =============================================================================
# Canonical agreement / structural invariants
# =============================================================================

def load_canonical():
    pd_can = pd.read_csv(
        PD_CANON_PATH,
        parse_dates=["timestamp"],
    )
    e2_can = pd.read_csv(
        E2_CANON_PATH,
        parse_dates=["timestamp"],
    )

    for d in (pd_can, e2_can):
        d["timestamp"] = pd.to_datetime(
            d["timestamp"]
        ).dt.floor("s")

    return pd_can, e2_can


def canonical_invariant_checks(pd_can, e2_can):
    checks = []

    for system in ("A", "B", "C"):
        p = (
            pd_can[pd_can["system"] == system]
            .sort_values("timestamp")
            .reset_index(drop=True)
        )
        e = (
            e2_can[e2_can["system"] == system]
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        checks.append({
            "System": system,
            "check": "row_count_equal",
            "PASS": len(p) == len(e),
            "details": f"PD={len(p)}, E2={len(e)}",
        })

        timestamp_equal = (
            len(p) == len(e)
            and p["timestamp"].equals(e["timestamp"])
        )

        checks.append({
            "System": system,
            "check": "timestamps_identical",
            "PASS": timestamp_equal,
            "details": (
                f"PD unique={p['timestamp'].nunique()}, "
                f"E2 unique={e['timestamp'].nunique()}"
            ),
        })

        for col in (
            "GTI_measured_Wm2",
            "P_measured_W",
            "Tp_measured_C",
            "AOI_deg",
            "Eext_tilt_Wm2",
            "kt_tilt",
        ):
            if col not in p.columns or col not in e.columns:
                checks.append({
                    "System": system,
                    "check": f"{col}_identical",
                    "PASS": False,
                    "details": "column missing in one canonical dataset",
                })
                continue

            eq = numeric_equal(
                p[col],
                e[col],
                atol=1e-10,
                rtol=1e-10,
            )

            checks.append({
                "System": system,
                "check": f"{col}_identical",
                "PASS": eq["all_equal"],
                "details": (
                    f"mismatch={eq['n_mismatch']}; "
                    f"max_abs_diff={eq['max_abs_difference']}"
                ),
            })

    return pd.DataFrame(checks)


def raw_to_canonical_agreement(
    parsed,
    pd_can,
    e2_can,
):
    rows = []

    a_pd = (
        pd_can[pd_can["system"] == "A"]
        .sort_values("timestamp")
    )
    a_e2 = (
        e2_can[e2_can["system"] == "A"]
        .sort_values("timestamp")
    )

    mapping = [
        (
            "IDA_PD",
            parsed["IDA_PD"],
            a_pd,
            "GTI_IDA_Wm2",
        ),
        (
            "IDA_E2",
            parsed["IDA_E2"],
            a_e2,
            "GTI_IDA_Wm2",
        ),
        (
            "PVsyst_PD",
            parsed["PVsyst_PD"],
            a_pd,
            "GTI_PVsyst_Wm2",
        ),
        (
            "PVsyst_E2",
            parsed["PVsyst_E2"],
            a_e2,
            "GTI_PVsyst_Wm2",
        ),
    ]

    for label, raw_series, canonical, ccol in mapping:
        merged = canonical[
            ["timestamp", ccol]
        ].merge(
            raw_series[
                ["timestamp", "GTI_Wm2"]
            ],
            on="timestamp",
            how="inner",
            validate="one_to_one",
        )

        eq = numeric_equal(
            merged[ccol],
            merged["GTI_Wm2"],
            atol=1e-9,
            rtol=1e-9,
        )

        rows.append({
            "series": label,
            "canonical_column": ccol,
            "n_merged": len(merged),
            "n_mismatch": eq["n_mismatch"],
            "fraction_equal": eq["fraction_equal"],
            "max_abs_difference": eq["max_abs_difference"],
            "PASS_exact_or_tolerance": eq["all_equal"],
        })

    return pd.DataFrame(rows)


# =============================================================================
# System A merged audit table
# =============================================================================

def system_a_table(pd_can, e2_can):
    p = (
        pd_can[pd_can["system"] == "A"]
        [
            [
                "timestamp",
                "GTI_measured_Wm2",
                "GTI_IDA_Wm2",
                "GTI_PVsyst_Wm2",
                "AOI_deg",
                "Eext_tilt_Wm2",
                "kt_tilt",
            ]
        ]
        .rename(
            columns={
                "GTI_IDA_Wm2": "IDA_PD_Wm2",
                "GTI_PVsyst_Wm2": "PVsyst_PD_Wm2",
            }
        )
    )

    e = (
        e2_can[e2_can["system"] == "A"]
        [
            [
                "timestamp",
                "GTI_IDA_Wm2",
                "GTI_PVsyst_Wm2",
            ]
        ]
        .rename(
            columns={
                "GTI_IDA_Wm2": "IDA_E2_Wm2",
                "GTI_PVsyst_Wm2": "PVsyst_E2_Wm2",
            }
        )
    )

    a = p.merge(
        e,
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )

    a["physical_timestamp"] = reconstruct_physical_timestamp(
        a["timestamp"]
    )

    a["physical_month"] = (
        pd.DatetimeIndex(
            a["physical_timestamp"]
        )
        .to_period("M")
        .astype(str)
    )

    a["daytime"] = (
        pd.to_numeric(
            a["GTI_measured_Wm2"],
            errors="coerce",
        ) > 0
    )

    for series in (
        "IDA_PD_Wm2",
        "PVsyst_PD_Wm2",
        "IDA_E2_Wm2",
        "PVsyst_E2_Wm2",
    ):
        a[f"{series}_residual"] = (
            a[series]
            - a["GTI_measured_Wm2"]
        )
        a[f"{series}_abs_residual"] = (
            a[f"{series}_residual"].abs()
        )

    a["IDA_E2_minus_PD"] = (
        a["IDA_E2_Wm2"]
        - a["IDA_PD_Wm2"]
    )
    a["PVsyst_E2_minus_PD"] = (
        a["PVsyst_E2_Wm2"]
        - a["PVsyst_PD_Wm2"]
    )

    return a


# =============================================================================
# Metric decomposition / lag audit / monthly audit
# =============================================================================

def metric_decomposition(a):
    d = a[a["daytime"]].copy()

    rows = []

    for method, software, col in (
        ("Perez-Driesse", "IDA ICE", "IDA_PD_Wm2"),
        ("Perez-Driesse", "PVsyst", "PVsyst_PD_Wm2"),
        ("Engerer2", "IDA ICE", "IDA_E2_Wm2"),
        ("Engerer2", "PVsyst", "PVsyst_E2_Wm2"),
    ):
        st = calc_metrics(
            d["GTI_measured_Wm2"],
            d[col],
        )

        rows.append({
            "Method": method,
            "Software": software,
            **st,
        })

    out = pd.DataFrame(rows)

    # Add the direct software difference within each method.
    summary_rows = []

    for method in ("Perez-Driesse", "Engerer2"):
        temp = out[out["Method"] == method]
        ida = temp[temp["Software"] == "IDA ICE"].iloc[0]
        pvs = temp[temp["Software"] == "PVsyst"].iloc[0]

        summary_rows.append({
            "Method": method,
            "Delta_RMSE_IDA_minus_PVsyst": (
                ida["RMSE"]
                - pvs["RMSE"]
            ),
            "Delta_CVRMSE_IDA_minus_PVsyst": (
                ida["CVRMSE_percent"]
                - pvs["CVRMSE_percent"]
            ),
        })

    summary = pd.DataFrame(summary_rows)

    return out, summary


def lag_test(a):
    """
    sim_shift_hours = +1 means the simulation series is shifted FORWARD by
    one hour before comparison, i.e. sim originally stamped at t is compared
    with measured at t+1.
    """
    base = (
        a.sort_values("timestamp")
        .reset_index(drop=True)
    )

    rows = []

    for label, col in (
        ("IDA_PD", "IDA_PD_Wm2"),
        ("PVsyst_PD", "PVsyst_PD_Wm2"),
        ("IDA_E2", "IDA_E2_Wm2"),
        ("PVsyst_E2", "PVsyst_E2_Wm2"),
    ):
        for lag in LAGS:
            shifted = base[col].shift(lag)

            # Daytime selection remains defined by measured GTI at the
            # comparison timestamp.
            mask = (
                base["GTI_measured_Wm2"] > 0
            )

            st = calc_metrics(
                base.loc[
                    mask,
                    "GTI_measured_Wm2",
                ],
                shifted.loc[mask],
            )

            rows.append({
                "Series": label,
                "sim_shift_hours": lag,
                "interpretation": (
                    "simulation shifted forward"
                    if lag > 0
                    else (
                        "simulation shifted backward"
                        if lag < 0
                        else "zero lag / current alignment"
                    )
                ),
                **st,
            })

    out = pd.DataFrame(rows)

    out["best_RMSE_for_series"] = False
    out["best_correlation_for_series"] = False

    for label in out["Series"].unique():
        ix = out["Series"] == label

        if out.loc[ix, "RMSE"].notna().any():
            best_rmse_idx = out.loc[ix, "RMSE"].idxmin()
            out.loc[
                best_rmse_idx,
                "best_RMSE_for_series",
            ] = True

        if out.loc[ix, "Pearson_r"].notna().any():
            best_r_idx = out.loc[ix, "Pearson_r"].idxmax()
            out.loc[
                best_r_idx,
                "best_correlation_for_series",
            ] = True

    return out


def monthly_audit(a):
    d = a[a["daytime"]].copy()

    rows = []

    for month, g in d.groupby(
        "physical_month",
        sort=True,
    ):
        for method, software, col in (
            ("Perez-Driesse", "IDA ICE", "IDA_PD_Wm2"),
            ("Perez-Driesse", "PVsyst", "PVsyst_PD_Wm2"),
            ("Engerer2", "IDA ICE", "IDA_E2_Wm2"),
            ("Engerer2", "PVsyst", "PVsyst_E2_Wm2"),
        ):
            st = calc_metrics(
                g["GTI_measured_Wm2"],
                g[col],
            )

            rows.append({
                "physical_month": month,
                "Method": method,
                "Software": software,
                **st,
                "measured_sum_Wh_per_m2": float(
                    g["GTI_measured_Wm2"].sum()
                ),
                "simulated_sum_Wh_per_m2": float(
                    g[col].sum()
                ),
                "mean_AOI_deg": float(
                    g["AOI_deg"].mean()
                ),
                "mean_kt_tilt": float(
                    g["kt_tilt"].mean()
                ),
            })

    return pd.DataFrame(rows)


# =============================================================================
# Large-residual / large-method-change tables
# =============================================================================

def largest_residuals(a):
    d = a[a["daytime"]].copy()

    e2_max = d[
        [
            "IDA_E2_Wm2_abs_residual",
            "PVsyst_E2_Wm2_abs_residual",
        ]
    ].max(axis=1)

    d["max_abs_E2_residual"] = e2_max

    cols = [
        "timestamp",
        "physical_timestamp",
        "GTI_measured_Wm2",
        "IDA_PD_Wm2",
        "PVsyst_PD_Wm2",
        "IDA_E2_Wm2",
        "PVsyst_E2_Wm2",
        "IDA_PD_Wm2_residual",
        "PVsyst_PD_Wm2_residual",
        "IDA_E2_Wm2_residual",
        "PVsyst_E2_Wm2_residual",
        "IDA_E2_minus_PD",
        "PVsyst_E2_minus_PD",
        "AOI_deg",
        "Eext_tilt_Wm2",
        "kt_tilt",
        "max_abs_E2_residual",
    ]

    return (
        d.sort_values(
            "max_abs_E2_residual",
            ascending=False,
        )
        .head(TOP_N)
        [cols]
    )


def largest_method_changes(a):
    d = a[a["daytime"]].copy()

    d["max_abs_PD_to_E2_change"] = (
        d[
            [
                "IDA_E2_minus_PD",
                "PVsyst_E2_minus_PD",
            ]
        ]
        .abs()
        .max(axis=1)
    )

    cols = [
        "timestamp",
        "physical_timestamp",
        "GTI_measured_Wm2",
        "IDA_PD_Wm2",
        "IDA_E2_Wm2",
        "IDA_E2_minus_PD",
        "PVsyst_PD_Wm2",
        "PVsyst_E2_Wm2",
        "PVsyst_E2_minus_PD",
        "AOI_deg",
        "Eext_tilt_Wm2",
        "kt_tilt",
        "max_abs_PD_to_E2_change",
    ]

    return (
        d.sort_values(
            "max_abs_PD_to_E2_change",
            ascending=False,
        )
        .head(TOP_N)
        [cols]
    )


# =============================================================================
# Cross-system comparison
# =============================================================================

def cross_system_summary(pd_can, e2_can):
    rows = []

    for system in ("A", "B", "C"):
        p = (
            pd_can[pd_can["system"] == system]
            .sort_values("timestamp")
            .copy()
        )
        e = (
            e2_can[e2_can["system"] == system]
            .sort_values("timestamp")
            .copy()
        )

        for method, d in (
            ("Perez-Driesse", p),
            ("Engerer2", e),
        ):
            day = d[
                pd.to_numeric(
                    d["GTI_measured_Wm2"],
                    errors="coerce",
                ) > 0
            ]

            for software, col in (
                ("IDA ICE", "GTI_IDA_Wm2"),
                ("PVsyst", "GTI_PVsyst_Wm2"),
            ):
                st = calc_metrics(
                    day["GTI_measured_Wm2"],
                    day[col],
                )

                rows.append({
                    "System": system,
                    "Method": method,
                    "Software": software,
                    **st,
                })

    out = pd.DataFrame(rows)

    # Add PD -> E2 RMSE change for direct context.
    pivot = out.pivot_table(
        index=["System", "Software"],
        columns="Method",
        values=[
            "RMSE",
            "CVRMSE_percent",
            "nMBE_percent",
        ],
    )

    pivot.columns = [
        f"{metric}_{method}"
        for metric, method in pivot.columns
    ]
    pivot = pivot.reset_index()

    for metric in (
        "RMSE",
        "CVRMSE_percent",
        "nMBE_percent",
    ):
        pivot[
            f"{metric}_E2_minus_PD"
        ] = (
            pivot[
                f"{metric}_Engerer2"
            ]
            - pivot[
                f"{metric}_Perez-Driesse"
            ]
        )

    return pivot


# =============================================================================
# Distribution audit
# =============================================================================

def distribution_summary(a):
    d = a[a["daytime"]].copy()

    rows = []

    for label, col in (
        ("Measured", "GTI_measured_Wm2"),
        ("IDA_PD", "IDA_PD_Wm2"),
        ("PVsyst_PD", "PVsyst_PD_Wm2"),
        ("IDA_E2", "IDA_E2_Wm2"),
        ("PVsyst_E2", "PVsyst_E2_Wm2"),
        ("IDA_E2_minus_PD", "IDA_E2_minus_PD"),
        ("PVsyst_E2_minus_PD", "PVsyst_E2_minus_PD"),
    ):
        rows.append({
            "Series": label,
            **distribution_stats(
                d[col]
            ),
        })

    return pd.DataFrame(rows)


# =============================================================================
# Figures
# =============================================================================

def make_figures(a, monthly):
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        warnings.warn(
            f"Matplotlib unavailable; figures skipped. Reason: {exc}"
        )
        return

    # Figure 1: monthly RMSE comparison.
    pivot = monthly.pivot_table(
        index="physical_month",
        columns=["Method", "Software"],
        values="RMSE",
    )

    ax = pivot.plot(
        kind="bar",
        figsize=(12, 6),
    )
    ax.set_ylabel("GTI RMSE [W/m²]")
    ax.set_xlabel("Physical month")
    ax.set_title(
        "System A GTI monthly RMSE: Perez–Driesse vs Engerer2"
    )
    ax.tick_params(
        axis="x",
        rotation=45,
    )
    ax.figure.tight_layout()
    ax.figure.savefig(
        OUT / "A_GTI_monthly_RMSE_audit.png",
        dpi=200,
    )
    plt.close(ax.figure)

    # Figure 2: ±12 h around the largest PD->E2 change.
    d = a[a["daytime"]].copy()
    d["max_change"] = (
        d[
            [
                "IDA_E2_minus_PD",
                "PVsyst_E2_minus_PD",
            ]
        ]
        .abs()
        .max(axis=1)
    )

    if d["max_change"].notna().any():
        center = d.loc[
            d["max_change"].idxmax(),
            "timestamp",
        ]

        window = a[
            (a["timestamp"] >= center - pd.Timedelta(hours=12))
            & (a["timestamp"] <= center + pd.Timedelta(hours=12))
        ].copy()

        fig, ax = plt.subplots(
            figsize=(12, 6)
        )

        for col, label in (
            ("GTI_measured_Wm2", "Measured"),
            ("IDA_PD_Wm2", "IDA PD"),
            ("PVsyst_PD_Wm2", "PVsyst PD"),
            ("IDA_E2_Wm2", "IDA E2"),
            ("PVsyst_E2_Wm2", "PVsyst E2"),
        ):
            ax.plot(
                window["physical_timestamp"],
                window[col],
                label=label,
            )

        ax.set_ylabel("GTI / effective irradiance [W/m²]")
        ax.set_xlabel("Physical timestamp")
        ax.set_title(
            "System A GTI around largest PD-to-E2 change"
        )
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(
            OUT / "A_GTI_largest_discrepancy_window.png",
            dpi=200,
        )
        plt.close(fig)


# =============================================================================
# Excel bundle
# =============================================================================

def write_excel(tables):
    path = OUT / "SystemA_GTI_AUDIT.xlsx"

    try:
        with pd.ExcelWriter(
            path,
            engine="xlsxwriter",
        ) as writer:
            for name, df in tables.items():
                sheet = name[:31]
                df.to_excel(
                    writer,
                    sheet_name=sheet,
                    index=False,
                )

                ws = writer.sheets[sheet]
                ws.freeze_panes(1, 0)

                for j, col in enumerate(df.columns):
                    sample = df[col].head(200)

                    widths = [
                        len(str(v))
                        for v in sample
                        if pd.notna(v)
                    ]

                    width = max(
                        [len(str(col))] + widths
                    )
                    width = min(
                        max(width + 2, 10),
                        34,
                    )

                    ws.set_column(
                        j,
                        j,
                        width,
                    )

        print(
            f"Wrote {path.relative_to(ROOT)}"
        )

    except Exception as exc:
        warnings.warn(
            "Could not create optional Excel audit workbook. "
            f"CSV outputs are still valid. Reason: {exc}"
        )


# =============================================================================
# Console verdict
# =============================================================================

def print_verdict(
    checks,
    raw_agreement,
    decomposition,
    delta_summary,
    lag,
    cross_system,
):
    print("\nAUDIT VERDICT")
    print("=" * 78)

    failed_checks = checks[
        ~checks["PASS"].astype(bool)
    ]
    failed_raw = raw_agreement[
        ~raw_agreement[
            "PASS_exact_or_tolerance"
        ].astype(bool)
    ]

    if len(failed_checks) == 0:
        print(
            "PASS: PD and E2 canonical datasets preserve identical "
            "timestamps, measurements, AOI, Eext_tilt and kt_tilt."
        )
    else:
        print(
            "WARNING: canonical invariants failed. Inspect 00_audit_checks.csv."
        )

    if len(failed_raw) == 0:
        print(
            "PASS: raw System A source parsing reproduces all four canonical "
            "simulated GTI series."
        )
    else:
        print(
            "WARNING: one or more raw-source series do not reproduce the "
            "canonical values. Inspect 03_raw_to_canonical_agreement.csv."
        )

    print("\nSYSTEM A RMSE DECOMPOSITION")
    print("-" * 78)
    print(
        decomposition[
            [
                "Method",
                "Software",
                "n",
                "RMSE",
                "CVRMSE_percent",
                "MBE",
                "nMBE_percent",
                "Pearson_r",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    print("\nWITHIN-METHOD IDA ICE - PVSYST DIFFERENCE")
    print("-" * 78)
    print(
        delta_summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    print("\nLAG CHECK")
    print("-" * 78)

    best_rows = (
        lag[
            lag["best_RMSE_for_series"]
        ]
        [
            [
                "Series",
                "sim_shift_hours",
                "RMSE",
                "Pearson_r",
            ]
        ]
        .copy()
    )

    print(
        best_rows.to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    nonzero_best = best_rows[
        best_rows["sim_shift_hours"] != 0
    ]

    if len(nonzero_best) == 0:
        print(
            "\nPASS: zero lag gives the lowest RMSE for all four System A "
            "simulated GTI series."
        )
    else:
        print(
            "\nWARNING: at least one simulated series has a lower RMSE at a "
            "nonzero lag. This deserves inspection before accepting the "
            "Engerer2 magnitude."
        )

    print("\nCROSS-SYSTEM PD -> E2 RMSE CHANGE")
    print("-" * 78)

    cols = [
        "System",
        "Software",
        "RMSE_Perez-Driesse",
        "RMSE_Engerer2",
        "RMSE_E2_minus_PD",
    ]

    print(
        cross_system[cols].to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    if (
        len(failed_checks) == 0
        and len(failed_raw) == 0
        and len(nonzero_best) == 0
    ):
        print(
            "\nSTRUCTURAL CONCLUSION:"
        )
        print(
            "No file-selection, parsing, canonical-layer or simple ±3 h "
            "alignment fault was detected. If the decomposition and monthly/"
            "residual diagnostics are also physically plausible, the large "
            "System A Engerer2 result is supported as a genuine simulation-"
            "scenario sensitivity rather than an obvious pipeline error."
        )
    else:
        print(
            "\nSTRUCTURAL CONCLUSION:"
        )
        print(
            "At least one audit condition needs inspection. Do not interpret "
            "the large System A Engerer2 result scientifically until the "
            "flagged issue is resolved."
        )


# =============================================================================
# Main
# =============================================================================

def main():
    require_inputs()

    print(
        "\nSYSTEM A GTI AUDIT: ENGERER2 vs PEREZ-DRIESSE"
    )
    print("=" * 78)
    print(
        "Diagnostic only — no data will be modified."
    )
    print(
        f"Output folder: {OUT.relative_to(ROOT)}"
    )

    # Source identity / architecture
    fingerprints = source_file_fingerprints()
    parsed, structures = source_structure_audit()

    # Canonical data
    pd_can, e2_can = load_canonical()
    checks = canonical_invariant_checks(
        pd_can,
        e2_can,
    )
    raw_agreement = raw_to_canonical_agreement(
        parsed,
        pd_can,
        e2_can,
    )

    # Main A audit
    a = system_a_table(
        pd_can,
        e2_can,
    )

    decomposition, delta_summary = metric_decomposition(
        a
    )
    lag = lag_test(a)
    monthly = monthly_audit(a)
    largest_resid = largest_residuals(a)
    largest_change = largest_method_changes(a)
    cross_system = cross_system_summary(
        pd_can,
        e2_can,
    )
    dist = distribution_summary(a)

    # Save all CSV outputs
    outputs = {
        "00_audit_checks.csv": checks,
        "01_source_file_fingerprints.csv": fingerprints,
        "02_source_structure.csv": structures,
        "03_raw_to_canonical_agreement.csv": raw_agreement,
        "04_A_GTI_metric_decomposition.csv": decomposition,
        "04b_A_GTI_within_method_delta.csv": delta_summary,
        "05_A_GTI_lag_test.csv": lag,
        "06_A_GTI_monthly_audit.csv": monthly,
        "07_A_GTI_largest_E2_residuals.csv": largest_resid,
        "08_A_GTI_largest_PD_to_E2_changes.csv": largest_change,
        "09_cross_system_PD_vs_E2_GTI_summary.csv": cross_system,
        "10_A_GTI_distribution_summary.csv": dist,
    }

    print("\nOUTPUTS")
    print("-" * 78)

    for filename, df in outputs.items():
        path = OUT / filename
        df.to_csv(
            path,
            index=False,
        )
        print(
            f"Wrote {path.relative_to(ROOT)}"
        )

    write_excel({
        "Audit_checks": checks,
        "Source_fingerprints": fingerprints,
        "Source_structure": structures,
        "Raw_vs_canonical": raw_agreement,
        "A_metric_decomposition": decomposition,
        "A_within_method_delta": delta_summary,
        "A_lag_test": lag,
        "A_monthly": monthly,
        "A_largest_E2_residuals": largest_resid,
        "A_largest_method_changes": largest_change,
        "Cross_system_summary": cross_system,
        "A_distribution": dist,
    })

    make_figures(
        a,
        monthly,
    )

    print_verdict(
        checks,
        raw_agreement,
        decomposition,
        delta_summary,
        lag,
        cross_system,
    )

    print("\nDONE")
    print("=" * 78)
    print(
        "Start by reading the console verdict, then inspect "
        "04_A_GTI_metric_decomposition.csv, 05_A_GTI_lag_test.csv, "
        "06_A_GTI_monthly_audit.csv, and "
        "09_cross_system_PD_vs_E2_GTI_summary.csv."
    )


if __name__ == "__main__":
    main()
