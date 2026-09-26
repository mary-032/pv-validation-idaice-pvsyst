from pathlib import Path
import math
import warnings

import numpy as np
import pandas as pd


# =============================================================================
# 08 - COMBINED MEASUREMENT + TEMPORAL UNCERTAINTY
# =============================================================================
#
# PURPOSE
# -------
# Quantify the effect of:
#
#   (1) temporal dependence / sampling uncertainty
#       -> 30-day circular moving-block bootstrap
#
#   (2) stated measurement uncertainty bounds
#       -> systematic series-level perturbation scenarios
#
# for both:
#
#   - Perez-Driesse baseline
#   - corrected Engerer2 sensitivity scenario
#
# IMPORTANT INTERPRETATION
# ------------------------
# The sensor specifications are treated as BOUNDS, not as probability
# distributions. Therefore this script does NOT invent a Normal or Uniform
# measurement-error distribution.
#
# Instead it evaluates three systematic measurement scenarios:
#
#   GTI:
#       LOW      = measured * 0.98
#       NOMINAL  = measured
#       HIGH     = measured * 1.02
#
#   AC power:
#       LOW      = measured * 0.99
#       NOMINAL  = measured
#       HIGH     = measured * 1.01
#
#   Panel temperature:
#       LOW      = measured - 0.5 °C
#       NOMINAL  = measured
#       HIGH     = measured + 0.5 °C
#
# The same perturbation is applied to the entire annual measured series in
# each scenario. This represents a calibration/systematic uncertainty bound,
# not independent hour-to-hour random noise.
#
# For each scenario, a 30-day moving-block bootstrap provides a 95% interval.
# The final "combined envelope" is:
#
#   low  = minimum of the three bootstrap lower bounds
#   high = maximum of the three bootstrap upper bounds
#
# This should be described in the manuscript as:
#
#   "a 95% moving-block bootstrap interval enveloped over the stated
#    measurement uncertainty bounds"
#
# rather than as a purely probabilistic combined 95% confidence interval.
#
# RECORD-SELECTION RULES
# ----------------------
# Identical to the finalized analysis:
#
#   * daytime selection is based on NOMINAL measured GTI > 0
#   * GTI: no outlier removal
#   * temperature: no outlier removal
#   * power: remove exactly the four agreed gross-error timestamps
#   * same physical chronology for bootstrap blocks
#   * error = simulated - measured
#
# The measurement perturbation does NOT change which timestamps are included.
#
# INPUTS
# ------
# 02_canonical_data/annual_unshaded_analysis.csv
# 02a_canonical_data_Engerer2/annual_unshaded_analysis_Engerer2.csv
#
# OUTPUTS
# -------
# 03_analysis_output/uncertainty/
#
#   08_Measurement_scenario_metrics.csv
#   08_Combined_metric_envelope.csv
#   08_Paired_comparison_by_measurement_scenario.csv
#   08_Paired_comparison_combined_envelope.csv
#   08_Combined_uncertainty_summary.csv
#   08_COMBINED_MEASUREMENT_TEMPORAL_UNCERTAINTY.xlsx
#
# =============================================================================


ROOT = Path(__file__).resolve().parents[1]

PD_CANON = (
    ROOT
    / "02_canonical_data"
    / "annual_unshaded_analysis.csv"
)

E2_CANON = (
    ROOT
    / "02a_canonical_data_Engerer2"
    / "annual_unshaded_analysis_Engerer2.csv"
)

OUT = (
    ROOT
    / "03_analysis_output"
    / "uncertainty"
)
OUT.mkdir(
    parents=True,
    exist_ok=True,
)

N_BOOT = 5000
BLOCK_DAYS = 30
SEED = 20260916

CI_LOW = 2.5
CI_HIGH = 97.5

POWER_EXCLUSIONS = pd.to_datetime([
    "2021-02-02 12:00:00",
    "2021-02-02 13:00:00",
    "2021-04-02 13:00:00",
    "2021-04-30 13:00:00",
])

