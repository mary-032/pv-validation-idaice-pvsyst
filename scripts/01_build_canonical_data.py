from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd


# ============================================================
# FINAL CANONICAL BUILDER - GITHUB REPOSITORY LAYOUT
# ============================================================
#
# Public-repository paths:
#   data/        -> source/provenance inputs
#   derived_data/ -> generated canonical datasets
#
# This version supersedes the working-directory paths
# 01_source_inputs/ and 02_canonical_data/.
#
#
# Measurement provenance:
#   Original source:
#       RISE_raw10min_389.xlsx
#
#   Historical processed measurement layer:
#       Results_PVsyst_E2_hour.xlsx
#
#   IMPORTANT:
#       ONLY the measured columns from Results_PVsyst_E2_hour.xlsx
#       are used here:
#           GTI3M, GTI9M
#           Tp3M, Tp8M, Tp9M
#           P3M, P8M, P9M
#
#       ALL historical E2 simulation columns are explicitly ignored.
#
# Why use the processed measurement layer?
#   A separate raw-data audit (01a_diagnose_RISE_preprocessing_v2.py)
#   showed:
#       - panel temperature preprocessing is exactly reproducible;
#       - GTI preprocessing is >98.9% exactly reproducible;
#       - historical measured-power preprocessing cannot be fully
#         reconstructed from the currently available raw Power_* columns.
#
#   Therefore the processed measured columns preserve the actual
#   measurement layer used in the historical analysis without inventing
#   undocumented corrections.
#
# Simulation provenance:
#   IDA ICE:
#       final Perez-Driesse Syst3_PD / Syst8_PD / Syst9_PD exports
#
#   PVsyst:
#       final Perez-Driesse hourly exports
#
# Analysis clock:
#   The historical analysis workbook uses a synthetic Jan-Dec 2021 clock.
#   IDA elapsed Time is mapped to that clock:
#       Time = 1 -> 2021-01-01 01:00
#       ...
#       Time = 8736 -> 2021-12-31 00:00
#   Time = 0 is treated as the initial simulation state and excluded.
#
#   PVsyst rows are mapped:
#       row 0 -> 2021-01-01 00:00
#       ...
#       row 8759 -> 2021-12-31 23:00
#
# This produces the 8,736 common timestamps used by the frozen analysis.
# ============================================================


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "derived_data"
OUT.mkdir(parents=True, exist_ok=True)

CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

ANALYSIS_START = pd.Timestamp("2021-01-01 00:00:00")

MEASURED_PATH = (
    DATA / "historical" / "Results_PVsyst_E2_hour.xlsx"
)

RAW_RISE_PATH = (
    DATA / "measured" / "annual" / "RISE_raw10min_389.xlsx"
)

IDA_PATHS = {
    "A": DATA / "ida_ice" / "annual" / "Perez_Driesse" / "Syst3_PD.xlsx",
    "B": DATA / "ida_ice" / "annual" / "Perez_Driesse" / "Syst8_PD.xlsx",
    "C": DATA / "ida_ice" / "annual" / "Perez_Driesse" / "Syst9_PD.xlsx",
}

PVSYST_PATHS = {
    "A": DATA / "pvsyst" / "annual" / "Perez_Driesse" / "PVsyst_3_PD_h.xlsx",
    "B": DATA / "pvsyst" / "annual" / "Perez_Driesse" / "PVsyst_8_PD_h.xlsx",
    "C": DATA / "pvsyst" / "annual" / "Perez_Driesse" / "PVsyst_9_PD_h.xlsx",
}

MEASURED_COLUMNS = {
    "A": {
        "GTI": "GTI3M",
        "Tp": "Tp3M",
        "P": "P3M",
    },
    "B": {
        "GTI": "GTI9M",
        "Tp": "Tp8M",
        "P": "P8M",
    },
    "C": {
        "GTI": "GTI9M",
        "Tp": "Tp9M",
        "P": "P9M",
    },
}

