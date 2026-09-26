from pathlib import Path
import json
import math
import warnings

import numpy as np
import pandas as pd


# =============================================================================
# 07 - REVERSE-TRANSPOSITION SENSITIVITY: ENGERER2 vs PEREZ-DRIESSE
# =============================================================================
#
# PURPOSE
# -------
# Re-run the finalized annual PV-validation analysis using the Engerer2-based
# IDA ICE and PVsyst simulations, while preserving EXACTLY the same measured
# data, timestamp alignment, geometry, kt_tilt, filters, exclusions and metric
# definitions as the authoritative Perez-Driesse (PD) baseline.
#
# This is a SENSITIVITY ANALYSIS. It does not replace the PD baseline.
#
# INPUTS
# ------
# Authoritative PD canonical data:
#   02_canonical_data/annual_unshaded_analysis.csv
#
# Engerer2 simulations:
#   01_source_inputs/annual/IDA_ICE/Syst3_E2.xlsx
#   01_source_inputs/annual/IDA_ICE/Syst8_E2.xlsx
#   01_source_inputs/annual/IDA_ICE/Syst9_E2.xlsx
#
#   01_source_inputs/annual/PVsyst/PVsyst_3_E2_h.xlsx
#   01_source_inputs/annual/PVsyst/PVsyst_8_E2_h.xlsx
#   01_source_inputs/annual/PVsyst/PVsyst_9_E2_h.xlsx
#
# OUTPUTS
# -------
# Canonical Engerer2 scenario:
#   02a_canonical_data_Engerer2/
#       annual_unshaded_analysis_Engerer2.csv
#       ENGERER2_PROVENANCE.txt
#
# Analysis:
#   03a_analysis_output_Engerer2/
#       Table4_GTI_Engerer2.csv
#       Table5_Temperature_Engerer2.csv
#       Table6_Power_Engerer2.csv
#       Monthly_RMSE_Engerer2.csv
#       Figure3_weather_bins_Engerer2.csv
#       Power_exclusion_audit_Engerer2.csv
#       Engerer2_Annual_metric_CI30d.csv
#       Engerer2_Paired_IDA_vs_PVsyst_30d.csv
#       Engerer2_vs_PD_sensitivity.csv
#       Reverse_transposition_paired_robustness.csv
#
# IMPORTANT DESIGN CHOICE
# -----------------------
# This script DOES NOT rebuild the measured layer or solar geometry.
# It takes those directly from the finalized PD canonical file and replaces
# ONLY the six simulation-result columns with Engerer2 simulation outputs.
#
# Therefore:
#   * System A measured GTI +1 h correction is identical to PD.
#   * B/C measured GTI source is identical to PD.
#   * Swedish civil-time interpretation is identical to PD.
#   * Full azimuth-aware AOI and Eext_tilt are identical to PD.
#   * kt_tilt and weather-bin assignment are identical to PD.
#   * The four agreed gross-error power timestamps are identical to PD.
#
# Any differences between the PD and E2 analyses are therefore attributable
# to the alternative reverse-transposition / irradiance-input scenario and
# its downstream effect on the simulations, not to changes in analysis rules.
#
# SYSTEM A / ENGERER2 / PVSYST TIMING CORRECTION
# ----------------------------------------------
# A dedicated audit found that GTI, panel temperature and AC power from the
# System A Engerer2 PVsyst export all independently preferred the SAME +1 h
# shift, while A/PD and B/C E2 preferred zero lag. Export metadata also showed
# that A/E2 uniquely used Ekås_Custom_E2.MET. The original .MET file is no
# longer available.
#
# Therefore the ENTIRE A/E2 PVsyst hourly output is assigned:
#
#     corrected timestamp = original row-order timestamp + 1 hour
#
# No value scaling, variable-specific shift, or other correction is applied.
# B/E2 and C/E2 remain unshifted. The raw source workbook is never modified.
# =============================================================================


ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / "01_source_inputs" / "annual"
BASE_CANON = ROOT / "02_canonical_data"
E2_CANON = ROOT / "02a_canonical_data_Engerer2"

PD_OUT = ROOT / "03_analysis_output"
E2_OUT = ROOT / "03a_analysis_output_Engerer2"

E2_CANON.mkdir(exist_ok=True)
E2_OUT.mkdir(exist_ok=True)

CFG = json.loads(
    (ROOT / "config.json").read_text(encoding="utf-8")
)

BASELINE_CANONICAL = BASE_CANON / "annual_unshaded_analysis.csv"

IDA_PATHS = {
    "A": SRC / "IDA_ICE" / "Syst3_E2.xlsx",
    "B": SRC / "IDA_ICE" / "Syst8_E2.xlsx",
    "C": SRC / "IDA_ICE" / "Syst9_E2.xlsx",
}

PVSYST_PATHS = {
    "A": SRC / "PVsyst" / "PVsyst_3_E2_h.xlsx",
    "B": SRC / "PVsyst" / "PVsyst_8_E2_h.xlsx",
    "C": SRC / "PVsyst" / "PVsyst_9_E2_h.xlsx",
}

# Uniform timestamp correction established by the dedicated timing audit.
# IMPORTANT: this shifts the entire PVsyst output record as a unit
# (GTI + panel temperature + AC power). It does NOT alter any values.
PVSYST_TIME_SHIFT_HOURS = {
    "A": 1,
    "B": 0,
    "C": 0,
}

ANALYSIS_START = pd.Timestamp("2021-01-01 00:00:00")

POWER_EXCLUSIONS = pd.to_datetime(
    CFG["annual"]["power_excluded_timestamps"]
)
POWER_EXCLUSION_SET = set(POWER_EXCLUSIONS)

EXPECTED_COMMON_TIMESTAMPS = int(
    CFG["annual"]["expected_common_timestamps"]
)
EXPECTED_ROWS = EXPECTED_COMMON_TIMESTAMPS * 3

N_BOOT = 5000
BLOCK_DAYS = 30
SEED = 20260915
CI_LOW = 2.5
CI_HIGH = 97.5

VARIABLES = {
    "GTI": {
        "measured": "GTI_measured_Wm2",
        "IDA ICE": "GTI_IDA_Wm2",
        "PVsyst": "GTI_PVsyst_Wm2",
        "unit": "W/m²",
    },
    "Temperature": {
        "measured": "Tp_measured_C",
        "IDA ICE": "Tp_IDA_C",
        "PVsyst": "Tp_PVsyst_C",
        "unit": "°C",
    },
    "Power": {
        "measured": "P_measured_W",
        "IDA ICE": "P_IDA_W",
        "PVsyst": "P_PVsyst_W",
        "unit": "W",
    },
}


# =============================================================================
# Input checks
# =============================================================================