VARIABLES = {
    "GTI": {
        "measured": "GTI_measured_Wm2",
        "IDA ICE": "GTI_IDA_Wm2",
        "PVsyst": "GTI_PVsyst_Wm2",
        "unit": "W/m²",
        "uncertainty_type": "relative",
        "uncertainty_bound": 0.02,
        "uncertainty_text": "±2%",
    },
    "Temperature": {
        "measured": "Tp_measured_C",
        "IDA ICE": "Tp_IDA_C",
        "PVsyst": "Tp_PVsyst_C",
        "unit": "°C",
        "uncertainty_type": "absolute",
        "uncertainty_bound": 0.5,
        "uncertainty_text": "±0.5 °C",
    },
    "Power": {
        "measured": "P_measured_W",
        "IDA ICE": "P_IDA_W",
        "PVsyst": "P_PVsyst_W",
        "unit": "W",
        "uncertainty_type": "relative",
        "uncertainty_bound": 0.01,
        "uncertainty_text": "±1%",
    },
}

SCENARIOS = (
    "LOW",
    "NOMINAL",
    "HIGH",
)


# =============================================================================
# Input / chronology helpers
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


def add_physical_days(d):
    out = d.copy()

    out["physical_timestamp"] = (
        reconstruct_physical_timestamp(
            out["timestamp"]
        )
    )

    out["physical_day"] = (
        out[
            "physical_timestamp"
        ].dt.normalize()
    )

    return out


# =============================================================================
# Measurement scenarios
# =============================================================================

def perturb_measured(series, variable, scenario):
    """
    Apply a single systematic measurement perturbation to the full series.
    """
    x = pd.to_numeric(
        series,
        errors="coerce",
    ).astype(float)

    spec = VARIABLES[
        variable
    ]

    if scenario == "NOMINAL":
        return x

    sign = (
        -1.0
        if scenario == "LOW"
        else 1.0
    )

    bound = float(
        spec["uncertainty_bound"]
    )

    if (
        spec["uncertainty_type"]
        == "relative"
    ):
        factor = (
            1.0
            + sign * bound
        )
        return x * factor

    if (
        spec["uncertainty_type"]
        == "absolute"
    ):
        return x + sign * bound

    raise ValueError(
        f"Unknown uncertainty type for {variable}"
    )


def selected_rows(
    d,
    system,
    variable,
):
    """
    Timestamp selection is based on NOMINAL data only and is therefore held
    fixed across measurement scenarios.
    """
    spec = VARIABLES[
        variable
    ]

    x = d[
        d["system"] == system
    ].copy()

    # Final daytime rule.
    x = x[
        pd.to_numeric(
            x["GTI_measured_Wm2"],
            errors="coerce",
        ) > 0
    ].copy()

    # Final power gross-error exclusions.
    if variable == "Power":
        x = x[
            ~x["timestamp"].isin(
                POWER_EXCLUSIONS
            )
        ].copy()

    needed = [
        spec["measured"],
        spec["IDA ICE"],
        spec["PVsyst"],
    ]

    for c in needed:
        x[c] = pd.to_numeric(
            x[c],
            errors="coerce",
        )

    x = x.dropna(
        subset=needed
    ).copy()

    return x


# =============================================================================
# Bootstrap engine
# =============================================================================

def build_day_index(d):
    days = pd.DatetimeIndex(
        sorted(
            d["physical_day"]
            .dropna()
            .unique()
        )
    )

    day_map = {
        day: i
        for i, day in enumerate(days)
    }

    return days, day_map


def circular_block_weights(
    n_days,
    block_days=BLOCK_DAYS,
    n_boot=N_BOOT,
    seed=SEED,
):
    """
    Circular moving-block bootstrap weights over physical days.
    """
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

        idx = idx.ravel()[
            :n_days
        ]

        weights[b] = np.bincount(
            idx,
            minlength=n_days,
        ).astype(
            np.uint16
        )

    return weights