# Explicit list of historical simulation columns that must never be used.
FORBIDDEN_OLD_SIMULATION_COLUMNS = {
    "GTI3IDAE2", "P3IDAE2", "Tp3IDAE2",
    "GTI8IDAE2", "P8IDAE2", "Tp8IDAE2",
    "GTI9IDAE2", "P9IDAE2", "Tp9IDAE2",
}


def check_inputs():
    required = [
        MEASURED_PATH,
        *IDA_PATHS.values(),
        *PVSYST_PATHS.values(),
        DATA
        / "shading"
        / "audited_reconstruction"
        / "Shading_results_definitive_audit.xlsx",
    ]

    missing = [p for p in required if not p.exists()]

    if missing:
        raise FileNotFoundError(
            "Missing required source files:\n"
            + "\n".join(
                f" - {p.relative_to(ROOT)}"
                for p in missing
            )
        )


def load_historical_measured_layer():
    """
    Load ONLY the measured columns from the historical processed workbook.

    Excel floating-point timestamps such as 17:59:59.999 are rounded to
    their intended whole hour before use.
    """
    xls = pd.ExcelFile(MEASURED_PATH)

    required = {
        "Date",
        "GTI3M", "GTI9M",
        "Tp3M", "Tp8M", "Tp9M",
        "P3M", "P8M", "P9M",
    }

    chosen = None
    chosen_sheet = None

    for sheet in xls.sheet_names:
        d = pd.read_excel(
            MEASURED_PATH,
            sheet_name=sheet,
        )
        d.columns = [str(c).strip() for c in d.columns]

        if required.issubset(d.columns):
            chosen = d
            chosen_sheet = sheet
            break

    if chosen is None:
        raise ValueError(
            f"Could not find the measured columns in {MEASURED_PATH.name}"
        )

    # Guardrail: make it impossible for old E2 simulation columns
    # to accidentally enter the canonical dataset.
    used = [
        "Date",
        "GTI3M", "GTI9M",
        "Tp3M", "Tp8M", "Tp9M",
        "P3M", "P8M", "P9M",
    ]

    d = chosen[used].copy()

    accidental = set(d.columns) & FORBIDDEN_OLD_SIMULATION_COLUMNS
    if accidental:
        raise RuntimeError(
            "Forbidden historical E2 simulation columns entered "
            f"the measured layer: {sorted(accidental)}"
        )

    d["timestamp"] = (
        pd.to_datetime(d["Date"], errors="coerce")
        .dt.round("h")
    )

    d = (
        d.dropna(subset=["timestamp"])
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
        .reset_index(drop=True)
    )

    if len(d) != 8760:
        raise ValueError(
            f"Historical measured layer has {len(d):,} hourly rows "
            "after timestamp normalization; expected 8,760."
        )

    if d["timestamp"].nunique() != 8760:
        raise ValueError(
            "Historical measured layer does not contain "
            "8,760 unique hourly timestamps."
        )

    expected_start = pd.Timestamp("2021-01-01 00:00:00")
    expected_end = pd.Timestamp("2021-12-31 23:00:00")

    if d["timestamp"].min() != expected_start:
        raise ValueError(
            f"Unexpected measured-layer start: {d['timestamp'].min()}"
        )

    if d["timestamp"].max() != expected_end:
        raise ValueError(
            f"Unexpected measured-layer end: {d['timestamp'].max()}"
        )

    print(
        f"  Measured layer: {MEASURED_PATH.name}/{chosen_sheet}; "
        "8,760 normalized hourly rows"
    )
    print(
        "  Old E2 simulation columns: explicitly NOT used"
    )

    return d