def require_inputs():
    required = [
        BASELINE_CANONICAL,
        *IDA_PATHS.values(),
        *PVSYST_PATHS.values(),
    ]

    missing = [p for p in required if not p.exists()]

    if missing:
        raise FileNotFoundError(
            "Missing required input(s):\n"
            + "\n".join(
                f"  - {p.relative_to(ROOT)}"
                for p in missing
            )
        )


# =============================================================================
# Read Engerer2 simulation files
# =============================================================================

def read_ida(system):
    """
    Parse Engerer2 IDA ICE workbook using the same architecture and timestamp
    mapping as the finalized PD builder.
    """
    path = IDA_PATHS[system]

    def read_sheet(name):
        d = pd.read_excel(
            path,
            sheet_name=name,
        )
        d.columns = [
            str(c).strip()
            for c in d.columns
        ]

        if "Time" not in d.columns:
            raise ValueError(
                f"{path.name}/{name} has no Time column."
            )

        d["Time"] = pd.to_numeric(
            d["Time"],
            errors="coerce",
        )
        return d[d["Time"].notna()].copy()

    power = read_sheet("ProducedPower")
    temp = read_sheet("EL-TEMPERATURES")
    irr = read_sheet("IRRADIANCE")

    pcols = [
        c for c in power.columns
        if "produced power" in c.lower()
    ]
    tcols = [
        c for c in temp.columns
        if c.lower().startswith(
            "panel temperature"
        )
    ]
    gcols = [
        c for c in irr.columns
        if c.lower().startswith(
            "panel effective irradiance"
        )
    ]

    if not pcols:
        raise ValueError(
            f"No Produced power column in {path.name}"
        )
    if not tcols:
        raise ValueError(
            f"No panel temperature columns in {path.name}"
        )
    if not gcols:
        raise ValueError(
            f"No panel effective irradiance columns in {path.name}"
        )

    p = pd.DataFrame({
        "ida_time_h": power["Time"],
        "P_IDA_W": pd.to_numeric(
            power[pcols[0]],
            errors="coerce",
        ),
    })

    t = pd.DataFrame({
        "ida_time_h": temp["Time"],
        "Tp_IDA_C": temp[tcols].apply(
            pd.to_numeric,
            errors="coerce",
        ).mean(axis=1),
    })

    g = pd.DataFrame({
        "ida_time_h": irr["Time"],
        "GTI_IDA_Wm2": irr[gcols].apply(
            pd.to_numeric,
            errors="coerce",
        ).mean(axis=1),
    })

    out = (
        p.merge(
            t,
            on="ida_time_h",
            how="inner",
        )
        .merge(
            g,
            on="ida_time_h",
            how="inner",
        )
    )

    # Same final alignment rule as PD: Time 0 is an initial state.
    out = out[
        out["ida_time_h"] > 0
    ].copy()

    out["timestamp"] = (
        ANALYSIS_START
        + pd.to_timedelta(
            out["ida_time_h"],
            unit="h",
        )
    ).dt.floor("s")

    if len(out) != EXPECTED_COMMON_TIMESTAMPS:
        raise ValueError(
            f"{path.name} produced {len(out):,} rows after Time>0; "
            f"expected {EXPECTED_COMMON_TIMESTAMPS:,}."
        )

    print(
        f"  IDA {system}: {path.name}; "
        f"{len(out):,} rows; "
        f"Time {out['ida_time_h'].min():g}.."
        f"{out['ida_time_h'].max():g}"
    )

    return out


def read_pvsyst(system):
    """
    Parse Engerer2 PVsyst hourly export using the same row-order timestamp
    architecture as the finalized PD builder, plus the documented uniform
    timing correction for System A / Engerer2.

    Timing rule
    -----------
    Raw source row i receives the synthetic row-order timestamp:

        ANALYSIS_START + i hours

    Then the complete hourly PVsyst record is shifted by:

        A: +1 h
        B:  0 h
        C:  0 h

    The correction is applied to the timestamp of the entire record, so GTI,
    panel temperature and AC power remain internally synchronized. No data
    values are scaled or edited.
    """
    path = PVSYST_PATHS[system]
    shift_h = int(
        PVSYST_TIME_SHIFT_HOURS[
            system
        ]
    )

    raw = pd.read_excel(
        path,
        header=None,
    )

    header_row = None

    for i in range(
        min(60, len(raw))
    ):
        row = [
            str(v).strip().lower()
            if pd.notna(v)
            else ""
            for v in raw.iloc[i].tolist()
        ]

        if (
            "date" in row
            and "e_grid" in row
            and "globeff" in row
        ):
            header_row = i
            break

    if header_row is None:
        raise ValueError(
            f"Could not locate PVsyst hourly table in {path.name}"
        )

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

    if len(d) != 8760:
        raise ValueError(
            f"{path.name} has {len(d):,} hourly data rows; expected 8,760."
        )

    d["pvsyst_hour_index"] = np.arange(
        len(d)
    )

    if "E_Grid.1" in d.columns:
        power_w = pd.to_numeric(
            d["E_Grid.1"],
            errors="coerce",
        )
    else:
        egrid_cols = [
            c for c in d.columns
            if c.lower().startswith(
                "e_grid"
            )
        ]
        if not egrid_cols:
            raise ValueError(
                f"No E_Grid column in {path.name}"
            )

        power_w = (
            pd.to_numeric(
                d[egrid_cols[0]],
                errors="coerce",
            )
            * 1000.0
        )

    glob = next(
        c for c in d.columns
        if "globeff" in c.lower()
    )

    if "TArray.1" in d.columns:
        tarray = "TArray.1"
    else:
        tarray = next(
            c for c in d.columns
            if "tarray" in c.lower()
        )

    out = pd.DataFrame({
        "pvsyst_hour_index": d[
            "pvsyst_hour_index"
        ],
        "P_PVsyst_W": power_w,
        "GTI_PVsyst_Wm2": pd.to_numeric(
            d[glob],
            errors="coerce",
        ),
        "Tp_PVsyst_C": pd.to_numeric(
            d[tarray],
            errors="coerce",
        ),
    })

    # Preserve both the original row-order timestamp and the corrected
    # comparison timestamp for a transparent provenance trail.
    out["pvsyst_timestamp_uncorrected"] = (
        ANALYSIS_START
        + pd.to_timedelta(
            out["pvsyst_hour_index"],
            unit="h",
        )
    ).dt.floor("s")

    out["pvsyst_time_shift_h"] = shift_h

    out["timestamp"] = (
        out[
            "pvsyst_timestamp_uncorrected"
        ]
        + pd.to_timedelta(
            shift_h,
            unit="h",
        )
    ).dt.floor("s")

    print(
        f"  PVsyst {system}: {path.name}; "
        f"{len(out):,} hourly rows; "
        f"timestamp shift={shift_h:+d} h"
    )

    if system == "A":
        print(
            "    A/E2 correction applies uniformly to "
            "GTI + panel temperature + AC power."
        )

    return out