def daily_stats(
    x,
    measured_values,
    simulated_col,
    day_map,
    n_days,
):
    """
    Aggregate sufficient statistics by physical day.
    """
    m = np.asarray(
        measured_values,
        dtype=float,
    )

    s = x[
        simulated_col
    ].to_numpy(
        dtype=float
    )

    e = s - m

    idx = (
        x["physical_day"]
        .map(day_map)
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
            len(x),
            dtype=float,
        ),
        "sum_e": e,
        "sum_e2": e ** 2,
        "sum_abs_e": np.abs(e),
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


def bootstrap_metrics(stats, W):
    n = W @ stats["n"]
    se = W @ stats["sum_e"]
    se2 = W @ stats["sum_e2"]
    sae = W @ stats["sum_abs_e"]
    sm = W @ stats["sum_m"]
    sm2 = W @ stats["sum_m2"]

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
            - sm ** 2 / n
        )

        r2 = (
            1.0
            - se2 / sst
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


# =============================================================================
# Single-software metric uncertainty
# =============================================================================

def scenario_metric_analysis(
    method_name,
    d,
    W,
    days,
    day_map,
):
    rows = []

    for system in (
        "A",
        "B",
        "C",
    ):
        for variable, spec in VARIABLES.items():
            x = selected_rows(
                d,
                system,
                variable,
            )

            for scenario in SCENARIOS:
                measured = perturb_measured(
                    x[
                        spec["measured"]
                    ],
                    variable,
                    scenario,
                ).to_numpy(
                    dtype=float
                )

                for software in (
                    "IDA ICE",
                    "PVsyst",
                ):
                    st = daily_stats(
                        x,
                        measured,
                        spec[software],
                        day_map,
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
                            "Irradiance_method": method_name,
                            "System": system,
                            "Variable": variable,
                            "Software": software,
                            "Measurement_scenario": scenario,
                            "Measurement_uncertainty": spec[
                                "uncertainty_text"
                            ],
                            "Metric": metric,
                            "Estimate": float(
                                point[
                                    metric
                                ][0]
                            ),
                            "Bootstrap95_low": lo,
                            "Bootstrap95_high": hi,
                            "block_days": BLOCK_DAYS,
                            "n_boot": N_BOOT,
                            "n_records": int(
                                round(
                                    point[
                                        "n"
                                    ][0]
                                )
                            ),
                        })

    return pd.DataFrame(
        rows
    )


def combined_metric_envelope(
    scenario_df,
):
    rows = []

    group_cols = [
        "Irradiance_method",
        "System",
        "Variable",
        "Software",
        "Metric",
    ]

    for keys, g in scenario_df.groupby(
        group_cols,
        sort=False,
    ):
        (
            method,
            system,
            variable,
            software,
            metric,
        ) = keys

        nominal = g[
            g[
                "Measurement_scenario"
            ] == "NOMINAL"
        ]

        if len(nominal) != 1:
            raise ValueError(
                "Expected exactly one NOMINAL row "
                f"for {keys}, found {len(nominal)}."
            )

        nominal = nominal.iloc[0]

        rows.append({
            "Irradiance_method": method,
            "System": system,
            "Variable": variable,
            "Software": software,
            "Metric": metric,
            "Measurement_uncertainty": nominal[
                "Measurement_uncertainty"
            ],
            "Nominal_estimate": nominal[
                "Estimate"
            ],
            "Nominal_bootstrap95_low": nominal[
                "Bootstrap95_low"
            ],
            "Nominal_bootstrap95_high": nominal[
                "Bootstrap95_high"
            ],
            "Sensor_scenario_min_estimate": float(
                g[
                    "Estimate"
                ].min()
            ),
            "Sensor_scenario_max_estimate": float(
                g[
                    "Estimate"
                ].max()
            ),
            "Combined_envelope_low": float(
                g[
                    "Bootstrap95_low"
                ].min()
            ),
            "Combined_envelope_high": float(
                g[
                    "Bootstrap95_high"
                ].max()
            ),
            "Combined_interval_definition": (
                "min/max of 30-day bootstrap 95% bounds "
                "across LOW/NOMINAL/HIGH measurement scenarios"
            ),
            "block_days": BLOCK_DAYS,
            "n_boot": N_BOOT,
        })

    return pd.DataFrame(
        rows
    )


