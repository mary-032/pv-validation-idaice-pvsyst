from pathlib import Path
import numpy as np
import pandas as pd


# =============================================================================
# 09 - TEMPORAL AGGREGATION SENSITIVITY
# =============================================================================
#
# PURPOSE
# -------
# Test whether the relative IDA ICE vs PVsyst power-performance conclusions
# depend on the temporal aggregation of the comparison.
#
# The same finalized annual power records are evaluated at:
#
#   1. Hourly power        [W]
#   2. Daily energy        [kWh/day]
#   3. Monthly energy      [kWh/month]
#
# for both:
#
#   - Perez-Driesse baseline
#   - corrected Engerer2 sensitivity scenario
#
# IMPORTANT
# ---------
# This script does NOT create any sub-hourly simulation data.
# It only aggregates the finalized hourly simulation/measured records.
#
# The annual power-record rules are kept identical to the finalized analysis:
#
#   * measured GTI > 0
#   * paired nonmissing measured/simulated power
#   * exclude exactly four gross-error timestamps:
#       2021-02-02 12:00
#       2021-02-02 13:00
#       2021-04-02 13:00
#       2021-04-30 13:00
#
# Error convention:
#
#       error = simulated - measured
#
# Metrics reported at each temporal scale:
#
#   RMSE
#   CVRMSE = RMSE / mean(measured) * 100
#   MAE
#   nMAE
#   MBE
#   nMBE = sum(sim - meas) / sum(measured) * 100
#   RE   = same annual/aggregate relative energy-bias convention
#   R²
#
# Additional outputs:
#
#   * RMSE normalized by installed capacity [W/kWp or kWh/kWp]
#   * direct paired IDA ICE - PVsyst RMSE difference
#   * ranking preservation across hourly/daily/monthly aggregation
#   * annual measured/simulated energy and annual energy bias
#
# INTERPRETATION
# --------------
# This is a temporal-aggregation sensitivity analysis. It asks whether the
# tool comparison changes when hour-to-hour errors are averaged into daily
# and monthly energy totals.
#
# It is NOT a substitute for a true sub-hourly simulation.
#
# OUTPUTS
# -------
# results/temporal_aggregation/
#
#   09_Temporal_aggregation_metrics.csv
#   09_Paired_IDA_vs_PVsyst_by_aggregation.csv
#   09_Aggregation_ranking_robustness.csv
#   09_Annual_energy_summary.csv
#   09_TEMPORAL_AGGREGATION_SENSITIVITY.xlsx
#
# =============================================================================


ROOT = Path(__file__).resolve().parents[1]

PD_CANON = (
    ROOT
    / "derived_data"
    / "annual_unshaded_analysis.csv"
)

E2_CANON = (
    ROOT
    / "derived_data"
    / "annual_unshaded_analysis_Engerer2.csv"
)

OUT = (
    ROOT
    / "results"
    / "temporal_aggregation"
)
OUT.mkdir(
    parents=True,
    exist_ok=True,
)

POWER_EXCLUSIONS = pd.to_datetime([
    "2021-02-02 12:00:00",
    "2021-02-02 13:00:00",
    "2021-04-02 13:00:00",
    "2021-04-30 13:00:00",
])


# =============================================================================
# Helpers
# =============================================================================

def require_inputs():
    missing = [
        p for p in (
            PD_CANON,
            E2_CANON,
        )
        if not p.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing required canonical dataset(s):\n"
            + "\n".join(
                f"  - {p.relative_to(ROOT)}"
                for p in missing
            )
        )


def load_canonical(path):
    d = pd.read_csv(
        path,
        parse_dates=["timestamp"],
    )

    d["timestamp"] = pd.to_datetime(
        d["timestamp"]
    ).dt.floor("s")

    expected_systems = {
        "A",
        "B",
        "C",
    }

    actual_systems = set(
        d["system"].dropna().unique()
    )

    if actual_systems != expected_systems:
        raise ValueError(
            f"{path.name}: expected systems {expected_systems}, "
            f"found {actual_systems}."
        )

    return d