def measured_for_system(measured, system):
    spec = MEASURED_COLUMNS[system]

    out = pd.DataFrame({
        "timestamp": measured["timestamp"],
        "GTI_measured_Wm2": pd.to_numeric(
            measured[spec["GTI"]],
            errors="coerce",
        ),
        "Tp_measured_C": pd.to_numeric(
            measured[spec["Tp"]],
            errors="coerce",
        ),
        "P_measured_W": pd.to_numeric(
            measured[spec["P"]],
            errors="coerce",
        ),
    })

    # VERIFIED SYSTEM-A GTI CLOCK CORRECTION
    # --------------------------------------
    # The historical GTI3M series is labeled one hour earlier than the
    # corresponding physical/simulation hour. This was diagnosed independently
    # because BOTH final Perez-Driesse simulations (IDA ICE and PVsyst) show the
    # same one-hour displacement relative to GTI3M, while System B/C do not.
    #
    # Correcting the measurement clock means:
    #     old GTI3M[t] belongs at timestamp t+1 h
    #
    # In the common hourly table this is equivalent to shifting the GTI values
    # down by one row. Temperature and power are NOT shifted here.
    #
    # Diagnostic effect with the current final PD exports:
    #   IDA A GTI RMSE:     131.32 -> 15.34 W/m²
    #   IDA A CV(RMSE):      56.41 ->  6.59 %
    #   IDA A nMBE:          -4.24 -> -4.01 %
    #
    # It also restores the System-A daytime mask used for temperature/power.
    if system == "A":
        out["GTI_measured_Wm2"] = out["GTI_measured_Wm2"].shift(1)

    return out