# =============================================================================
# Paired IDA ICE vs PVsyst uncertainty
# =============================================================================

def paired_daily_stats(
    x,
    measured_values,
    spec,
    day_map,
    n_days,
):
    m = np.asarray(
        measured_values,
        dtype=float,
    )

    ida = x[
        spec["IDA ICE"]
    ].to_numpy(
        dtype=float
    )

    pvs = x[
        spec["PVsyst"]
    ].to_numpy(
        dtype=float
    )

    ei = ida - m
    ep = pvs - m

    idx = (
        x["physical_day"]
        .map(day_map)
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
            len(x),
            dtype=float,
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
    sm = W @ stats["sum_m"]
    ie2 = W @ stats["ida_e2"]
    pe2 = W @ stats["pvs_e2"]

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):
        rmse_ida = np.sqrt(
            ie2 / n
        )
        rmse_pvs = np.sqrt(
            pe2 / n
        )
        mean_m = sm / n

        delta_rmse = (
            rmse_ida
            - rmse_pvs
        )

        delta_cvrmse = (
            100.0
            * delta_rmse
            / mean_m
        )

    return {
        "n": n,
        "RMSE_IDA": rmse_ida,
        "RMSE_PVsyst": rmse_pvs,
        "Delta_RMSE": delta_rmse,
        "Delta_CVRMSE_pp": delta_cvrmse,
    }


