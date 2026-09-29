from pathlib import Path
import warnings

import numpy as np
import pandas as pd


# =============================================================================
# 07b v2 - PVSYST RAW CLOCK + ALL-SYSTEM LAG AUDIT
# =============================================================================
#
# This script corrects the date parsing used in the first 07b audit by
# explicitly treating PVsyst's European date strings as day-first.
#
# It also expands the diagnostic to all systems (A/B/C), both irradiance
# reconstruction methods (PD/E2), and all three output variables
# (GTI, panel temperature, AC power).
#
# DIAGNOSTIC ONLY. It does not alter any source/canonical file.
#
# OUTPUT:
# 03a_analysis_output_Engerer2/audit_SystemA_GTI/
#   11v2_PVsyst_raw_clock_summary.csv
#   12v2_PVsyst_raw_clock_edges.csv
#   13v2_all_system_lag_test.csv
#   14v2_best_lag_summary.csv
#   PVsyst_CLOCK_AND_LAG_AUDIT_v2.xlsx
# =============================================================================


ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / "01_source_inputs" / "annual" / "PVsyst"
PD_CANON = ROOT / "02_canonical_data" / "annual_unshaded_analysis.csv"
E2_CANON = (
    ROOT / "02a_canonical_data_Engerer2"
    / "annual_unshaded_analysis_Engerer2.csv"
)

OUT = (
    ROOT / "03a_analysis_output_Engerer2"
    / "audit_SystemA_GTI"
)
OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    ("A", "PD"): SRC / "PVsyst_3_PD_h.xlsx",
    ("A", "E2"): SRC / "PVsyst_3_E2_h.xlsx",
    ("B", "PD"): SRC / "PVsyst_8_PD_h.xlsx",
    ("B", "E2"): SRC / "PVsyst_8_E2_h.xlsx",
    ("C", "PD"): SRC / "PVsyst_9_PD_h.xlsx",
    ("C", "E2"): SRC / "PVsyst_9_E2_h.xlsx",
}

ANALYSIS_START = pd.Timestamp("2021-01-01 00:00:00")
LAGS = range(-3, 4)

POWER_EXCLUSIONS = pd.to_datetime([
    "2021-02-02 12:00:00",
    "2021-02-02 13:00:00",
    "2021-04-02 13:00:00",
    "2021-04-30 13:00:00",
])


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def require_inputs():
    required = [PD_CANON, E2_CANON, *FILES.values()]
    missing = [p for p in required if not p.exists()]

    if missing:
        raise FileNotFoundError(
            "Missing required input(s):\n"
            + "\n".join(
                f"  - {p.relative_to(ROOT)}"
                for p in missing
            )
        )


def parse_pvsyst_date(series):
    """
    PVsyst exports commonly use European day/month ordering.
    Explicit dayfirst=True avoids the systematic month/day ambiguity that
    produced non-hourly jumps in the first 07b diagnostic.
    """
    return pd.to_datetime(
        series,
        errors="coerce",
        dayfirst=True,
    )


def find_header(path):
    raw = pd.read_excel(path, header=None)

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
        f"Could not locate hourly header in {path.name}"
    )


def time_to_timedelta(value):
    if pd.isna(value):
        return pd.NaT

    if isinstance(value, pd.Timedelta):
        return value

    if hasattr(value, "hour"):
        return pd.Timedelta(
            hours=value.hour,
            minutes=getattr(value, "minute", 0),
            seconds=getattr(value, "second", 0),
        )

    if isinstance(value, (int, float, np.integer, np.floating)):
        return pd.to_timedelta(float(value), unit="D")

    text = str(value).strip()

    try:
        return pd.to_timedelta(text)
    except Exception:
        return pd.NaT


def normalize_raw_clock_to_2021(date_series, time_series):
    dates = parse_pvsyst_date(date_series)
    offsets = time_series.map(time_to_timedelta)
    raw_dt = dates.dt.normalize() + offsets

    normalized = []

    for t in raw_dt:
        if pd.isna(t):
            normalized.append(pd.NaT)
            continue

        try:
            normalized.append(
                pd.Timestamp(
                    year=2021,
                    month=t.month,
                    day=t.day,
                    hour=t.hour,
                    minute=t.minute,
                    second=t.second,
                )
            )
        except ValueError:
            normalized.append(pd.NaT)

    return pd.DatetimeIndex(normalized), pd.DatetimeIndex(raw_dt)