def reconstruct_physical_timestamp(ts):
    """
    Synthetic Jan-Dec 2021 analysis axis -> physical Jun2020-May2021 calendar.
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


def calculate_stats(
    measured,
    simulated,
):
    """
    Generic paired statistics.
    """
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
        return {
            "n": 0,
            "mean_measured": np.nan,
            "mean_simulated": np.nan,
            "RMSE": np.nan,
            "CVRMSE_percent": np.nan,
            "MAE": np.nan,
            "nMAE_percent": np.nan,
            "MBE": np.nan,
            "nMBE_percent": np.nan,
            "RE_percent": np.nan,
            "R2": np.nan,
        }

    error = (
        s - m
    )

    mean_measured = float(
        np.mean(m)
    )

    mean_simulated = float(
        np.mean(s)
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

    nmbe = (
        float(
            np.sum(error)
            / np.sum(m)
            * 100.0
        )
        if np.sum(m) != 0
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
        "mean_simulated": mean_simulated,
        "RMSE": rmse,
        "CVRMSE_percent": cvrmse,
        "MAE": mae,
        "nMAE_percent": nmae,
        "MBE": mbe,
        "nMBE_percent": nmbe,
        "RE_percent": nmbe,
        "R2": r2,
    }


def cleaned_power_records(
    d,
    system,
):
    """
    Finalized annual power record selection.
    """
    x = d[
        d["system"] == system
    ].copy()

    x = x[
        pd.to_numeric(
            x["GTI_measured_Wm2"],
            errors="coerce",
        ) > 0
    ].copy()

    x = x[
        ~x["timestamp"].isin(
            POWER_EXCLUSIONS
        )
    ].copy()

    for col in (
        "P_measured_W",
        "P_IDA_W",
        "P_PVsyst_W",
    ):
        x[col] = pd.to_numeric(
            x[col],
            errors="coerce",
        )

    x = x.dropna(
        subset=[
            "P_measured_W",
            "P_IDA_W",
            "P_PVsyst_W",
        ]
    ).copy()

    x["physical_timestamp"] = (
        reconstruct_physical_timestamp(
            x["timestamp"]
        )
    )

    x["physical_day"] = (
        x["physical_timestamp"]
        .dt.normalize()
    )

    x["physical_month"] = (
        x["physical_timestamp"]
        .dt.to_period("M")
    )

    return x


# =============================================================================
# Aggregation
# =============================================================================

def hourly_dataset(x):
    """
    Hourly power comparison. Values remain W.
    """
    return pd.DataFrame({
        "period": x[
            "physical_timestamp"
        ],
        "Measured": x[
            "P_measured_W"
        ],
        "IDA ICE": x[
            "P_IDA_W"
        ],
        "PVsyst": x[
            "P_PVsyst_W"
        ],
    })


def daily_dataset(x):
    """
    Daily energy comparison. Hourly W values integrated as hourly Wh and
    converted to kWh.
    """
    g = (
        x.groupby(
            "physical_day",
            sort=True,
        )[
            [
                "P_measured_W",
                "P_IDA_W",
                "P_PVsyst_W",
            ]
        ]
        .sum()
        / 1000.0
    )

    return (
        g.reset_index()
        .rename(
            columns={
                "physical_day": "period",
                "P_measured_W": "Measured",
                "P_IDA_W": "IDA ICE",
                "P_PVsyst_W": "PVsyst",
            }
        )
    )


def monthly_dataset(x):
    """
    Monthly energy comparison. Same cleaned hourly records as the hourly and
    daily analyses; only the aggregation changes.
    """
    g = (
        x.groupby(
            "physical_month",
            sort=True,
        )[
            [
                "P_measured_W",
                "P_IDA_W",
                "P_PVsyst_W",
            ]
        ]
        .sum()
        / 1000.0
    )

    out = g.reset_index()

    out["period"] = (
        out[
            "physical_month"
        ].astype(str)
    )

    out = out.drop(
        columns=[
            "physical_month"
        ]
    )

    return out.rename(
        columns={
            "P_measured_W": "Measured",
            "P_IDA_W": "IDA ICE",
            "P_PVsyst_W": "PVsyst",
        }
    )


AGGREGATIONS = {
    "Hourly": {
        "builder": hourly_dataset,
        "quantity": "Power",
        "unit": "W",
        "rmse_per_kwp_unit": "W/kWp",
    },
    "Daily": {
        "builder": daily_dataset,
        "quantity": "Energy",
        "unit": "kWh/day",
        "rmse_per_kwp_unit": "kWh/kWp/day",
    },
    "Monthly": {
        "builder": monthly_dataset,
        "quantity": "Energy",
        "unit": "kWh/month",
        "rmse_per_kwp_unit": "kWh/kWp/month",
    },
}


# =============================================================================
# Main analysis
# =============================================================================

def run_method(
    method_name,
    d,
):
    metric_rows = []
    paired_rows = []
    annual_rows = []

    for system in (
        "A",
        "B",
        "C",
    ):
        x = cleaned_power_records(
            d,
            system,
        )

        kwp = float(
            x["kWp"].iloc[0]
        )

        # Annual energy is the same underlying cleaned hourly dataset for all
        # aggregation analyses.
        measured_annual_kwh = float(
            x[
                "P_measured_W"
            ].sum()
            / 1000.0
        )

        for software, col in (
            ("IDA ICE", "P_IDA_W"),
            ("PVsyst", "P_PVsyst_W"),
        ):
            sim_annual_kwh = float(
                x[col].sum()
                / 1000.0
            )

            diff_kwh = (
                sim_annual_kwh
                - measured_annual_kwh
            )

            diff_percent = (
                diff_kwh
                / measured_annual_kwh
                * 100.0
                if measured_annual_kwh != 0
                else np.nan
            )

            annual_rows.append({
                "Irradiance_method": method_name,
                "System": system,
                "Software": software,
                "kWp": kwp,
                "Measured_annual_energy_kWh": measured_annual_kwh,
                "Simulated_annual_energy_kWh": sim_annual_kwh,
                "Annual_energy_difference_kWh": diff_kwh,
                "Annual_energy_bias_percent": diff_percent,
            })

        for aggregation, cfg in AGGREGATIONS.items():
            agg = cfg[
                "builder"
            ](x)

            software_stats = {}

            for software in (
                "IDA ICE",
                "PVsyst",
            ):
                st = calculate_stats(
                    agg["Measured"],
                    agg[software],
                )

                software_stats[
                    software
                ] = st

                metric_rows.append({
                    "Irradiance_method": method_name,
                    "System": system,
                    "Aggregation": aggregation,
                    "Quantity": cfg[
                        "quantity"
                    ],
                    "Unit": cfg[
                        "unit"
                    ],
                    "Software": software,
                    "kWp": kwp,
                    **st,
                    "RMSE_per_kWp": (
                        st["RMSE"]
                        / kwp
                    ),
                    "RMSE_per_kWp_unit": cfg[
                        "rmse_per_kwp_unit"
                    ],
                })

            ida = software_stats[
                "IDA ICE"
            ]
            pvs = software_stats[
                "PVsyst"
            ]

            delta_rmse = (
                ida["RMSE"]
                - pvs["RMSE"]
            )

            delta_cvrmse = (
                ida[
                    "CVRMSE_percent"
                ]
                - pvs[
                    "CVRMSE_percent"
                ]
            )

            paired_rows.append({
                "Irradiance_method": method_name,
                "System": system,
                "Aggregation": aggregation,
                "Quantity": cfg[
                    "quantity"
                ],
                "Unit": cfg[
                    "unit"
                ],
                "n_periods": int(
                    ida["n"]
                ),
                "kWp": kwp,
                "RMSE_IDA": ida[
                    "RMSE"
                ],
                "RMSE_PVsyst": pvs[
                    "RMSE"
                ],
                "Delta_RMSE_IDA_minus_PVsyst": delta_rmse,
                "CVRMSE_IDA_percent": ida[
                    "CVRMSE_percent"
                ],
                "CVRMSE_PVsyst_percent": pvs[
                    "CVRMSE_percent"
                ],
                "Delta_CVRMSE_percentage_points": delta_cvrmse,
                "nMBE_IDA_percent": ida[
                    "nMBE_percent"
                ],
                "nMBE_PVsyst_percent": pvs[
                    "nMBE_percent"
                ],
                "Favored_by_RMSE": (
                    "IDA ICE"
                    if delta_rmse < 0
                    else (
                        "PVsyst"
                        if delta_rmse > 0
                        else "Tie"
                    )
                ),
                "Favored_by_CVRMSE": (
                    "IDA ICE"
                    if delta_cvrmse < 0
                    else (
                        "PVsyst"
                        if delta_cvrmse > 0
                        else "Tie"
                    )
                ),
            })

    return (
        pd.DataFrame(
            metric_rows
        ),
        pd.DataFrame(
            paired_rows
        ),
        pd.DataFrame(
            annual_rows
        ),
    )


def ranking_robustness(
    paired,
):
    rows = []

    for (
        method,
        system,
    ), g in paired.groupby(
        [
            "Irradiance_method",
            "System",
        ],
        sort=False,
    ):
        order = [
            "Hourly",
            "Daily",
            "Monthly",
        ]

        g = (
            g.set_index(
                "Aggregation"
            )
            .reindex(order)
            .reset_index()
        )

        favored = g[
            "Favored_by_RMSE"
        ].tolist()

        delta_cv = g[
            "Delta_CVRMSE_percentage_points"
        ].tolist()

        rows.append({
            "Irradiance_method": method,
            "System": system,
            "Hourly_favored_tool": favored[0],
            "Daily_favored_tool": favored[1],
            "Monthly_favored_tool": favored[2],
            "Favored_tool_same_hourly_daily_monthly": (
                len(
                    set(favored)
                ) == 1
            ),
            "Hourly_Delta_CVRMSE_pp": delta_cv[0],
            "Daily_Delta_CVRMSE_pp": delta_cv[1],
            "Monthly_Delta_CVRMSE_pp": delta_cv[2],
            "Delta_CVRMSE_sign_same_all_scales": (
                (
                    np.all(
                        np.asarray(
                            delta_cv
                        ) < 0
                    )
                )
                or (
                    np.all(
                        np.asarray(
                            delta_cv
                        ) > 0
                    )
                )
            ),
        })

    out = pd.DataFrame(
        rows
    )

    # Add cross-method context.
    wide = out.pivot(
        index="System",
        columns="Irradiance_method",
        values=[
            "Hourly_favored_tool",
            "Daily_favored_tool",
            "Monthly_favored_tool",
            "Favored_tool_same_hourly_daily_monthly",
        ],
    )

    wide.columns = [
        f"{field}_{method}"
        for field, method in wide.columns
    ]

    wide = wide.reset_index()

    return out, wide


# =============================================================================
# Excel output
# =============================================================================

def write_excel(
    metrics_df,
    paired_df,
    robustness_df,
    cross_method_df,
    annual_df,
):
    path = (
        OUT
        / "09_TEMPORAL_AGGREGATION_SENSITIVITY.xlsx"
    )

    with pd.ExcelWriter(
        path,
        engine="xlsxwriter",
    ) as writer:
        sheets = {
            "Metrics": metrics_df,
            "Paired_comparison": paired_df,
            "Aggregation_robustness": robustness_df,
            "Cross_method": cross_method_df,
            "Annual_energy": annual_df,
        }

        for name, df in sheets.items():
            df.to_excel(
                writer,
                sheet_name=name[:31],
                index=False,
            )

            ws = writer.sheets[
                name[:31]
            ]

            ws.freeze_panes(
                1,
                0,
            )

            for j, col in enumerate(
                df.columns
            ):
                values = [
                    len(str(v))
                    for v in df[col].head(200)
                    if pd.notna(v)
                ]

                width = max(
                    [len(str(col))]
                    + values
                )

                ws.set_column(
                    j,
                    j,
                    min(
                        max(
                            width + 2,
                            10,
                        ),
                        40,
                    ),
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
        "\nTEMPORAL AGGREGATION SENSITIVITY"
    )
    print("=" * 78)
    print(
        "Comparison scales: hourly power, daily energy, monthly energy."
    )
    print(
        "Same finalized daytime-cleaned power records are used at every scale."
    )
    print(
        "This analysis aggregates hourly results; it does not create "
        "sub-hourly simulations."
    )

    datasets = {
        "Perez-Driesse": load_canonical(
            PD_CANON
        ),
        "Engerer2": load_canonical(
            E2_CANON
        ),
    }

    metric_parts = []
    paired_parts = []
    annual_parts = []

    for method_name, d in datasets.items():
        print(
            f"\nRunning {method_name}..."
        )

        (
            m,
            p,
            a,
        ) = run_method(
            method_name,
            d,
        )

        metric_parts.append(
            m
        )
        paired_parts.append(
            p
        )
        annual_parts.append(
            a
        )

    metrics_df = pd.concat(
        metric_parts,
        ignore_index=True,
    )

    paired_df = pd.concat(
        paired_parts,
        ignore_index=True,
    )

    annual_df = pd.concat(
        annual_parts,
        ignore_index=True,
    )

    (
        robustness_df,
        cross_method_df,
    ) = ranking_robustness(
        paired_df
    )

    outputs = {
        "09_Temporal_aggregation_metrics.csv": metrics_df,
        "09_Paired_IDA_vs_PVsyst_by_aggregation.csv": paired_df,
        "09_Aggregation_ranking_robustness.csv": robustness_df,
        "09_Aggregation_cross_method_summary.csv": cross_method_df,
        "09_Annual_energy_summary.csv": annual_df,
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

    write_excel(
        metrics_df,
        paired_df,
        robustness_df,
        cross_method_df,
        annual_df,
    )

    print("\nPAIRED IDA ICE vs PVSYST BY TEMPORAL SCALE")
    print("-" * 78)

    show = paired_df[
        [
            "Irradiance_method",
            "System",
            "Aggregation",
            "n_periods",
            "CVRMSE_IDA_percent",
            "CVRMSE_PVsyst_percent",
            "Delta_CVRMSE_percentage_points",
            "nMBE_IDA_percent",
            "nMBE_PVsyst_percent",
            "Favored_by_RMSE",
        ]
    ]

    print(
        show.to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    print("\nRANKING ROBUSTNESS ACROSS HOURLY / DAILY / MONTHLY")
    print("-" * 78)

    print(
        robustness_df[
            [
                "Irradiance_method",
                "System",
                "Hourly_favored_tool",
                "Daily_favored_tool",
                "Monthly_favored_tool",
                "Favored_tool_same_hourly_daily_monthly",
            ]
        ].to_string(
            index=False
        )
    )

    print("\nANNUAL ENERGY BIAS")
    print("-" * 78)

    print(
        annual_df[
            [
                "Irradiance_method",
                "System",
                "Software",
                "Measured_annual_energy_kWh",
                "Simulated_annual_energy_kWh",
                "Annual_energy_bias_percent",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    print("\nDONE")
    print("=" * 78)
    print(
        "Use the aggregation analysis as a sensitivity test of whether "
        "hourly tool-performance differences persist when evaluated as "
        "daily and monthly energy."
    )


if __name__ == "__main__":
    main()