def bootstrap_p(
    boot_values,
    observed,
):
    """
    Two-sided centered bootstrap p-value, matching script 05/07 convention.
    """
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

    centered = (
        b - observed
    )

    extreme = np.sum(
        np.abs(centered)
        >= abs(observed)
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


def paired_scenario_analysis(
    method_name,
    d,
    W,
    days,
    day_map,
):
    rows = []

    for scenario in SCENARIOS:
        scenario_rows = []

        for system in (
            "A",
            "B",
            "C",
        ):
            for variable, spec in VARIABLES.items():
                x = selected_rows(
                    d,
                    system,
                    variable,
                )

                measured = perturb_measured(
                    x[
                        spec["measured"]
                    ],
                    variable,
                    scenario,
                ).to_numpy(
                    dtype=float
                )

                st = paired_daily_stats(
                    x,
                    measured,
                    spec,
                    day_map,
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
                    point[
                        "Delta_RMSE"
                    ][0]
                )

                lo, hi = percentile_ci(
                    boot[
                        "Delta_RMSE"
                    ]
                )

                cv_lo, cv_hi = percentile_ci(
                    boot[
                        "Delta_CVRMSE_pp"
                    ]
                )

                scenario_rows.append({
                    "Irradiance_method": method_name,
                    "System": system,
                    "Variable": variable,
                    "Measurement_scenario": scenario,
                    "Measurement_uncertainty": spec[
                        "uncertainty_text"
                    ],
                    "n_common": int(
                        round(
                            point[
                                "n"
                            ][0]
                        )
                    ),
                    "RMSE_IDA": float(
                        point[
                            "RMSE_IDA"
                        ][0]
                    ),
                    "RMSE_PVsyst": float(
                        point[
                            "RMSE_PVsyst"
                        ][0]
                    ),
                    "Delta_RMSE_IDA_minus_PVsyst": observed,
                    "Delta_RMSE_bootstrap95_low": lo,
                    "Delta_RMSE_bootstrap95_high": hi,
                    "Delta_CVRMSE_percentage_points": float(
                        point[
                            "Delta_CVRMSE_pp"
                        ][0]
                    ),
                    "Delta_CVRMSE_bootstrap95_low": cv_lo,
                    "Delta_CVRMSE_bootstrap95_high": cv_hi,
                    "bootstrap_p_raw": bootstrap_p(
                        boot[
                            "Delta_RMSE"
                        ],
                        observed,
                    ),
                    "block_days": BLOCK_DAYS,
                    "n_boot": N_BOOT,
                })

        scenario_df = pd.DataFrame(
            scenario_rows
        )

        scenario_df[
            "bootstrap_p_Holm"
        ] = holm_adjust(
            scenario_df[
                "bootstrap_p_raw"
            ].to_numpy()
        )

        scenario_df[
            "significant_Holm_0.05"
        ] = (
            scenario_df[
                "bootstrap_p_Holm"
            ] < 0.05
        )

        scenario_df[
            "Favored_by_RMSE"
        ] = np.where(
            scenario_df[
                "Delta_RMSE_IDA_minus_PVsyst"
            ] < 0,
            "IDA ICE",
            np.where(
                scenario_df[
                    "Delta_RMSE_IDA_minus_PVsyst"
                ] > 0,
                "PVsyst",
                "Tie",
            ),
        )

        rows.append(
            scenario_df
        )

    return pd.concat(
        rows,
        ignore_index=True,
    )


def paired_combined_envelope(
    paired_df,
):
    rows = []

    group_cols = [
        "Irradiance_method",
        "System",
        "Variable",
    ]

    for keys, g in paired_df.groupby(
        group_cols,
        sort=False,
    ):
        (
            method,
            system,
            variable,
        ) = keys

        nominal = g[
            g[
                "Measurement_scenario"
            ] == "NOMINAL"
        ]

        if len(nominal) != 1:
            raise ValueError(
                f"Expected one NOMINAL paired row for {keys}."
            )

        nominal = nominal.iloc[0]

        delta_min = float(
            g[
                "Delta_RMSE_IDA_minus_PVsyst"
            ].min()
        )

        delta_max = float(
            g[
                "Delta_RMSE_IDA_minus_PVsyst"
            ].max()
        )

        envelope_low = float(
            g[
                "Delta_RMSE_bootstrap95_low"
            ].min()
        )

        envelope_high = float(
            g[
                "Delta_RMSE_bootstrap95_high"
            ].max()
        )

        favored = set(
            g[
                "Favored_by_RMSE"
            ].tolist()
        )

        significant = g[
            "significant_Holm_0.05"
        ].astype(bool)

        direction_robust = (
            delta_max < 0
            or delta_min > 0
        )

        combined_excludes_zero = (
            envelope_low > 0
            or envelope_high < 0
        )

        rows.append({
            "Irradiance_method": method,
            "System": system,
            "Variable": variable,
            "Measurement_uncertainty": nominal[
                "Measurement_uncertainty"
            ],
            "Nominal_Delta_RMSE": nominal[
                "Delta_RMSE_IDA_minus_PVsyst"
            ],
            "Nominal_bootstrap95_low": nominal[
                "Delta_RMSE_bootstrap95_low"
            ],
            "Nominal_bootstrap95_high": nominal[
                "Delta_RMSE_bootstrap95_high"
            ],
            "Nominal_p_Holm": nominal[
                "bootstrap_p_Holm"
            ],
            "Nominal_favored_tool": nominal[
                "Favored_by_RMSE"
            ],
            "Sensor_scenario_Delta_RMSE_min": delta_min,
            "Sensor_scenario_Delta_RMSE_max": delta_max,
            "Combined_envelope_low": envelope_low,
            "Combined_envelope_high": envelope_high,
            "Favored_tool_same_all_sensor_scenarios": (
                len(favored) == 1
            ),
            "Favored_tool_across_sensor_scenarios": (
                " | ".join(
                    sorted(favored)
                )
            ),
            "Delta_direction_robust_to_sensor_bounds": (
                direction_robust
            ),
            "Combined_envelope_excludes_zero": (
                combined_excludes_zero
            ),
            "Significant_Holm_all_sensor_scenarios": bool(
                significant.all()
            ),
            "Significant_Holm_any_sensor_scenario": bool(
                significant.any()
            ),
            "Combined_interval_definition": (
                "min/max of 30-day paired-bootstrap 95% bounds "
                "across LOW/NOMINAL/HIGH measurement scenarios"
            ),
            "block_days": BLOCK_DAYS,
            "n_boot": N_BOOT,
        })

    return pd.DataFrame(
        rows
    )


# =============================================================================
# Cross-method summary
# =============================================================================

def build_cross_method_summary(
    paired_envelope,
):
    """
    One compact table for manuscript/reviewer interpretation.
    """
    p = paired_envelope.copy()

    keep = [
        "Irradiance_method",
        "System",
        "Variable",
        "Nominal_Delta_RMSE",
        "Combined_envelope_low",
        "Combined_envelope_high",
        "Nominal_favored_tool",
        "Delta_direction_robust_to_sensor_bounds",
        "Combined_envelope_excludes_zero",
        "Significant_Holm_all_sensor_scenarios",
    ]

    p = p[
        keep
    ]

    wide = p.pivot(
        index=[
            "System",
            "Variable",
        ],
        columns="Irradiance_method",
    )

    wide.columns = [
        f"{field}_{method}"
        for field, method in wide.columns
    ]

    wide = wide.reset_index()

    pd_fav = (
        wide[
            "Nominal_favored_tool_Perez-Driesse"
        ]
        if (
            "Nominal_favored_tool_Perez-Driesse"
            in wide.columns
        )
        else pd.Series(
            np.nan,
            index=wide.index,
        )
    )

    e2_fav = (
        wide[
            "Nominal_favored_tool_Engerer2"
        ]
        if (
            "Nominal_favored_tool_Engerer2"
            in wide.columns
        )
        else pd.Series(
            np.nan,
            index=wide.index,
        )
    )

    wide[
        "Favored_tool_same_PD_vs_E2"
    ] = (
        pd_fav == e2_fav
    )

    pd_sensor_robust = (
        wide[
            "Delta_direction_robust_to_sensor_bounds_Perez-Driesse"
        ].astype(bool)
    )

    e2_sensor_robust = (
        wide[
            "Delta_direction_robust_to_sensor_bounds_Engerer2"
        ].astype(bool)
    )

    wide[
        "Direction_robust_to_sensor_bounds_in_both_methods"
    ] = (
        pd_sensor_robust
        & e2_sensor_robust
    )

    return wide


# =============================================================================
# Excel output
# =============================================================================

def write_excel(
    scenario_metrics,
    combined_metrics,
    paired_scenarios,
    paired_envelope,
    summary,
):
    path = (
        OUT
        / "08_COMBINED_MEASUREMENT_TEMPORAL_UNCERTAINTY.xlsx"
    )

    try:
        with pd.ExcelWriter(
            path,
            engine="xlsxwriter",
        ) as writer:
            sheets = {
                "Scenario_metrics": scenario_metrics,
                "Combined_metrics": combined_metrics,
                "Paired_scenarios": paired_scenarios,
                "Paired_envelope": paired_envelope,
                "Cross_method_summary": summary,
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
                            max(width + 2, 10),
                            42,
                        ),
                    )

        print(
            f"Wrote {path.relative_to(ROOT)}"
        )

    except Exception as exc:
        warnings.warn(
            f"Could not create Excel workbook: {exc}"
        )


