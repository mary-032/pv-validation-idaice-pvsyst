from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "02_canonical_data"
OUT = ROOT / "03_analysis_output"
OUT.mkdir(exist_ok=True)

CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

ANNUAL_PATH = CANON / "annual_unshaded_analysis.csv"
SHADING_PATH = CANON / "shading_analysis.csv"

POWER_EXCLUSIONS = pd.to_datetime(CFG["annual"]["power_excluded_timestamps"])
POWER_EXCLUSION_SET = set(POWER_EXCLUSIONS)

EXPECTED_ANNUAL_TIMESTAMPS = int(CFG["annual"]["expected_common_timestamps"])
EXPECTED_ANNUAL_ROWS = EXPECTED_ANNUAL_TIMESTAMPS * 3


def calculate_stats(measured, simulated):
    """Frozen convention: error = simulated - measured."""
    m = pd.to_numeric(measured, errors="coerce")
    s = pd.to_numeric(simulated, errors="coerce")

    valid = m.notna() & s.notna()
    m = m[valid].to_numpy(dtype=float)
    s = s[valid].to_numpy(dtype=float)

    if len(m) == 0:
        return None

    error = s - m
    mean_measured = float(np.mean(m))

    rmse = float(np.sqrt(np.mean(error ** 2)))
    mae = float(np.mean(np.abs(error)))
    mbe = float(np.mean(error))

    # Frozen September convention.
    summed_normalized_bias = (
        float(np.sum(error) / np.sum(m) * 100.0)
        if np.sum(m) != 0
        else np.nan
    )

    cvrmse = (
        float(rmse / mean_measured * 100.0)
        if mean_measured != 0
        else np.nan
    )

    nmae = (
        float(mae / mean_measured * 100.0)
        if mean_measured != 0
        else np.nan
    )

    ss_res = float(np.sum((s - m) ** 2))
    ss_tot = float(np.sum((m - mean_measured) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot != 0 else np.nan

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


def check_annual_structure(df):
    required = {
        "timestamp", "system", "kWp",
        "GTI_measured_Wm2", "P_measured_W", "Tp_measured_C",
        "GTI_IDA_Wm2", "P_IDA_W", "Tp_IDA_C",
        "GTI_PVsyst_Wm2", "P_PVsyst_W", "Tp_PVsyst_C",
        "kt_tilt", "AOI_deg",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            "annual_unshaded_analysis.csv is missing columns: "
            + ", ".join(missing)
        )

    duplicates = df.duplicated(["timestamp", "system"], keep=False)
    if duplicates.any():
        sample = df.loc[duplicates, ["timestamp", "system"]].head(10)
        raise ValueError(
            "Duplicate timestamp-system rows found:\n"
            + sample.to_string(index=False)
        )

    unique_times = df["timestamp"].nunique()

    print("\nANNUAL CANONICAL CHECK")
    print("=" * 48)
    print(f"Rows:              {len(df):,}")
    print(f"Unique timestamps: {unique_times:,}")
    print(f"Systems:           {sorted(df['system'].unique().tolist())}")

    if len(df) != EXPECTED_ANNUAL_ROWS:
        raise ValueError(
            f"Annual canonical dataset has {len(df)} rows; "
            f"expected {EXPECTED_ANNUAL_ROWS}."
        )

    if unique_times != EXPECTED_ANNUAL_TIMESTAMPS:
        raise ValueError(
            f"Annual canonical dataset has {unique_times} unique timestamps; "
            f"expected {EXPECTED_ANNUAL_TIMESTAMPS}."
        )

    # Confirm all four frozen power-exclusion hours are actually in the file.
    missing_exclusions = [
        t for t in POWER_EXCLUSIONS
        if not (df["timestamp"] == t).any()
    ]
    if missing_exclusions:
        raise ValueError(
            "Frozen power-exclusion timestamps missing from canonical data: "
            + ", ".join(str(x) for x in missing_exclusions)
        )

    print("Annual structure:   PASS")


def run_annual_analysis():
    if not ANNUAL_PATH.exists():
        print("ANNUAL: 02_canonical_data/annual_unshaded_analysis.csv is missing.")
        return False

    annual = pd.read_csv(ANNUAL_PATH, parse_dates=["timestamp"])
    check_annual_structure(annual)

    table4 = []
    table5 = []
    table6 = []
    monthly_rows = []
    weather_rows = []
    removal_rows = []

    for system in ("A", "B", "C"):
        d = annual[annual["system"] == system].copy()

        # Final daytime rule: system-specific measured GTI > 0.
        daytime = d[
            pd.to_numeric(d["GTI_measured_Wm2"], errors="coerce") > 0
        ].copy()

        # ----------------------------------------------------------
        # Table 4: GTI
        # No residual GTI outlier removal in the frozen pipeline.
        # ----------------------------------------------------------
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

        # ----------------------------------------------------------
        # Table 5: Panel temperature
        # No residual temperature outlier removal.
        # ----------------------------------------------------------
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

        # ----------------------------------------------------------
        # Table 6: AC power
        # Remove exactly the four common frozen timestamps.
        # ----------------------------------------------------------
        power_data = daytime[
            ~daytime["timestamp"].isin(POWER_EXCLUSION_SET)
        ].copy()

        removal_rows.append({
            "System": system,
            "daytime_rows_before_power_exclusions": len(daytime),
            "power_rows_after_four_timestamp_exclusions": len(power_data),
            "rows_removed": len(daytime) - len(power_data),
        })

        for software, sim_col in (
            ("IDA ICE", "P_IDA_W"),
            ("PVsyst", "P_PVsyst_W"),
        ):
            st = calculate_stats(
                power_data["P_measured_W"],
                power_data[sim_col],
            )

            # Monthly RMSE/kWp:
            # cleaned hourly W -> hourly kWh -> monthly sums
            # -> RMSE across months -> divide by installed kWp.
            tmp = power_data[
                ["timestamp", "P_measured_W", sim_col]
            ].copy()

            tmp["P_measured_W"] = pd.to_numeric(
                tmp["P_measured_W"], errors="coerce"
            )
            tmp[sim_col] = pd.to_numeric(
                tmp[sim_col], errors="coerce"
            )
            tmp = tmp.dropna(
                subset=["P_measured_W", sim_col]
            )

            tmp["month"] = tmp["timestamp"].dt.to_period("M")

            monthly = (
                tmp.groupby("month")[["P_measured_W", sim_col]]
                .sum()
                / 1000.0
            )

            monthly["difference_kWh"] = (
                monthly[sim_col] - monthly["P_measured_W"]
            )

            rmse_month_kwh = float(
                np.sqrt(np.mean(monthly["difference_kWh"] ** 2))
            )

            kwp = float(d["kWp"].iloc[0])
            rmse_month_per_kwp = rmse_month_kwh / kwp

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

        # ----------------------------------------------------------
        # Weather bins / Figure 3
        # Same cleaned power mask + AOI < 80°.
        # ----------------------------------------------------------
        weather_data = power_data.copy()
        weather_data["kt_tilt"] = pd.to_numeric(
            weather_data["kt_tilt"], errors="coerce"
        )
        weather_data["AOI_deg"] = pd.to_numeric(
            weather_data["AOI_deg"], errors="coerce"
        )

        weather_data = weather_data[
            weather_data["kt_tilt"].notna()
            & weather_data["AOI_deg"].notna()
            & (
                weather_data["AOI_deg"]
                < float(CFG["annual"]["weather_aoi_limit_deg"])
            )
        ].copy()

        for bin_cfg in CFG["sky_bins"]:
            lo = float(bin_cfg["min"])
            hi = bin_cfg["max"]

            in_bin = weather_data["kt_tilt"] >= lo
            if hi is not None:
                hi = float(hi)
                in_bin &= weather_data["kt_tilt"] < hi

            b = weather_data[in_bin]

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
                        "Sky_condition": bin_cfg["name"],
                        "kt_min": lo,
                        "kt_max": np.nan if hi is None else hi,
                        "Software": software,
                        **st,
                    })

    # Save.
    pd.DataFrame(table4).to_csv(
        OUT / "Table4_GTI_recomputed.csv", index=False
    )
    pd.DataFrame(table5).to_csv(
        OUT / "Table5_Temperature_recomputed.csv", index=False
    )
    pd.DataFrame(table6).to_csv(
        OUT / "Table6_Power_recomputed.csv", index=False
    )
    pd.DataFrame(monthly_rows).to_csv(
        OUT / "Monthly_RMSE_recomputed.csv", index=False
    )
    pd.DataFrame(weather_rows).to_csv(
        OUT / "Figure3_weather_bins_recomputed.csv", index=False
    )
    pd.DataFrame(removal_rows).to_csv(
        OUT / "Power_exclusion_audit.csv", index=False
    )

    print("\nANNUAL ANALYSIS")
    print("=" * 48)
    print("Wrote Table4_GTI_recomputed.csv")
    print("Wrote Table5_Temperature_recomputed.csv")
    print("Wrote Table6_Power_recomputed.csv")
    print("Wrote Monthly_RMSE_recomputed.csv")
    print("Wrote Figure3_weather_bins_recomputed.csv")
    print("Wrote Power_exclusion_audit.csv")

    return True