# =============================================================================
# Build the Engerer2 canonical scenario
# =============================================================================

def build_e2_canonical():
    """
    Preserve the finalized PD measured/geometry layer and replace ONLY the
    simulation columns with Engerer2 outputs.
    """
    base = pd.read_csv(
        BASELINE_CANONICAL,
        parse_dates=["timestamp"],
    )
    base["timestamp"] = pd.to_datetime(
        base["timestamp"]
    ).dt.floor("s")

    if len(base) != EXPECTED_ROWS:
        raise ValueError(
            f"Baseline canonical has {len(base):,} rows; "
            f"expected {EXPECTED_ROWS:,}."
        )

    if (
        base["timestamp"].nunique()
        != EXPECTED_COMMON_TIMESTAMPS
    ):
        raise ValueError(
            "Baseline canonical has unexpected number of unique timestamps."
        )

    # Everything except the six PD simulation output columns is authoritative
    # and remains unchanged in the E2 sensitivity scenario.
    simulation_cols = {
        "GTI_IDA_Wm2",
        "P_IDA_W",
        "Tp_IDA_C",
        "GTI_PVsyst_Wm2",
        "P_PVsyst_W",
        "Tp_PVsyst_C",
        "ida_time_h",
        "pvsyst_hour_index",
        "pvsyst_timestamp_uncorrected",
        "pvsyst_time_shift_h",
    }

    fixed_cols = [
        c for c in base.columns
        if c not in simulation_cols
    ]

    parts = []

    print("\nBUILD ENGERER2 CANONICAL SCENARIO")
    print("=" * 72)

    for system in ("A", "B", "C"):
        b = base[
            base["system"] == system
        ][fixed_cols].copy()

        i = read_ida(system)
        p = read_pvsyst(system)

        d = (
            b.merge(
                i,
                on="timestamp",
                how="inner",
                validate="one_to_one",
            )
            .merge(
                p,
                on="timestamp",
                how="inner",
                validate="one_to_one",
            )
        )

        if len(d) != EXPECTED_COMMON_TIMESTAMPS:
            raise ValueError(
                f"System {system}: E2 canonical has {len(d):,} rows; "
                f"expected {EXPECTED_COMMON_TIMESTAMPS:,}."
            )

        baseline_times = pd.DatetimeIndex(
            sorted(
                b["timestamp"].unique()
            )
        )
        e2_times = pd.DatetimeIndex(
            sorted(
                d["timestamp"].unique()
            )
        )

        if not baseline_times.equals(e2_times):
            raise ValueError(
                f"System {system}: E2 timestamps do not exactly match "
                "the finalized PD canonical timestamps."
            )

        parts.append(d)

        print(
            f"  System {system}: "
            f"{len(d):,} exact baseline timestamps preserved"
        )

    annual = (
        pd.concat(
            parts,
            ignore_index=True,
        )
        .sort_values(
            ["timestamp", "system"]
        )
        .reset_index(drop=True)
    )

    # Keep a stable, familiar column order.
    preferred = [
        "timestamp",
        "system",
        "rise_system",
        "kWp",
        "GTI_measured_Wm2",
        "P_measured_W",
        "Tp_measured_C",
        "ida_time_h",
        "GTI_IDA_Wm2",
        "P_IDA_W",
        "Tp_IDA_C",
        "pvsyst_hour_index",
        "pvsyst_timestamp_uncorrected",
        "pvsyst_time_shift_h",
        "GTI_PVsyst_Wm2",
        "P_PVsyst_W",
        "Tp_PVsyst_C",
        "Eext_tilt_Wm2",
        "AOI_deg",
        "kt_tilt",
    ]

    remaining = [
        c for c in annual.columns
        if c not in preferred
    ]
    annual = annual[
        [c for c in preferred if c in annual.columns]
        + remaining
    ]

    out_path = (
        E2_CANON
        / "annual_unshaded_analysis_Engerer2.csv"
    )

    annual.to_csv(
        out_path,
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
    )

    # Explicit audit record of the applied PVsyst timestamp correction.
    correction_audit = (
        annual.groupby(
            "system",
            as_index=False,
        )
        .agg(
            n_canonical_rows=(
                "timestamp",
                "size",
            ),
            pvsyst_time_shift_h=(
                "pvsyst_time_shift_h",
                "first",
            ),
            first_corrected_timestamp=(
                "timestamp",
                "min",
            ),
            last_corrected_timestamp=(
                "timestamp",
                "max",
            ),
            first_source_timestamp_used=(
                "pvsyst_timestamp_uncorrected",
                "min",
            ),
            last_source_timestamp_used=(
                "pvsyst_timestamp_uncorrected",
                "max",
            ),
            first_source_hour_index_used=(
                "pvsyst_hour_index",
                "min",
            ),
            last_source_hour_index_used=(
                "pvsyst_hour_index",
                "max",
            ),
        )
    )

    correction_audit[
        "correction_basis"
    ] = np.where(
        correction_audit[
            "system"
        ] == "A",
        (
            "Dedicated timing audit: A/E2 PVsyst GTI, panel temperature "
            "and AC power all independently preferred +1 h; A/PD and "
            "B/C E2 preferred 0 h; A/E2 uniquely referenced "
            "Ekås_Custom_E2.MET."
        ),
        "No timing correction indicated by audit.",
    )

    correction_path = (
        E2_OUT
        / "PVsyst_Engerer2_timestamp_correction_audit.csv"
    )

    correction_audit.to_csv(
        correction_path,
        index=False,
    )

    print(
        f"Wrote:             "
        f"{correction_path.relative_to(ROOT)}"
    )

    print("\nENGERER2 CANONICAL RESULT")
    print("-" * 72)
    print(f"Rows:              {len(annual):,}")
    print(
        f"Unique timestamps: "
        f"{annual['timestamp'].nunique():,}"
    )
    print(
        f"First timestamp:   "
        f"{annual['timestamp'].min()}"
    )
    print(
        f"Last timestamp:    "
        f"{annual['timestamp'].max()}"
    )
    print(
        f"Wrote:             "
        f"{out_path.relative_to(ROOT)}"
    )

    return annual


# =============================================================================
# Analysis: exact same point-metric conventions as script 02
# =============================================================================