# =============================================================================
# Main
# =============================================================================

def main():
    require_inputs()

    print(
        "\nCOMBINED MEASUREMENT + TEMPORAL UNCERTAINTY"
    )
    print("=" * 78)
    print(
        f"30-day circular moving-block bootstrap, "
        f"{N_BOOT:,} replicates."
    )
    print(
        "Measurement bounds are treated as systematic LOW/NOMINAL/HIGH "
        "scenarios, not as invented probability distributions."
    )
    print(
        "GTI ±2%; AC power ±1%; panel temperature ±0.5 °C."
    )

    datasets = {
        "Perez-Driesse": add_physical_days(
            load_canonical(
                PD_CANON
            )
        ),
        "Engerer2": add_physical_days(
            load_canonical(
                E2_CANON
            )
        ),
    }

    # Both canonical datasets share the same physical chronology.
    days, day_map = build_day_index(
        datasets[
            "Perez-Driesse"
        ]
    )

    W = circular_block_weights(
        len(days),
        block_days=BLOCK_DAYS,
        n_boot=N_BOOT,
        seed=SEED,
    )

    scenario_metric_parts = []
    paired_parts = []

    for method_name, d in datasets.items():
        print(
            f"\nRunning {method_name}..."
        )

        scenario_metric_parts.append(
            scenario_metric_analysis(
                method_name,
                d,
                W,
                days,
                day_map,
            )
        )

        paired_parts.append(
            paired_scenario_analysis(
                method_name,
                d,
                W,
                days,
                day_map,
            )
        )

    scenario_metrics = pd.concat(
        scenario_metric_parts,
        ignore_index=True,
    )

    combined_metrics = (
        combined_metric_envelope(
            scenario_metrics
        )
    )

    paired_scenarios = pd.concat(
        paired_parts,
        ignore_index=True,
    )

    paired_envelope = (
        paired_combined_envelope(
            paired_scenarios
        )
    )

    summary = (
        build_cross_method_summary(
            paired_envelope
        )
    )

    outputs = {
        "08_Measurement_scenario_metrics.csv": scenario_metrics,
        "08_Combined_metric_envelope.csv": combined_metrics,
        "08_Paired_comparison_by_measurement_scenario.csv": paired_scenarios,
        "08_Paired_comparison_combined_envelope.csv": paired_envelope,
        "08_Combined_uncertainty_summary.csv": summary,
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
        scenario_metrics,
        combined_metrics,
        paired_scenarios,
        paired_envelope,
        summary,
    )

    print("\nPAIRED COMPARISON: COMBINED SENSOR + TEMPORAL ENVELOPE")
    print("-" * 78)

    show = paired_envelope[
        [
            "Irradiance_method",
            "System",
            "Variable",
            "Nominal_Delta_RMSE",
            "Combined_envelope_low",
            "Combined_envelope_high",
            "Nominal_favored_tool",
            "Favored_tool_same_all_sensor_scenarios",
            "Combined_envelope_excludes_zero",
            "Significant_Holm_all_sensor_scenarios",
        ]
    ].copy()

    print(
        show.to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    print("\nCROSS-METHOD ROBUSTNESS")
    print("-" * 78)

    cross_cols = [
        c
        for c in (
            "System",
            "Variable",
            "Nominal_favored_tool_Perez-Driesse",
            "Nominal_favored_tool_Engerer2",
            "Favored_tool_same_PD_vs_E2",
            "Direction_robust_to_sensor_bounds_in_both_methods",
        )
        if c in summary.columns
    ]

    print(
        summary[
            cross_cols
        ].to_string(
            index=False
        )
    )

    print("\nDONE")
    print("=" * 78)
    print(
        "Interpret the combined bounds as a bootstrap interval enveloped "
        "over stated sensor uncertainty limits, not as a fully probabilistic "
        "joint 95% confidence interval."
    )


if __name__ == "__main__":
    main()