def read_pvsyst(path):
    header = find_header(path)

    d = pd.read_excel(
        path,
        header=header,
    )
    d.columns = [
        str(c).strip()
        for c in d.columns
    ]

    date_col = next(
        c for c in d.columns
        if c.lower() == "date"
    )

    date_idx = d.columns.get_loc(date_col)
    time_col = d.columns[date_idx + 1]

    parsed_dates = parse_pvsyst_date(d[date_col])
    d = d[parsed_dates.notna()].reset_index(drop=True)

    if len(d) != 8760:
        raise ValueError(
            f"{path.name}: expected 8760 rows, found {len(d)}."
        )

    normalized, raw_dt = normalize_raw_clock_to_2021(
        d[date_col],
        d[time_col],
    )

    d["raw_datetime"] = raw_dt
    d["rawclock_timestamp_2021"] = normalized

    d["rowindex_timestamp_2021"] = (
        ANALYSIS_START
        + pd.to_timedelta(
            np.arange(len(d)),
            unit="h",
        )
    )

    glob_col = next(
        c for c in d.columns
        if "globeff" in c.lower()
    )

    if "TArray.1" in d.columns:
        temp_col = "TArray.1"
    else:
        temp_col = next(
            c for c in d.columns
            if "tarray" in c.lower()
        )

    if "E_Grid.1" in d.columns:
        power_col = "E_Grid.1"
        power_scale = 1.0
    else:
        pcols = [
            c for c in d.columns
            if c.lower().startswith("e_grid")
        ]
        if not pcols:
            raise ValueError(
                f"No E_Grid column in {path.name}"
            )
        power_col = pcols[0]
        power_scale = 1000.0

    out = pd.DataFrame({
        "raw_datetime": d["raw_datetime"],
        "rawclock_timestamp_2021": d["rawclock_timestamp_2021"],
        "rowindex_timestamp_2021": d["rowindex_timestamp_2021"],
        "GTI_Wm2": pd.to_numeric(
            d[glob_col],
            errors="coerce",
        ),
        "Tp_C": pd.to_numeric(
            d[temp_col],
            errors="coerce",
        ),
        "P_W": (
            pd.to_numeric(
                d[power_col],
                errors="coerce",
            )
            * power_scale
        ),
    })

    meta = {
        "header_row_zero_based": header,
        "date_column": date_col,
        "time_column": time_col,
        "GTI_column": glob_col,
        "temperature_column": temp_col,
        "power_column": power_col,
    }

    return out, meta


def clock_summary(system, method, path, d, meta):
    raw = pd.DatetimeIndex(d["raw_datetime"])
    norm = pd.DatetimeIndex(d["rawclock_timestamp_2021"])
    row = pd.DatetimeIndex(d["rowindex_timestamp_2021"])

    delta_h = (
        (norm - row)
        / pd.Timedelta(hours=1)
    )

    diffs = pd.Series(raw).diff().dropna()

    return {
        "System": system,
        "Method": method,
        "file": path.name,
        "header_row_zero_based": meta["header_row_zero_based"],
        "date_column": meta["date_column"],
        "time_column": meta["time_column"],
        "GTI_column": meta["GTI_column"],
        "temperature_column": meta["temperature_column"],
        "power_column": meta["power_column"],
        "n_rows": len(d),
        "raw_first": raw[0],
        "raw_second": raw[1],
        "raw_last_minus1": raw[-2],
        "raw_last": raw[-1],
        "median_rawclock_minus_rowindex_h": float(
            np.nanmedian(delta_h)
        ),
        "min_rawclock_minus_rowindex_h": float(
            np.nanmin(delta_h)
        ),
        "max_rawclock_minus_rowindex_h": float(
            np.nanmax(delta_h)
        ),
        "n_duplicate_raw_timestamps": int(
            pd.Series(raw).duplicated().sum()
        ),
        "n_non_1h_raw_intervals": int(
            (diffs != pd.Timedelta(hours=1)).sum()
        ),
    }


def edge_rows(system, method, d, n=8):
    first = d.head(n).copy()
    first.insert(0, "edge", "first")

    last = d.tail(n).copy()
    last.insert(0, "edge", "last")

    out = pd.concat(
        [first, last],
        ignore_index=True,
    )
    out.insert(0, "Method", method)
    out.insert(0, "System", system)
    return out


def metrics(measured, simulated):
    m = pd.to_numeric(
        measured,
        errors="coerce",
    )
    s = pd.to_numeric(
        simulated,
        errors="coerce",
    )

    valid = m.notna() & s.notna()

    m = m[valid].to_numpy(float)
    s = s[valid].to_numpy(float)

    if len(m) == 0:
        return {
            "n": 0,
            "RMSE": np.nan,
            "MBE": np.nan,
            "nMBE_percent": np.nan,
            "Pearson_r": np.nan,
        }

    e = s - m

    return {
        "n": len(m),
        "RMSE": float(np.sqrt(np.mean(e**2))),
        "MBE": float(np.mean(e)),
        "nMBE_percent": (
            float(np.sum(e) / np.sum(m) * 100)
            if np.sum(m) != 0
            else np.nan
        ),
        "Pearson_r": (
            float(np.corrcoef(m, s)[0, 1])
            if (
                len(m) > 1
                and np.std(m) > 0
                and np.std(s) > 0
            )
            else np.nan
        ),
    }