def calculate_stats(
    measured,
    simulated,
):
    """Final convention: error = simulated - measured."""
    m = pd.to_numeric(
        measured,
        errors="coerce",
    )
    s = pd.to_numeric(
        simulated,
        errors="coerce",
    )

    valid = (
        m.notna()
        & s.notna()
    )

    m = m[valid].to_numpy(
        dtype=float
    )
    s = s[valid].to_numpy(
        dtype=float
    )

    if len(m) == 0:
        return None

    error = s - m
    mean_measured = float(
        np.mean(m)
    )

    rmse = float(
        np.sqrt(
            np.mean(
                error ** 2
            )
        )
    )
    mae = float(
        np.mean(
            np.abs(error)
        )
    )
    mbe = float(
        np.mean(error)
    )

    summed_normalized_bias = (
        float(
            np.sum(error)
            / np.sum(m)
            * 100.0
        )
        if np.sum(m) != 0
        else np.nan
    )

    cvrmse = (
        float(
            rmse
            / mean_measured
            * 100.0
        )
        if mean_measured != 0
        else np.nan
    )

    nmae = (
        float(
            mae
            / mean_measured
            * 100.0
        )
        if mean_measured != 0
        else np.nan
    )

    ss_res = float(
        np.sum(
            (s - m) ** 2
        )
    )
    ss_tot = float(
        np.sum(
            (m - mean_measured) ** 2
        )
    )

    r2 = (
        float(
            1.0
            - ss_res
            / ss_tot
        )
        if ss_tot != 0
        else np.nan
    )

    return {
        "n": len(m),
        "mean_measured": mean_measured,
        "RMSE": rmse,
        "MAE": mae,
        "CVRMSE_percent": cvrmse,
        "nMAE_percent": nmae,
        "MBE": mbe,
        "nMBE_percent": summed_normalized_bias,
        "RE_percent": summed_normalized_bias,
        "R2": r2,
    }


def run_e2_point_analysis(annual):
    table4 = []
    table5 = []
    table6 = []
    monthly_rows = []
    weather_rows = []
    removal_rows = []

    for system in ("A", "B", "C"):
        d = annual[
            annual["system"] == system
        ].copy()

        daytime = d[
            pd.to_numeric(
                d["GTI_measured_Wm2"],
                errors="coerce",
            ) > 0
        ].copy()

        # Table 4: GTI
        for software, sim_col in (
            ("IDA ICE", "GTI_IDA_Wm2"),
            ("PVsyst", "GTI_PVsyst_Wm2"),
        ):
            st = calculate_stats(
                daytime["GTI_measured_Wm2"],
                daytime[sim_col],
            )
            table4.append({
                "System": system,
                "Software": software,
                **st,
            })

        # Table 5: temperature
        for software, sim_col in (
            ("IDA ICE", "Tp_IDA_C"),
            ("PVsyst", "Tp_PVsyst_C"),
        ):
            st = calculate_stats(
                daytime["Tp_measured_C"],
                daytime[sim_col],
            )
            table5.append({
                "System": system,
                "Software": software,
                **st,
            })

        # Table 6: power
        power_data = daytime[
            ~daytime["timestamp"].isin(
                POWER_EXCLUSION_SET
            )
        ].copy()

        removal_rows.append({
            "System": system,
            "daytime_rows_before_power_exclusions": len(daytime),
            "power_rows_after_four_timestamp_exclusions": len(power_data),
            "rows_removed": (
                len(daytime)
                - len(power_data)
            ),
        })

        for software, sim_col in (
            ("IDA ICE", "P_IDA_W"),
            ("PVsyst", "P_PVsyst_W"),
        ):
            st = calculate_stats(
                power_data["P_measured_W"],
                power_data[sim_col],
            )

            tmp = power_data[
                [
                    "timestamp",
                    "P_measured_W",
                    sim_col,
                ]
            ].copy()

            tmp["P_measured_W"] = pd.to_numeric(
                tmp["P_measured_W"],
                errors="coerce",
            )
            tmp[sim_col] = pd.to_numeric(
                tmp[sim_col],
                errors="coerce",
            )
            tmp = tmp.dropna(
                subset=[
                    "P_measured_W",
                    sim_col,
                ]
            )

            tmp["month"] = (
                tmp["timestamp"]
                .dt.to_period("M")
            )

            monthly = (
                tmp.groupby(
                    "month"
                )[
                    [
                        "P_measured_W",
                        sim_col,
                    ]
                ]
                .sum()
                / 1000.0
            )

            monthly["difference_kWh"] = (
                monthly[sim_col]
                - monthly["P_measured_W"]
            )

            rmse_month_kwh = float(
                np.sqrt(
                    np.mean(
                        monthly[
                            "difference_kWh"
                        ] ** 2
                    )
                )
            )

            kwp = float(
                d["kWp"].iloc[0]
            )
            rmse_month_per_kwp = (
                rmse_month_kwh
                / kwp
            )

            monthly_rows.append({
                "System": system,
                "Software": software,
                "kWp": kwp,
                "n_months": len(monthly),
                "RMSE_month_kWh": rmse_month_kwh,
                "RMSE_month_kWh_per_kWp": rmse_month_per_kwp,
            })

            table6.append({
                "System": system,
                "Software": software,
                "Common_power_timestamps_removed": 4,
                "RMSE_month_kWh_per_kWp": rmse_month_per_kwp,
                **st,
            })

        # Weather-bin / Figure-3 sensitivity under same measured kt_tilt bins.
        weather_data = power_data.copy()

        weather_data[
            "kt_tilt"
        ] = pd.to_numeric(
            weather_data["kt_tilt"],
            errors="coerce",
        )
        weather_data[
            "AOI_deg"
        ] = pd.to_numeric(
            weather_data["AOI_deg"],
            errors="coerce",
        )

        weather_data = weather_data[
            weather_data[
                "kt_tilt"
            ].notna()
            & weather_data[
                "AOI_deg"
            ].notna()
            & (
                weather_data["AOI_deg"]
                < float(
                    CFG["annual"][
                        "weather_aoi_limit_deg"
                    ]
                )
            )
        ].copy()

        for bin_cfg in CFG["sky_bins"]:
            lo = float(
                bin_cfg["min"]
            )
            hi = bin_cfg["max"]

            in_bin = (
                weather_data["kt_tilt"]
                >= lo
            )

            if hi is not None:
                hi = float(hi)
                in_bin &= (
                    weather_data["kt_tilt"]
                    < hi
                )

            b = weather_data[
                in_bin
            ]

            for software, sim_col in (
                ("IDA ICE", "P_IDA_W"),
                ("PVsyst", "P_PVsyst_W"),
            ):
                st = calculate_stats(
                    b["P_measured_W"],
                    b[sim_col],
                )

                if st is not None:
                    weather_rows.append({
                        "System": system,
                        "Sky_condition": bin_cfg[
                            "name"
                        ],
                        "kt_min": lo,
                        "kt_max": (
                            np.nan
                            if hi is None
                            else hi
                        ),
                        "Software": software,
                        **st,
                    })

    tables = {
        "Table4_GTI_Engerer2.csv": pd.DataFrame(
            table4
        ),
        "Table5_Temperature_Engerer2.csv": pd.DataFrame(
            table5
        ),
        "Table6_Power_Engerer2.csv": pd.DataFrame(
            table6
        ),
        "Monthly_RMSE_Engerer2.csv": pd.DataFrame(
            monthly_rows
        ),
        "Figure3_weather_bins_Engerer2.csv": pd.DataFrame(
            weather_rows
        ),
        "Power_exclusion_audit_Engerer2.csv": pd.DataFrame(
            removal_rows
        ),
    }

    print("\nENGERER2 POINT ANALYSIS")
    print("=" * 72)

    for name, df in tables.items():
        df.to_csv(
            E2_OUT / name,
            index=False,
        )
        print(
            f"Wrote "
            f"{(E2_OUT / name).relative_to(ROOT)}"
        )

    return tables