def run_shading_analysis():
    if not SHADING_PATH.exists():
        print("SHADING: 02_canonical_data/shading_analysis.csv is missing.")
        return False

    d = pd.read_csv(SHADING_PATH, parse_dates=["timestamp"])

    if len(d) != 3600:
        raise ValueError(
            f"Shading canonical dataset has {len(d)} rows; expected 3600."
        )

    counts = d.groupby("system").size().to_dict()
    if counts != {"A": 1200, "B": 1200, "C": 1200}:
        raise ValueError(
            "Unexpected shading row counts by system: "
            + str(counts)
        )

    sh = CFG["shading"]

    periods = {
        "Clear_day_2023-06-05": (
            pd.Timestamp(sh["clear_start"]),
            pd.Timestamp(sh["clear_end"]),
        ),
        "Partly_cloudy_day_2023-05-15": (
            pd.Timestamp(sh["cloudy_start"]),
            pd.Timestamp(sh["cloudy_end"]),
        ),
        "Full_period_2023-05-01_to_2023-06-19": (
            pd.Timestamp(sh["full_start"]),
            pd.Timestamp(sh["full_end"]),
        ),
    }

    energy_rows = []

    # Hour-ending convention:
    # start < timestamp <= end.
    for period_name, (start, end) in periods.items():
        period = d[
            (d["timestamp"] > start)
            & (d["timestamp"] <= end)
        ].copy()

        for system in ("A", "B", "C"):
            s = period[period["system"] == system].copy()

            measured_kwh = (
                pd.to_numeric(
                    s["P_measured_W"], errors="coerce"
                ).sum()
                / 1000.0
            )

            for software, sim_col in (
                ("IDA ICE", "P_IDA_W"),
                ("PVsyst", "P_PVsyst_W"),
            ):
                simulated_kwh = (
                    pd.to_numeric(
                        s[sim_col], errors="coerce"
                    ).sum()
                    / 1000.0
                )

                difference_kwh = simulated_kwh - measured_kwh

                energy_rows.append({
                    "period": period_name,
                    "System": system,
                    "Software": software,
                    "n_intervals": len(s),
                    "measured_kWh": measured_kwh,
                    "simulated_kWh": simulated_kwh,
                    "difference_kWh": difference_kwh,
                    "difference_fraction": (
                        difference_kwh / measured_kwh
                        if measured_kwh != 0
                        else np.nan
                    ),
                    "difference_percent": (
                        difference_kwh / measured_kwh * 100.0
                        if measured_kwh != 0
                        else np.nan
                    ),
                })

    pd.DataFrame(energy_rows).to_csv(
        OUT / "Shading_energy_recomputed.csv",
        index=False,
    )

    # Full-period hourly diagnostics:
    # measured GTI > 0; no outlier removal.
    start, end = periods[
        "Full_period_2023-05-01_to_2023-06-19"
    ]

    full = d[
        (d["timestamp"] > start)
        & (d["timestamp"] <= end)
    ].copy()

    diagnostic_rows = []

    for system in ("A", "B", "C"):
        s = full[full["system"] == system].copy()

        s = s[
            pd.to_numeric(
                s["GTI_measured_Wm2"], errors="coerce"
            ) > 0
        ].copy()

        for software, sim_col in (
            ("IDA ICE", "P_IDA_W"),
            ("PVsyst", "P_PVsyst_W"),
        ):
            st = calculate_stats(
                s["P_measured_W"],
                s[sim_col],
            )

            diagnostic_rows.append({
                "System": system,
                "Software": software,
                **st,
            })

    pd.DataFrame(diagnostic_rows).to_csv(
        OUT / "Shading_hourly_diagnostics_recomputed.csv",
        index=False,
    )

    print("\nSHADING ANALYSIS")
    print("=" * 48)
    print("Canonical rows: 3,600")
    print("Wrote Shading_energy_recomputed.csv")
    print("Wrote Shading_hourly_diagnostics_recomputed.csv")

    return True


def write_run_summary():
    lines = [
        "PV validation analysis run",
        "==========================",
        "",
        "Frozen conventions:",
        "- Error sign: simulated - measured",
        "- Annual daytime filter: system-specific measured GTI > 0 W/m2",
        "- GTI residual outlier deletion: none",
        "- Temperature residual outlier deletion: none",
        "- Power exclusions: exactly four common timestamps",
        "- nMBE and RE: sum(error) / sum(measured) * 100",
        "- Weather bins: cleaned power mask + AOI < 80 deg",
        "- Shading timestamps: hour-ending",
        "- Shading outlier deletion: none",
    ]

    (OUT / "Analysis_run_summary.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    print("\nPV VALIDATION - FINAL ANALYSIS")
    print("=" * 48)

    shading_ok = run_shading_analysis()
    annual_ok = run_annual_analysis()
    write_run_summary()

    print("\nDONE")
    print("=" * 48)
    print(f"Shading analysis: {'OK' if shading_ok else 'SKIPPED'}")
    print(f"Annual analysis:  {'OK' if annual_ok else 'SKIPPED'}")
    print(f"Output folder:    {OUT}")