def read_ida(system):
    """
    Read final IDA ICE Perez-Driesse workbook.

    No variable-specific time-shifting is performed here. This is the
    transparent baseline alignment:
        timestamp = 2021-01-01 00:00 + Time hours
        Time > 0 only.
    """
    path = IDA_PATHS[system]

    def read_sheet(name):
        d = pd.read_excel(
            path,
            sheet_name=name,
        )
        d.columns = [str(c).strip() for c in d.columns]

        if "Time" not in d.columns:
            raise ValueError(
                f"{path.name}/{name} has no Time column."
            )

        d["Time"] = pd.to_numeric(
            d["Time"],
            errors="coerce",
        )

        d = d[d["Time"].notna()].copy()
        return d

    power = read_sheet("ProducedPower")
    pcols = [
        c for c in power.columns
        if "produced power" in c.lower()
    ]
    if not pcols:
        raise ValueError(
            f"No Produced power column in {path.name}"
        )

    temp = read_sheet("EL-TEMPERATURES")
    tcols = [
        c for c in temp.columns
        if c.lower().startswith("panel temperature")
    ]
    if not tcols:
        raise ValueError(
            f"No panel temperature columns in {path.name}"
        )

    irr = read_sheet("IRRADIANCE")
    gcols = [
        c for c in irr.columns
        if c.lower().startswith(
            "panel effective irradiance"
        )
    ]
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
        p.merge(t, on="ida_time_h", how="inner")
         .merge(g, on="ida_time_h", how="inner")
    )

    out = out[out["ida_time_h"] > 0].copy()

    out["timestamp"] = (
        ANALYSIS_START
        + pd.to_timedelta(
            out["ida_time_h"],
            unit="h",
        )
    ).dt.floor("s")

    if len(out) != 8736:
        warnings.warn(
            f"{path.name} produced {len(out):,} rows after Time>0; "
            "expected 8,736."
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
    Read final PVsyst Perez-Driesse hourly export.

    The arbitrary calendar year stored inside each PVsyst export is ignored.
    Row order is mapped to the synthetic 2021 analysis clock.
    """
    path = PVSYST_PATHS[system]

    raw = pd.read_excel(path, header=None)

    header_row = None

    for i in range(min(60, len(raw))):
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
    d.columns = [str(c).strip() for c in d.columns]

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

    d["pvsyst_hour_index"] = np.arange(len(d))

    # Power: prefer the explicit W column.
    if "E_Grid.1" in d.columns:
        power_w = pd.to_numeric(
            d["E_Grid.1"],
            errors="coerce",
        )
    else:
        egrid_cols = [
            c for c in d.columns
            if c.lower().startswith("e_grid")
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
        "pvsyst_hour_index": d["pvsyst_hour_index"],
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

    out["timestamp"] = (
        ANALYSIS_START
        + pd.to_timedelta(
            out["pvsyst_hour_index"],
            unit="h",
        )
    ).dt.floor("s")

    print(
        f"  PVsyst {system}: {path.name}; 8,760 hourly rows"
    )

    return out


def geometry_for_timestamps(timestamps):
    """
    Calculate physically preferred full azimuth-aware solar geometry.

    IMPORTANT CLOCK HANDLING
    ------------------------
    The canonical annual dataset uses the historical synthetic Jan-Dec 2021
    analysis clock.

    An empirical diagnostic of the original RISE 10-minute irradiance series
    shows that the logger timestamps are Swedish local CIVIL time
    (CET in winter, CEST in summer), not fixed CET all year.

    For solar geometry we therefore:
      1. map Jan-May -> physical 2021,
      2. map Jun-Dec -> physical 2020,
      3. interpret each reconstructed timestamp directly as
         Europe/Stockholm local civil time.

    This preserves the physical wall-clock time used by the RISE logger
    when calculating solar position, AOI, Eext_tilt and kt_tilt.

    EXTRATERRESTRIAL IRRADIANCE
    ---------------------------
    We retain the original documented extraterrestrial-normal irradiance
    formula from data.m, including Esc = 1361.1 W/m²:

        beta = 2*pi*doy/365
        E0 = 1.00011
             + 0.034221*cos(beta)
             + 0.00128*sin(beta)
             + 0.000719*cos(2*beta)
             + 0.000077*sin(2*beta)
        Eextn = 1361.1 * E0

    The old simplified 2-D incidence angle is NOT used.

    Instead pvlib calculates the full 3-D azimuth-aware AOI, and

        Eext_tilt = Eextn * max(cos(AOI), 0)

    with Eext_tilt set to zero when the sun is below the horizon.
    """
    try:
        import pvlib
    except ImportError as exc:
        raise ImportError(
            "pvlib is required for the full azimuth-aware geometry. "
            "Install it in the project environment before continuing."
        ) from exc

    s = CFG["site"]
    analysis_ts = pd.DatetimeIndex(pd.to_datetime(timestamps)).floor("s")

    # Reconstruct the real study year from the synthetic Jan-Dec 2021 clock.
    physical_naive = []
    for t in analysis_ts:
        physical_year = 2021 if t.month <= 5 else 2020
        physical_naive.append(t.replace(year=physical_year))

    physical_naive = pd.DatetimeIndex(physical_naive)

    # Empirical logger-clock diagnostic:
    # the original RISE timestamps are Swedish civil time
    # (CET in winter, CEST in summer), not fixed CET all year.
    #
    # Therefore the reconstructed physical study timestamps are localized
    # directly as Europe/Stockholm wall time.
    # The RISE logger contains a regular 144 ten-minute records even on
    # DST-transition days, so the autumn 02:00 hour is not duplicated and the
    # spring 02:00 hour is not omitted. Pandas therefore cannot infer the
    # autumn occurrence from sequence structure.
    #
    # Resolve the single ambiguous autumn hour as standard time (CET) and
    # shift the nonexistent spring hour forward. Both transition hours occur
    # at night at this site, with measured GTI = 0, so this convention has no
    # effect on the daytime AOI / Eext_tilt / kt_tilt analysis.
    physical_local = physical_naive.tz_localize(
        s["timezone"],
        ambiguous=False,
        nonexistent="shift_forward",
    )

    sol = pvlib.solarposition.get_solarposition(
        physical_local,
        latitude=float(s["latitude"]),
        longitude=float(s["longitude"]),
        altitude=float(s["altitude_m"]),
    )

    aoi = pvlib.irradiance.aoi(
        float(s["surface_tilt_deg"]),
        float(s["surface_azimuth_deg_pvlib"]),
        sol["apparent_zenith"],
        sol["azimuth"],
    )

    # Original documented Eextn formula from data.m.
    doy = physical_local.dayofyear.to_numpy(dtype=float)
    beta = (2.0 * np.pi * doy) / 365.0

    e0 = (
        1.00011
        + 0.034221 * np.cos(beta)
        + 0.00128 * np.sin(beta)
        + 0.000719 * np.cos(2.0 * beta)
        + 0.000077 * np.sin(2.0 * beta)
    )

    eextn = 1361.1 * e0

    aoi_arr = np.asarray(aoi, dtype=float)
    cos_aoi = np.cos(np.deg2rad(aoi_arr))

    apparent_elevation = np.asarray(
        sol["apparent_elevation"],
        dtype=float,
    )

    eext_tilt = np.where(
        (apparent_elevation > 0.0) & (cos_aoi > 0.0),
        eextn * cos_aoi,
        0.0,
    )

    g = pd.DataFrame({
        "timestamp": analysis_ts,
        "physical_local_timestamp": [
            x.isoformat() for x in physical_local
        ],
        "physical_utc_timestamp": [
            x.tz_convert("UTC").isoformat() for x in physical_local
        ],
        "solar_azimuth_deg": np.asarray(sol["azimuth"], dtype=float),
        "solar_elevation_deg": apparent_elevation,
        "Eext_normal_Wm2": eextn,
        "Eext_tilt_Wm2": eext_tilt,
        "AOI_deg": aoi_arr,
    })

    audit_path = OUT / "_geometry_full_azimuth_aware.csv"
    g.to_csv(
        audit_path,
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
    )

    print(
        "  Geometry: full azimuth-aware pvlib AOI + documented "
        "Esc=1361.1 Eextn formula"
    )
    print(
        f"  Geometry site: {s['latitude']}, {s['longitude']}; "
        f"tilt={s['surface_tilt_deg']}°, "
        f"azimuth={s['surface_azimuth_deg_pvlib']}°"
    )
    print(
        "  Geometry clock: physical Jun-Dec 2020 / Jan-May 2021, "
        f"localized directly as {s['timezone']} civil time"
    )

    return (
        g[["timestamp", "Eext_tilt_Wm2", "AOI_deg"]].copy(),
        "FULL_AZIMUTH_AWARE_PVLIB_AOI + documented Esc=1361.1 Eextn + CIVIL_TIME",
    )

def build_annual():
    print("\nANNUAL - AUDITED PROCESSED MEASUREMENT LAYER")
    print("=" * 64)

    measured = load_historical_measured_layer()

    parts = []

    for system in ("A", "B", "C"):
        m = measured_for_system(
            measured,
            system,
        )
        i = read_ida(system)
        p = read_pvsyst(system)

        d = (
            m.merge(
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

        meta = CFG["systems"][system]

        d["system"] = system
        d["rise_system"] = meta["rise_system"]
        d["kWp"] = meta["kWp"]

        parts.append(d)

        print(
            f"  System {system}: {len(d):,} common timestamps; "
            f"{d['timestamp'].min()} -> "
            f"{d['timestamp'].max()}"
        )

    annual = (
        pd.concat(parts, ignore_index=True)
        .sort_values(["timestamp", "system"])
        .reset_index(drop=True)
    )

    common_times = (
        annual["timestamp"]
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    geom, geometry_status = geometry_for_timestamps(
        common_times
    )

    annual = annual.merge(
        geom,
        on="timestamp",
        how="left",
        validate="many_to_one",
    )

    annual["kt_tilt"] = np.where(
        pd.to_numeric(
            annual["Eext_tilt_Wm2"],
            errors="coerce",
        ) > 0,
        pd.to_numeric(
            annual["GTI_measured_Wm2"],
            errors="coerce",
        )
        / pd.to_numeric(
            annual["Eext_tilt_Wm2"],
            errors="coerce",
        ),
        np.nan,
    )

    annual["timestamp"] = (
        pd.to_datetime(annual["timestamp"])
        .dt.floor("s")
    )

    keep = [
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
        "GTI_PVsyst_Wm2",
        "P_PVsyst_W",
        "Tp_PVsyst_C",
        "Eext_tilt_Wm2",
        "AOI_deg",
        "kt_tilt",
    ]

    annual = annual[keep]

    out_path = OUT / "annual_unshaded_analysis.csv"

    annual.to_csv(
        out_path,
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
    )

    n_times = annual["timestamp"].nunique()
    expected = int(
        CFG["annual"]["expected_common_timestamps"]
    )

    print("\nANNUAL CANONICAL RESULT")
    print("-" * 64)
    print(f"Rows:              {len(annual):,}")
    print(f"Unique timestamps: {n_times:,}")
    print(
        f"First timestamp:   {annual['timestamp'].min()}"
    )
    print(
        f"Last timestamp:    {annual['timestamp'].max()}"
    )

    if n_times != expected:
        raise ValueError(
            f"Expected {expected:,} common timestamps; got {n_times:,}."
        )

    if len(annual) != expected * 3:
        raise ValueError(
            f"Expected {expected*3:,} annual rows; got {len(annual):,}."
        )

    print(
        f"Common timestamp count: PASS ({expected:,})"
    )

    write_provenance(
        annual=annual,
        geometry_status=geometry_status,
    )


def write_provenance(annual, geometry_status):
    """
    Write a human-readable provenance record and a compact CSV audit.
    """
    txt = f"""ANNUAL CANONICAL DATA PROVENANCE
================================

Canonical output:
  derived_data/annual_unshaded_analysis.csv

MEASURED DATA
-------------
Original raw source:
  data/measured/annual/RISE_raw10min_389.xlsx

Historical processed measurement layer used in the canonical dataset:
  data/historical/Results_PVsyst_E2_hour.xlsx

Measured columns used:
  System A: GTI3M, Tp3M, P3M
  System B: GTI9M, Tp8M, P8M
  System C: GTI9M, Tp9M, P9M

Verified System-A irradiance clock correction:
  GTI3M is shifted forward by one hour before analysis
  (old GTI3M[t] is assigned to timestamp t+1 h).
  No corresponding shift is applied to Tp3M or P3M.

Historical E2 simulation columns:
  NOT USED.

Reason:
  Raw-data audit with 01a_diagnose_RISE_preprocessing_v2.py showed:
  - panel-temperature preprocessing is exactly reproducible;
  - GTI preprocessing is almost completely reproducible;
  - historical measured-power preprocessing cannot be fully reconstructed
    from the currently available raw Power_* columns without undocumented
    corrections.

Therefore the historical measured columns are treated as the authoritative
processed-measurement layer for reproduction of the published/frozen analysis.

ANALYSIS CLOCK
--------------
The processed measurement layer uses a synthetic Jan-Dec 2021 hourly clock.
Excel floating timestamp artifacts are rounded to the nearest whole hour.

IDA ICE:
  Time = 0 excluded as initial state.
  timestamp = 2021-01-01 00:00 + Time hours.
  No variable-specific alignment correction is applied in this builder.

PVsyst:
  internal arbitrary export years ignored.
  row 0 = 2021-01-01 00:00.
  rows remain in exported order.

Canonical common period:
  {annual['timestamp'].min()}
  through
  {annual['timestamp'].max()}

Common timestamps:
  {annual['timestamp'].nunique():,}

SIMULATION SOURCES
------------------
IDA ICE:
  Syst3_PD.xlsx
  Syst8_PD.xlsx
  Syst9_PD.xlsx

PVsyst:
  PVsyst_3_PD_h.xlsx
  PVsyst_8_PD_h.xlsx
  PVsyst_9_PD_h.xlsx

GEOMETRY / WEATHER BINS
-----------------------
Status:
  {geometry_status}

The final weather-bin analysis uses the geometry reconstructed here,
with AOI < 80° and the sky-condition thresholds defined in config.json.

NEXT VALIDATION
---------------
Run:
  python scripts/02_run_analysis.py

Annual mismatches should be investigated as simulation-source,
alignment, or software-environment differences. Do not alter measured
values merely to force agreement with archived results.
"""

    txt_path = OUT / "ANNUAL_PROVENANCE_AUDIT.txt"
    txt_path.write_text(
        txt,
        encoding="utf-8",
    )

    rows = [
        {
            "component": "Measured raw source",
            "source": "RISE_raw10min_389.xlsx",
            "status": "AUDITED",
            "note": (
                "Raw source retained. Historical processed power "
                "not fully reconstructible from available raw Power_*."
            ),
        },
        {
            "component": "Measured canonical layer",
            "source": "Results_PVsyst_E2_hour.xlsx measured columns only",
            "status": "AUTHORITATIVE_PROCESSED_LAYER",
            "note": "All historical E2 simulation columns explicitly excluded.",
        },
        {
            "component": "IDA ICE A/B/C",
            "source": "Syst3_PD.xlsx; Syst8_PD.xlsx; Syst9_PD.xlsx",
            "status": "FINAL_PD_INPUTS",
            "note": "Time=0 excluded; no variable-specific alignment correction.",
        },
        {
            "component": "PVsyst A/B/C",
            "source": (
                "PVsyst_3_PD_h.xlsx; PVsyst_8_PD_h.xlsx; "
                "PVsyst_9_PD_h.xlsx"
            ),
            "status": "FINAL_PD_INPUTS",
            "note": "Internal arbitrary calendar years ignored; row order retained.",
        },
        {
            "component": "Weather-bin geometry",
            "source": geometry_status,
            "status": (
                "APPROVED"
                if geometry_status.startswith("APPROVED")
                else "UNVERIFIED"
            ),
            "note": "Must reproduce frozen weather-bin results before acceptance.",
        },
    ]

    pd.DataFrame(rows).to_csv(
        OUT / "ANNUAL_PROVENANCE_AUDIT.csv",
        index=False,
    )

    print(
        "Provenance audit:     wrote ANNUAL_PROVENANCE_AUDIT.txt/.csv"
    )


def build_shading():
    """
    Retain the already-audited definitive shading reconstruction.
    """
    path = (
        DATA
        / "shading"
        / "audited_reconstruction"
        / "Shading_results_definitive_audit.xlsx"
    )

    d = pd.read_excel(
        path,
        sheet_name="Reconstruction",
    )

    ida_cols = {
        "A": "A_IDA_aligned",
        "B": "B_IDA_corrected",
        "C": "C_IDA",
    }

    parts = []

    for system in ("A", "B", "C"):
        meta = CFG["systems"][system]

        parts.append(
            pd.DataFrame({
                "timestamp": pd.to_datetime(
                    d["DateTime"]
                ).dt.floor("s"),
                "system": system,
                "rise_system": meta["rise_system"],
                "kWp": meta["kWp"],
                "GTI_measured_Wm2": pd.to_numeric(
                    d[f"{system}_GTI"],
                    errors="coerce",
                ),
                "P_measured_W": pd.to_numeric(
                    d[f"{system}_Measured"],
                    errors="coerce",
                ),
                "P_IDA_W": pd.to_numeric(
                    d[ida_cols[system]],
                    errors="coerce",
                ),
                "P_PVsyst_W": pd.to_numeric(
                    d[f"{system}_PVsyst"],
                    errors="coerce",
                ),
            })
        )

    out = (
        pd.concat(parts, ignore_index=True)
        .sort_values(["timestamp", "system"])
    )

    out.to_csv(
        OUT / "shading_analysis.csv",
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
    )

    print(
        f"Shading canonical: {len(out):,} rows"
    )


if __name__ == "__main__":
    check_inputs()

    print("\nBUILD CANONICAL DATA - AUDITED PROVENANCE")
    print("=" * 64)
    print(f"Repository root:      {ROOT}")
    print(f"Source-data folder:   {DATA.relative_to(ROOT)}")
    print(f"Derived-data folder:  {OUT.relative_to(ROOT)}")
    if RAW_RISE_PATH.exists():
        print(f"Raw RISE archive:     found ({RAW_RISE_PATH.relative_to(ROOT)})")
    else:
        print("Raw RISE archive:     not present (not required by this builder)")

    build_shading()
    build_annual()