# =============================================================================
# 30-day bootstrap uncertainty for the Engerer2 scenario
# =============================================================================

def reconstruct_physical_timestamp(ts):
    """
    Synthetic Jan-Dec 2021 analysis axis -> real Jun2020-May2021 chronology.
    """
    ts = pd.DatetimeIndex(
        pd.to_datetime(ts)
    )

    return pd.DatetimeIndex([
        t.replace(
            year=(
                2021
                if t.month <= 5
                else 2020
            )
        )
        for t in ts
    ])


def prepare_physical_days(annual):
    d = annual.copy()

    d["physical_timestamp"] = (
        reconstruct_physical_timestamp(
            d["timestamp"]
        )
    )
    d["physical_day"] = (
        d["physical_timestamp"]
        .dt.normalize()
    )

    days = pd.DatetimeIndex(
        sorted(
            d["physical_day"]
            .unique()
        )
    )

    dmap = {
        day: i
        for i, day in enumerate(days)
    }

    return d, days, dmap


def circular_block_weights(
    n_days,
    block_days=BLOCK_DAYS,
    n_boot=N_BOOT,
    seed=SEED + 100 * BLOCK_DAYS,
):
    rng = np.random.default_rng(
        seed
    )

    n_blocks = math.ceil(
        n_days
        / block_days
    )

    weights = np.zeros(
        (
            n_boot,
            n_days,
        ),
        dtype=np.uint16,
    )

    offsets = np.arange(
        block_days
    )

    for b in range(
        n_boot
    ):
        starts = rng.integers(
            0,
            n_days,
            size=n_blocks,
        )

        idx = (
            starts[:, None]
            + offsets[None, :]
        ) % n_days

        idx = (
            idx.ravel()[
                :n_days
            ]
        )

        weights[b] = np.bincount(
            idx,
            minlength=n_days,
        ).astype(
            np.uint16
        )

    return weights


def selected_rows(
    annual,
    system,
    variable,
    software=None,
    both=False,
):
    spec = VARIABLES[
        variable
    ]

    d = annual[
        annual["system"]
        == system
    ].copy()

    d = d[
        pd.to_numeric(
            d["GTI_measured_Wm2"],
            errors="coerce",
        ) > 0
    ].copy()

    if variable == "Power":
        d = d[
            ~d["timestamp"].isin(
                POWER_EXCLUSIONS
            )
        ].copy()

    cols = [
        spec["measured"]
    ]

    if both:
        cols += [
            spec["IDA ICE"],
            spec["PVsyst"],
        ]
    else:
        cols += [
            spec[software]
        ]

    for c in cols:
        d[c] = pd.to_numeric(
            d[c],
            errors="coerce",
        )

    return d.dropna(
        subset=cols
    ).copy()


def daily_stats(
    d,
    mcol,
    scol,
    dmap,
    n_days,
):
    m = d[mcol].to_numpy(
        dtype=float
    )
    s = d[scol].to_numpy(
        dtype=float
    )
    e = s - m

    idx = (
        d["physical_day"]
        .map(dmap)
        .to_numpy(
            dtype=int
        )
    )

    out = {
        key: np.zeros(
            n_days,
            dtype=float,
        )
        for key in (
            "n",
            "sum_e",
            "sum_e2",
            "sum_abs_e",
            "sum_m",
            "sum_m2",
        )
    }

    values = {
        "n": np.ones(
            len(d),
            dtype=float,
        ),
        "sum_e": e,
        "sum_e2": e ** 2,
        "sum_abs_e": np.abs(
            e
        ),
        "sum_m": m,
        "sum_m2": m ** 2,
    }

    for key, arr in values.items():
        out[key] += np.bincount(
            idx,
            weights=arr,
            minlength=n_days,
        )

    return out


def bootstrap_metrics(
    stats,
    W,
):
    n = W @ stats["n"]
    se = W @ stats[
        "sum_e"
    ]
    se2 = W @ stats[
        "sum_e2"
    ]
    sae = W @ stats[
        "sum_abs_e"
    ]
    sm = W @ stats[
        "sum_m"
    ]
    sm2 = W @ stats[
        "sum_m2"
    ]

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):
        mean_m = sm / n
        rmse = np.sqrt(
            se2 / n
        )
        mae = sae / n
        mbe = se / n
        cvrmse = (
            100.0
            * rmse
            / mean_m
        )
        nmae = (
            100.0
            * mae
            / mean_m
        )
        nmbe = (
            100.0
            * se
            / sm
        )

        sst = (
            sm2
            - sm ** 2
            / n
        )
        r2 = (
            1.0
            - se2
            / sst
        )

    r2 = np.where(
        sst > 0,
        r2,
        np.nan,
    )

    return {
        "n": n,
        "RMSE": rmse,
        "CVRMSE_percent": cvrmse,
        "MAE": mae,
        "nMAE_percent": nmae,
        "MBE": mbe,
        "nMBE_percent": nmbe,
        "RE_percent": nmbe,
        "R2": r2,
    }


def percentile_ci(values):
    v = np.asarray(
        values,
        dtype=float,
    )
    v = v[
        np.isfinite(v)
    ]

    if len(v) == 0:
        return (
            np.nan,
            np.nan,
        )

    lo, hi = np.percentile(
        v,
        [
            CI_LOW,
            CI_HIGH,
        ],
    )

    return (
        float(lo),
        float(hi),
    )