def load_canonical(method):
    path = PD_CANON if method == "PD" else E2_CANON

    d = pd.read_csv(
        path,
        parse_dates=["timestamp"],
    )
    d["timestamp"] = pd.to_datetime(
        d["timestamp"]
    ).dt.floor("s")

    return d


def all_system_lag_test(parsed):
    rows = []

    canon = {
        "PD": load_canonical("PD"),
        "E2": load_canonical("E2"),
    }

    variables = {
        "GTI": {
            "measured": "GTI_measured_Wm2",
            "sim_raw": "GTI_Wm2",
        },
        "Temperature": {
            "measured": "Tp_measured_C",
            "sim_raw": "Tp_C",
        },
        "Power": {
            "measured": "P_measured_W",
            "sim_raw": "P_W",
        },
    }

    for (system, method), sim in parsed.items():
        ref = (
            canon[method][
                canon[method]["system"] == system
            ]
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        # Use the row-order mapping because this is the mapping under audit.
        sim = (
            sim.sort_values("rowindex_timestamp_2021")
            .reset_index(drop=True)
        )

        # Keep the same 8736 timestamps as the canonical comparison layer.
        merged = ref[
            [
                "timestamp",
                "GTI_measured_Wm2",
                "Tp_measured_C",
                "P_measured_W",
            ]
        ].merge(
            sim[
                [
                    "rowindex_timestamp_2021",
                    "GTI_Wm2",
                    "Tp_C",
                    "P_W",
                ]
            ].rename(
                columns={
                    "rowindex_timestamp_2021": "timestamp",
                }
            ),
            on="timestamp",
            how="inner",
            validate="one_to_one",
        )

        for variable, spec in variables.items():
            for lag in LAGS:
                shifted = merged[
                    spec["sim_raw"]
                ].shift(lag)

                mask = (
                    pd.to_numeric(
                        merged["GTI_measured_Wm2"],
                        errors="coerce",
                    ) > 0
                )

                if variable == "Power":
                    mask &= ~merged["timestamp"].isin(
                        POWER_EXCLUSIONS
                    )

                st = metrics(
                    merged.loc[
                        mask,
                        spec["measured"],
                    ],
                    shifted.loc[mask],
                )

                rows.append({
                    "System": system,
                    "Method": method,
                    "Variable": variable,
                    "sim_shift_hours": lag,
                    "interpretation": (
                        "simulation shifted forward"
                        if lag > 0
                        else (
                            "simulation shifted backward"
                            if lag < 0
                            else "current zero-lag mapping"
                        )
                    ),
                    **st,
                })

    out = pd.DataFrame(rows)

    out["best_RMSE_for_series"] = False
    out["best_correlation_for_series"] = False

    group_cols = [
        "System",
        "Method",
        "Variable",
    ]

    for _, g in out.groupby(group_cols):
        if g["RMSE"].notna().any():
            out.loc[
                g["RMSE"].idxmin(),
                "best_RMSE_for_series",
            ] = True

        if g["Pearson_r"].notna().any():
            out.loc[
                g["Pearson_r"].idxmax(),
                "best_correlation_for_series",
            ] = True

    return out


def best_lag_summary(lag):
    best = lag[
        lag["best_RMSE_for_series"]
    ].copy()

    zero = lag[
        lag["sim_shift_hours"] == 0
    ][
        [
            "System",
            "Method",
            "Variable",
            "RMSE",
            "Pearson_r",
        ]
    ].rename(
        columns={
            "RMSE": "zero_lag_RMSE",
            "Pearson_r": "zero_lag_Pearson_r",
        }
    )

    best = best.merge(
        zero,
        on=[
            "System",
            "Method",
            "Variable",
        ],
        how="left",
        validate="one_to_one",
    )

    best["RMSE_improvement_from_best_lag"] = (
        best["zero_lag_RMSE"]
        - best["RMSE"]
    )

    best["RMSE_improvement_percent"] = (
        100.0
        * best["RMSE_improvement_from_best_lag"]
        / best["zero_lag_RMSE"]
    )

    return best[
        [
            "System",
            "Method",
            "Variable",
            "sim_shift_hours",
            "zero_lag_RMSE",
            "RMSE",
            "RMSE_improvement_from_best_lag",
            "RMSE_improvement_percent",
            "zero_lag_Pearson_r",
            "Pearson_r",
        ]
    ].sort_values(
        [
            "System",
            "Method",
            "Variable",
        ]
    )


def main():
    require_inputs()

    print(
        "\nPVSYST RAW CLOCK + ALL-SYSTEM LAG AUDIT v2"
    )
    print("=" * 80)
    print(
        "Diagnostic only — explicit day-first parsing; no files will be modified."
    )

    parsed = {}
    summaries = []
    edges = []

    for (system, method), path in FILES.items():
        d, meta = read_pvsyst(path)
        parsed[(system, method)] = d

        summaries.append(
            clock_summary(
                system,
                method,
                path,
                d,
                meta,
            )
        )
        edges.append(
            edge_rows(
                system,
                method,
                d,
            )
        )

    summary = pd.DataFrame(summaries)
    edge = pd.concat(
        edges,
        ignore_index=True,
    )

    lag = all_system_lag_test(parsed)
    best = best_lag_summary(lag)

    print("\nRAW CLOCK SUMMARY")
    print("-" * 80)
    print(
        summary[
            [
                "System",
                "Method",
                "file",
                "raw_first",
                "raw_last",
                "median_rawclock_minus_rowindex_h",
                "n_duplicate_raw_timestamps",
                "n_non_1h_raw_intervals",
            ]
        ].to_string(
            index=False
        )
    )

    print("\nBEST LAG BY SYSTEM / METHOD / VARIABLE")
    print("-" * 80)
    print(
        best.to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    # Key diagnostic.
    a_e2 = best[
        (best["System"] == "A")
        & (best["Method"] == "E2")
    ]

    other_e2 = best[
        ~(
            (best["System"] == "A")
            & (best["Method"] == "E2")
        )
        & (best["Method"] == "E2")
    ]

    print("\nVERDICT")
    print("-" * 80)

    if (
        len(a_e2) == 3
        and (a_e2["sim_shift_hours"] == 1).all()
        and (
            other_e2["sim_shift_hours"] == 0
        ).all()
    ):
        print(
            "STRONG EVIDENCE: all three outputs in System A / Engerer2 / PVsyst "
            "(GTI, temperature, power) prefer the same +1 h shift, while the "
            "other Engerer2 PVsyst systems prefer zero lag."
        )
        print(
            "That pattern is consistent with a one-hour offset in the CONTENT "
            "of the A/E2 PVsyst simulation/export, even if its printed raw clock "
            "labels themselves look normal."
        )
        print(
            "Next inspect the exact meteo/weather file imported into the A/E2 "
            "PVsyst project and the PVsyst time convention/export settings. "
            "Do not correct the results until that input/export provenance "
            "provides an independent reason for the +1 h offset."
        )
    elif len(a_e2) == 3 and (
        a_e2["sim_shift_hours"] == 1
    ).sum() >= 2:
        print(
            "A/E2 shows a consistent +1 h tendency across multiple outputs, "
            "but not all three. Inspect the detailed lag table before deciding "
            "whether the whole export is shifted."
        )
    else:
        print(
            "The +1 h anomaly is not consistently shared by A/E2 GTI, "
            "temperature and power. Treat it as a variable-specific issue "
            "rather than a whole-export clock offset."
        )

    # Save outputs.
    outputs = {
        "11v2_PVsyst_raw_clock_summary.csv": summary,
        "12v2_PVsyst_raw_clock_edges.csv": edge,
        "13v2_all_system_lag_test.csv": lag,
        "14v2_best_lag_summary.csv": best,
    }

    print("\nOUTPUTS")
    print("-" * 80)

    for name, df in outputs.items():
        path = OUT / name
        df.to_csv(
            path,
            index=False,
        )
        print(
            f"Wrote {path.relative_to(ROOT)}"
        )

    try:
        xlsx = OUT / "PVsyst_CLOCK_AND_LAG_AUDIT_v2.xlsx"

        with pd.ExcelWriter(
            xlsx,
            engine="xlsxwriter",
        ) as writer:
            for name, df in {
                "Clock_summary": summary,
                "Clock_edges": edge,
                "All_lags": lag,
                "Best_lag": best,
            }.items():
                df.to_excel(
                    writer,
                    sheet_name=name,
                    index=False,
                )

                ws = writer.sheets[name]
                ws.freeze_panes(1, 0)

                for j, col in enumerate(df.columns):
                    vals = [
                        len(str(v))
                        for v in df[col].head(200)
                        if pd.notna(v)
                    ]
                    width = max(
                        [len(str(col))] + vals
                    )
                    ws.set_column(
                        j,
                        j,
                        min(max(width + 2, 10), 36),
                    )

        print(
            f"Wrote {xlsx.relative_to(ROOT)}"
        )

    except Exception as exc:
        warnings.warn(
            f"Optional Excel bundle not created: {exc}"
        )


if __name__ == "__main__":
    main()