def engerer2_metric_cis(
    annual,
):
    d, days, dmap = (
        prepare_physical_days(
            annual
        )
    )

    W = circular_block_weights(
        len(days)
    )

    rows = []

    for system in (
        "A",
        "B",
        "C",
    ):
        for variable, spec in VARIABLES.items():
            for software in (
                "IDA ICE",
                "PVsyst",
            ):
                x = selected_rows(
                    d,
                    system,
                    variable,
                    software=software,
                )

                st = daily_stats(
                    x,
                    spec["measured"],
                    spec[software],
                    dmap,
                    len(days),
                )

                point = bootstrap_metrics(
                    st,
                    np.ones(
                        (
                            1,
                            len(days),
                        )
                    ),
                )
                boot = bootstrap_metrics(
                    st,
                    W,
                )

                for metric in (
                    "RMSE",
                    "CVRMSE_percent",
                    "nMBE_percent",
                ):
                    lo, hi = percentile_ci(
                        boot[metric]
                    )

                    rows.append({
                        "System": system,
                        "Variable": variable,
                        "Software": software,
                        "Metric": metric,
                        "Estimate": float(
                            point[metric][0]
                        ),
                        "CI95_low": lo,
                        "CI95_high": hi,
                        "block_days": BLOCK_DAYS,
                        "n_boot": N_BOOT,
                    })

    out = pd.DataFrame(
        rows
    )

    path = (
        E2_OUT
        / "Engerer2_Annual_metric_CI30d.csv"
    )
    out.to_csv(
        path,
        index=False,
    )

    print(
        f"Wrote {path.relative_to(ROOT)}"
    )

    return out, d, days, dmap, W


# =============================================================================
# Paired IDA ICE vs PVsyst inference under Engerer2
# =============================================================================

def paired_daily_stats(
    d,
    spec,
    dmap,
    n_days,
):
    m = d[
        spec["measured"]
    ].to_numpy(
        dtype=float
    )
    ida = d[
        spec["IDA ICE"]
    ].to_numpy(
        dtype=float
    )
    pvs = d[
        spec["PVsyst"]
    ].to_numpy(
        dtype=float
    )

    ei = ida - m
    ep = pvs - m

    idx = (
        d["physical_day"]
        .map(dmap)
        .to_numpy(
            dtype=int
        )
    )

    out = {
        key: np.zeros(
            n_days,
            dtype=float,
        )
        for key in (
            "n",
            "sum_m",
            "ida_e2",
            "pvs_e2",
        )
    }

    values = {
        "n": np.ones(
            len(d)
        ),
        "sum_m": m,
        "ida_e2": ei ** 2,
        "pvs_e2": ep ** 2,
    }

    for key, arr in values.items():
        out[key] += np.bincount(
            idx,
            weights=arr,
            minlength=n_days,
        )

    return out


def paired_effect(
    stats,
    W,
):
    n = W @ stats["n"]
    sm = W @ stats[
        "sum_m"
    ]
    ie2 = W @ stats[
        "ida_e2"
    ]
    pe2 = W @ stats[
        "pvs_e2"
    ]

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):
        ri = np.sqrt(
            ie2 / n
        )
        rp = np.sqrt(
            pe2 / n
        )
        mean_m = sm / n

        delta_rmse = (
            ri - rp
        )
        delta_cvrmse = (
            100.0
            * delta_rmse
            / mean_m
        )

    return (
        n,
        ri,
        rp,
        delta_rmse,
        delta_cvrmse,
    )


def bootstrap_p(
    boot_values,
    observed,
):
    b = np.asarray(
        boot_values,
        dtype=float,
    )
    b = b[
        np.isfinite(b)
    ]

    if (
        len(b) == 0
        or not np.isfinite(
            observed
        )
    ):
        return np.nan

    null_dev = (
        b - observed
    )

    extreme = np.sum(
        np.abs(
            null_dev
        ) >= abs(
            observed
        )
    )

    return float(
        (
            extreme + 1
        )
        / (
            len(b) + 1
        )
    )


def holm_adjust(p_values):
    p = np.asarray(
        p_values,
        dtype=float,
    )

    out = np.full_like(
        p,
        np.nan,
        dtype=float,
    )

    valid = np.where(
        np.isfinite(p)
    )[0]

    if len(valid) == 0:
        return out

    order = valid[
        np.argsort(
            p[valid]
        )
    ]

    m = len(order)
    running = 0.0

    for rank, idx in enumerate(
        order
    ):
        candidate = min(
            1.0,
            (
                m - rank
            ) * p[idx],
        )
        running = max(
            running,
            candidate,
        )
        out[idx] = running

    return out


def engerer2_paired_inference(
    annual_with_days,
    days,
    dmap,
    W,
):
    rows = []

    for system in (
        "A",
        "B",
        "C",
    ):
        for variable, spec in VARIABLES.items():
            d = selected_rows(
                annual_with_days,
                system,
                variable,
                both=True,
            )

            st = paired_daily_stats(
                d,
                spec,
                dmap,
                len(days),
            )

            point = paired_effect(
                st,
                np.ones(
                    (
                        1,
                        len(days),
                    )
                ),
            )
            boot = paired_effect(
                st,
                W,
            )

            observed = float(
                point[3][0]
            )

            lo, hi = percentile_ci(
                boot[3]
            )
            cv_lo, cv_hi = (
                percentile_ci(
                    boot[4]
                )
            )

            rows.append({
                "System": system,
                "Variable": variable,
                "unit_RMSE": spec[
                    "unit"
                ],
                "n_common": int(
                    round(
                        point[0][0]
                    )
                ),
                "RMSE_IDA": float(
                    point[1][0]
                ),
                "RMSE_PVsyst": float(
                    point[2][0]
                ),
                "Delta_RMSE_IDA_minus_PVsyst": observed,
                "Delta_RMSE_CI95_low": lo,
                "Delta_RMSE_CI95_high": hi,
                "Delta_CVRMSE_percentage_points": float(
                    point[4][0]
                ),
                "Delta_CVRMSE_CI95_low": cv_lo,
                "Delta_CVRMSE_CI95_high": cv_hi,
                "bootstrap_p_raw": bootstrap_p(
                    boot[3],
                    observed,
                ),
                "block_days": BLOCK_DAYS,
                "n_boot": N_BOOT,
            })

    out = pd.DataFrame(
        rows
    )

    out[
        "bootstrap_p_Holm"
    ] = holm_adjust(
        out[
            "bootstrap_p_raw"
        ].to_numpy()
    )

    out[
        "significant_Holm_0.05"
    ] = (
        out[
            "bootstrap_p_Holm"
        ] < 0.05
    )

    out[
        "CI_excludes_zero"
    ] = (
        (
            out[
                "Delta_RMSE_CI95_low"
            ] > 0
        )
        | (
            out[
                "Delta_RMSE_CI95_high"
            ] < 0
        )
    )

    out[
        "Favored_by_RMSE"
    ] = np.where(
        out[
            "Delta_RMSE_IDA_minus_PVsyst"
        ] < 0,
        "IDA ICE",
        np.where(
            out[
                "Delta_RMSE_IDA_minus_PVsyst"
            ] > 0,
            "PVsyst",
            "Tie",
        ),
    )

    path = (
        E2_OUT
        / "Engerer2_Paired_IDA_vs_PVsyst_30d.csv"
    )

    out.to_csv(
        path,
        index=False,
    )

    print(
        f"Wrote {path.relative_to(ROOT)}"
    )

    return out


# =============================================================================
# Direct Engerer2 vs Perez-Driesse sensitivity tables
# =============================================================================

def long_from_point_tables(
    table4,
    table5,
    table6,
):
    rows = []

    mapping = [
        (
            "GTI",
            table4,
            [
                "RMSE",
                "CVRMSE_percent",
                "nMBE_percent",
                "MAE",
                "nMAE_percent",
                "MBE",
                "RE_percent",
                "R2",
            ],
        ),
        (
            "Temperature",
            table5,
            [
                "RMSE",
                "CVRMSE_percent",
                "nMBE_percent",
                "MAE",
                "nMAE_percent",
                "MBE",
                "RE_percent",
                "R2",
            ],
        ),
        (
            "Power",
            table6,
            [
                "RMSE",
                "CVRMSE_percent",
                "nMBE_percent",
                "MAE",
                "nMAE_percent",
                "MBE",
                "RE_percent",
                "R2",
                "RMSE_month_kWh_per_kWp",
            ],
        ),
    ]

    for variable, df, metrics in mapping:
        for _, r in df.iterrows():
            for metric in metrics:
                if metric not in r.index:
                    continue

                rows.append({
                    "System": r[
                        "System"
                    ],
                    "Variable": variable,
                    "Software": r[
                        "Software"
                    ],
                    "Metric": metric,
                    "Value": r[
                        metric
                    ],
                })

    return pd.DataFrame(
        rows
    )


def build_pd_e2_comparison(
    e2_tables,
):
    pd_files = {
        "GTI": (
            PD_OUT
            / "Table4_GTI_recomputed.csv"
        ),
        "Temperature": (
            PD_OUT
            / "Table5_Temperature_recomputed.csv"
        ),
        "Power": (
            PD_OUT
            / "Table6_Power_recomputed.csv"
        ),
    }

    missing = [
        p
        for p in pd_files.values()
        if not p.exists()
    ]

    if missing:
        warnings.warn(
            "PD point-result table(s) missing, so the direct "
            "Engerer2-vs-PD comparison table will be skipped:\n"
            + "\n".join(
                str(p)
                for p in missing
            )
        )
        return None

    pd_long = long_from_point_tables(
        pd.read_csv(
            pd_files["GTI"]
        ),
        pd.read_csv(
            pd_files["Temperature"]
        ),
        pd.read_csv(
            pd_files["Power"]
        ),
    ).rename(
        columns={
            "Value": "Perez_Driesse"
        }
    )

    e2_long = long_from_point_tables(
        e2_tables[
            "Table4_GTI_Engerer2.csv"
        ],
        e2_tables[
            "Table5_Temperature_Engerer2.csv"
        ],
        e2_tables[
            "Table6_Power_Engerer2.csv"
        ],
    ).rename(
        columns={
            "Value": "Engerer2"
        }
    )

    out = pd_long.merge(
        e2_long,
        on=[
            "System",
            "Variable",
            "Software",
            "Metric",
        ],
        how="outer",
        validate="one_to_one",
    )

    out[
        "Engerer2_minus_Perez_Driesse"
    ] = (
        out["Engerer2"]
        - out["Perez_Driesse"]
    )

    percent_metrics = {
        "CVRMSE_percent",
        "nMBE_percent",
        "nMAE_percent",
        "RE_percent",
    }

    out[
        "Difference_interpretation"
    ] = np.where(
        out[
            "Metric"
        ].isin(
            percent_metrics
        ),
        "percentage points",
        "metric units",
    )

    path = (
        E2_OUT
        / "Engerer2_vs_PD_sensitivity.csv"
    )

    out.to_csv(
        path,
        index=False,
    )

    print(
        f"Wrote {path.relative_to(ROOT)}"
    )

    return out


def compare_paired_robustness(
    e2_paired,
):
    pd_path = (
        PD_OUT
        / "05_Paired_IDA_vs_PVsyst_by_block.csv"
    )

    if not pd_path.exists():
        warnings.warn(
            "PD paired-bootstrap output is missing, so "
            "Reverse_transposition_paired_robustness.csv "
            "will be skipped."
        )
        return None

    pd_paired = pd.read_csv(
        pd_path
    )

    pd30 = pd_paired[
        pd_paired[
            "block_days"
        ] == BLOCK_DAYS
    ].copy()

    if len(pd30) != 9:
        raise ValueError(
            f"Expected 9 PD paired comparisons at {BLOCK_DAYS} days; "
            f"found {len(pd30)}."
        )

    pd_keep = pd30[
        [
            "System",
            "Variable",
            "Delta_RMSE_IDA_minus_PVsyst",
            "Delta_RMSE_CI95_low",
            "Delta_RMSE_CI95_high",
            "bootstrap_p_Holm",
            "significant_Holm_0.05",
            "Favored_by_RMSE",
        ]
    ].rename(
        columns={
            "Delta_RMSE_IDA_minus_PVsyst":
                "PD_Delta_RMSE_IDA_minus_PVsyst",
            "Delta_RMSE_CI95_low":
                "PD_CI95_low",
            "Delta_RMSE_CI95_high":
                "PD_CI95_high",
            "bootstrap_p_Holm":
                "PD_p_Holm",
            "significant_Holm_0.05":
                "PD_significant",
            "Favored_by_RMSE":
                "PD_favored_tool",
        }
    )

    e2_keep = e2_paired[
        [
            "System",
            "Variable",
            "Delta_RMSE_IDA_minus_PVsyst",
            "Delta_RMSE_CI95_low",
            "Delta_RMSE_CI95_high",
            "bootstrap_p_Holm",
            "significant_Holm_0.05",
            "Favored_by_RMSE",
        ]
    ].rename(
        columns={
            "Delta_RMSE_IDA_minus_PVsyst":
                "E2_Delta_RMSE_IDA_minus_PVsyst",
            "Delta_RMSE_CI95_low":
                "E2_CI95_low",
            "Delta_RMSE_CI95_high":
                "E2_CI95_high",
            "bootstrap_p_Holm":
                "E2_p_Holm",
            "significant_Holm_0.05":
                "E2_significant",
            "Favored_by_RMSE":
                "E2_favored_tool",
        }
    )

    out = pd_keep.merge(
        e2_keep,
        on=[
            "System",
            "Variable",
        ],
        how="inner",
        validate="one_to_one",
    )

    out[
        "Favored_tool_preserved"
    ] = (
        out[
            "PD_favored_tool"
        ]
        == out[
            "E2_favored_tool"
        ]
    )

    out[
        "Significance_class_preserved"
    ] = (
        out[
            "PD_significant"
        ].astype(bool)
        == out[
            "E2_significant"
        ].astype(bool)
    )

    out[
        "Delta_RMSE_change_E2_minus_PD"
    ] = (
        out[
            "E2_Delta_RMSE_IDA_minus_PVsyst"
        ]
        - out[
            "PD_Delta_RMSE_IDA_minus_PVsyst"
        ]
    )

    path = (
        E2_OUT
        / "Reverse_transposition_paired_robustness.csv"
    )

    out.to_csv(
        path,
        index=False,
    )

    print(
        f"Wrote {path.relative_to(ROOT)}"
    )

    return out


# =============================================================================
# Provenance
# =============================================================================

def write_provenance():
    text = f"""ENGERER2 REVERSE-TRANSPOSITION SENSITIVITY
============================================================

Purpose
-------
Sensitivity analysis of the finalized annual PV validation to an alternative
reverse-transposition / irradiance-input scenario.

Authoritative baseline retained unchanged
-----------------------------------------
02_canonical_data/annual_unshaded_analysis.csv

The following are inherited exactly from the finalized PD canonical dataset:
- processed measured GTI, AC power and panel temperature
- verified System A measured-GTI +1 h correction
- System B/C measured GTI source
- common synthetic analysis timestamps
- physical clock interpretation
- full azimuth-aware AOI
- Eext_tilt
- kt_tilt
- installed capacity metadata
- four agreed power-exclusion timestamps
- all analysis filters and metric conventions

Engerer2 IDA ICE inputs
-----------------------
{IDA_PATHS["A"].relative_to(ROOT)}
{IDA_PATHS["B"].relative_to(ROOT)}
{IDA_PATHS["C"].relative_to(ROOT)}

Engerer2 PVsyst inputs
----------------------
{PVSYST_PATHS["A"].relative_to(ROOT)}
{PVSYST_PATHS["B"].relative_to(ROOT)}
{PVSYST_PATHS["C"].relative_to(ROOT)}

System A Engerer2 PVsyst timing correction
------------------------------------------
A uniform +1 h timestamp correction is applied to the ENTIRE System A
Engerer2 PVsyst hourly output record:
- GlobEff / GTI
- TArray / panel temperature
- E_Grid / AC power

Systems B and C receive 0 h correction.

Correction:
    corrected timestamp = row-order timestamp + 1 h   [System A only]

No data values are scaled, interpolated or otherwise changed.

Basis:
Dedicated timing audits found that System A Engerer2 PVsyst GTI, panel
temperature and AC power all independently had their lowest RMSE at +1 h,
while System A Perez-Driesse and Systems B/C Engerer2 preferred zero lag.
The A/E2 export also uniquely referenced the weather file
Ekås_Custom_E2.MET. The original .MET file is no longer available, so the
uniform correction is retained transparently as an audited preprocessing
step. The original PVsyst source workbook remains unchanged.

Audit output:
{(E2_OUT / "PVsyst_Engerer2_timestamp_correction_audit.csv").relative_to(ROOT)}

Separate outputs
----------------
Canonical:
{E2_CANON.relative_to(ROOT)}

Analysis:
{E2_OUT.relative_to(ROOT)}

Uncertainty
-----------
30-day circular moving-block bootstrap
Replicates: {N_BOOT}
Primary paired comparison:
Delta RMSE = RMSE_IDA ICE - RMSE_PVsyst

Interpretation
--------------
This is a scenario/sensitivity analysis, not a replacement for the
Perez-Driesse baseline. Differences between the PD and E2 analyses quantify
sensitivity to the alternative irradiance reconstruction used to generate the
simulation weather inputs.
"""

    path = (
        E2_CANON
        / "ENGERER2_PROVENANCE.txt"
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print(
        f"Wrote {path.relative_to(ROOT)}"
    )


# =============================================================================
# Main
# =============================================================================

def main():
    require_inputs()

    print(
        "\nREVERSE-TRANSPOSITION SENSITIVITY: "
        "ENGERER2 vs PEREZ-DRIESSE"
    )
    print("=" * 72)
    print(
        "PVsyst E2 timing rule: "
        "System A = +1 h uniform record shift; "
        "Systems B/C = 0 h."
    )
    print(
        "The A shift applies jointly to GTI, panel temperature and AC power."
    )

    annual = build_e2_canonical()

    # Ensure timestamps are datetime after construction.
    annual["timestamp"] = pd.to_datetime(
        annual["timestamp"]
    ).dt.floor("s")

    e2_tables = run_e2_point_analysis(
        annual
    )

    print(
        "\n30-DAY ENGERER2 UNCERTAINTY / PAIRED INFERENCE"
    )
    print("=" * 72)

    ci, annual_days, days, dmap, W = (
        engerer2_metric_cis(
            annual
        )
    )

    e2_paired = (
        engerer2_paired_inference(
            annual_days,
            days,
            dmap,
            W,
        )
    )

    print(
        "\nDIRECT ENGERER2 vs PEREZ-DRIESSE COMPARISON"
    )
    print("=" * 72)

    comparison = (
        build_pd_e2_comparison(
            e2_tables
        )
    )

    robustness = (
        compare_paired_robustness(
            e2_paired
        )
    )

    write_provenance()

    print("\nSUMMARY")
    print("=" * 72)

    display = e2_paired[
        [
            "System",
            "Variable",
            "Delta_RMSE_IDA_minus_PVsyst",
            "Delta_RMSE_CI95_low",
            "Delta_RMSE_CI95_high",
            "bootstrap_p_Holm",
            "Favored_by_RMSE",
            "significant_Holm_0.05",
        ]
    ]

    print(
        "\nEngerer2 paired comparison, 30-day blocks:"
    )
    print(
        display.to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    if robustness is not None:
        print(
            "\nRobustness of favored tool across "
            "Perez-Driesse and Engerer2:"
        )

        show = robustness[
            [
                "System",
                "Variable",
                "PD_favored_tool",
                "E2_favored_tool",
                "Favored_tool_preserved",
                "PD_significant",
                "E2_significant",
                "Significance_class_preserved",
            ]
        ]

        print(
            show.to_string(
                index=False
            )
        )

        n_rank = int(
            robustness[
                "Favored_tool_preserved"
            ].sum()
        )
        n_sig = int(
            robustness[
                "Significance_class_preserved"
            ].sum()
        )

        print(
            f"\nFavored-tool ranking preserved: "
            f"{n_rank}/9 comparisons"
        )
        print(
            f"Significance classification preserved: "
            f"{n_sig}/9 comparisons"
        )

    print("\nDONE")
    print("=" * 72)
    print(
        f"Engerer2 canonical folder: "
        f"{E2_CANON.relative_to(ROOT)}"
    )
    print(
        f"Engerer2 analysis folder:  "
        f"{E2_OUT.relative_to(ROOT)}"
    )
    print(
        "\nThe authoritative Perez-Driesse files in "
        "02_canonical_data and 03_analysis_output were not modified."
    )


if __name__ == "__main__":
    main()
