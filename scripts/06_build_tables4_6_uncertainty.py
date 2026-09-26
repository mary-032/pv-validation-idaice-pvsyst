from pathlib import Path
import math

import numpy as np
import pandas as pd


# =====================================================================
# 06 - BUILD ARTICLE TABLES 4-6 WITH UNCERTAINTY / ROBUSTNESS
# =====================================================================
#
# Does NOT overwrite Table4_GTI_recomputed.csv, Table5_Temperature_recomputed.csv,
# or Table6_Power_recomputed.csv.
#
# Creates two article-style versions of each table:
#
#   * uncertainty_CI30d:
#       estimate [95% CI]
#       30-day circular moving-block bootstrap, 5,000 replicates
#
#   * robustness_pHolm30d:
#       point estimates + a dedicated paired RMSE comparison column
#       [p=...] = Holm-adjusted paired bootstrap p-value, 30-day blocks
#
# IMPORTANT:
# The paired p-value tests IDA ICE vs PVsyst RMSE for the same timestamps.
# It is NOT a p-value for nMBE, MBE, RE, etc., so it is kept in a separate
# comparison column rather than appended to unrelated metrics.
#
# For Table 6, monthly RMSE [kWh/kWp] remains a descriptive point estimate.
# The uncertainty/significance analysis is based on the hourly paired series.
# =====================================================================


ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "02_canonical_data"
OUT = ROOT / "03_analysis_output"

ANNUAL = CANON / "annual_unshaded_analysis.csv"

T4 = OUT / "Table4_GTI_recomputed.csv"
T5 = OUT / "Table5_Temperature_recomputed.csv"
T6 = OUT / "Table6_Power_recomputed.csv"

PAIRED = OUT / "05_Paired_IDA_vs_PVsyst_by_block.csv"

BLOCK_DAYS = 30
N_BOOT = 5000
SEED = 20260915

FALLBACK_EXCLUSIONS = pd.to_datetime([
    "2021-02-02 12:00:00",
    "2021-02-02 13:00:00",
    "2021-04-02 13:00:00",
    "2021-04-30 13:00:00",
])


VARIABLES = {
    "GTI": {
        "m": "GTI_measured_Wm2",
        "IDA ICE": "GTI_IDA_Wm2",
        "PVsyst": "GTI_PVsyst_Wm2",
    },
    "Temperature": {
        "m": "Tp_measured_C",
        "IDA ICE": "Tp_IDA_C",
        "PVsyst": "Tp_PVsyst_C",
    },
    "Power": {
        "m": "P_measured_W",
        "IDA ICE": "P_IDA_W",
        "PVsyst": "P_PVsyst_W",
    },
}


def physical_timestamp(ts):
    return pd.DatetimeIndex([
        t.replace(year=2021 if t.month <= 5 else 2020)
        for t in pd.DatetimeIndex(pd.to_datetime(ts))
    ])


def block_weights(n_days, block_days, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n_days / block_days)
    W = np.zeros((n_boot, n_days), dtype=np.uint16)
    offsets = np.arange(block_days)

    for b in range(n_boot):
        starts = rng.integers(0, n_days, size=n_blocks)
        idx = ((starts[:, None] + offsets[None, :]) % n_days).ravel()[:n_days]
        W[b] = np.bincount(idx, minlength=n_days)

    return W


def selected_rows(annual, system, variable, software):
    spec = VARIABLES[variable]

    d = annual[annual["system"] == system].copy()
    d = d[pd.to_numeric(d["GTI_measured_Wm2"], errors="coerce") > 0].copy()

    if variable == "Power":
        d = d[~d["timestamp"].isin(FALLBACK_EXCLUSIONS)].copy()

    for c in (spec["m"], spec[software]):
        d[c] = pd.to_numeric(d[c], errors="coerce")

    return d.dropna(subset=[spec["m"], spec[software]]).copy()


def daily_stats(d, mcol, scol, day_map, n_days):
    m = d[mcol].to_numpy(float)
    s = d[scol].to_numpy(float)
    e = s - m
    idx = d["physical_day"].map(day_map).to_numpy(int)

    out = {
        k: np.zeros(n_days, float)
        for k in ("n", "e", "e2", "m", "m2")
    }

    values = {
        "n": np.ones(len(d)),
        "e": e,
        "e2": e ** 2,
        "m": m,
        "m2": m ** 2,
    }

    for key, values_ in values.items():
        out[key] += np.bincount(
            idx,
            weights=values_,
            minlength=n_days,
        )

    return out


def metrics(st, W):
    n = W @ st["n"]
    se = W @ st["e"]
    se2 = W @ st["e2"]
    sm = W @ st["m"]

    with np.errstate(divide="ignore", invalid="ignore"):
        mean_m = sm / n
        rmse = np.sqrt(se2 / n)
        mbe = se / n
        cvrmse = 100.0 * rmse / mean_m
        nmbe = 100.0 * se / sm

    return {
        "RMSE": rmse,
        "MBE": mbe,
        "CVRMSE_percent": cvrmse,
        "nMBE_percent": nmbe,
        "RE_percent": nmbe,  # current pipeline convention
    }


def bootstrap_ci_table(annual):
    days = pd.DatetimeIndex(sorted(annual["physical_day"].unique()))
    day_map = {d: i for i, d in enumerate(days)}

    W = block_weights(
        len(days),
        BLOCK_DAYS,
        seed=SEED + 100 * BLOCK_DAYS,
    )

    rows = []

    for system in ("A", "B", "C"):
        for variable, spec in VARIABLES.items():
            for software in ("IDA ICE", "PVsyst"):
                d = selected_rows(
                    annual,
                    system,
                    variable,
                    software,
                )

                st = daily_stats(
                    d,
                    spec["m"],
                    spec[software],
                    day_map,
                    len(days),
                )

                point = metrics(
                    st,
                    np.ones((1, len(days))),
                )
                boot = metrics(st, W)

                for metric in point:
                    vals = np.asarray(boot[metric], float)
                    vals = vals[np.isfinite(vals)]
                    lo, hi = np.percentile(vals, [2.5, 97.5])

                    rows.append({
                        "System": system,
                        "Variable": variable,
                        "Software": software,
                        "Metric": metric,
                        "Estimate": float(point[metric][0]),
                        "CI95_low": float(lo),
                        "CI95_high": float(hi),
                    })

    return pd.DataFrame(rows)


def get_ci(ci, system, variable, software, metric):
    r = ci[
        (ci["System"] == system)
        & (ci["Variable"] == variable)
        & (ci["Software"] == software)
        & (ci["Metric"] == metric)
    ]

    if len(r) != 1:
        raise ValueError(
            f"Expected exactly one CI row for "
            f"{system}/{variable}/{software}/{metric}; got {len(r)}."
        )

    r = r.iloc[0]
    return (
        float(r["Estimate"]),
        float(r["CI95_low"]),
        float(r["CI95_high"]),
    )


def fmt_ci(values, decimals=2):
    est, lo, hi = values
    return (
        f"{est:.{decimals}f} "
        f"[{lo:.{decimals}f}, {hi:.{decimals}f}]"
    )


def fmt_num(x, decimals=2):
    return f"{float(x):.{decimals}f}"


def fmt_p(p):
    return f"[p={float(p):.3f}]"


def p_lookup(paired, system, variable):
    r = paired[
        (paired["block_days"] == BLOCK_DAYS)
        & (paired["System"] == system)
        & (paired["Variable"] == variable)
    ]

    if len(r) != 1:
        raise ValueError(
            f"Expected one 30-day paired row for {system}/{variable}; "
            f"got {len(r)}."
        )

    return float(r.iloc[0]["bootstrap_p_Holm"])


def main():
    required = [ANNUAL, T4, T5, T6, PAIRED]
    missing = [p for p in required if not p.exists()]

    if missing:
        raise FileNotFoundError(
            "Missing required outputs:\n"
            + "\n".join(f"  - {p.relative_to(ROOT)}" for p in missing)
            + "\nRun scripts 01, 02 and the final script 05 first."
        )

    annual = pd.read_csv(ANNUAL, parse_dates=["timestamp"])
    annual["timestamp"] = pd.to_datetime(annual["timestamp"]).dt.floor("s")
    annual["physical_timestamp"] = physical_timestamp(annual["timestamp"])
    annual["physical_day"] = annual["physical_timestamp"].dt.normalize()

    t4 = pd.read_csv(T4)
    t5 = pd.read_csv(T5)
    t6 = pd.read_csv(T6)
    paired = pd.read_csv(PAIRED)

    ci = bootstrap_ci_table(annual)

    # --------------------------------------------------------------
    # TABLE 4
    # --------------------------------------------------------------
    ci_rows = []
    p_rows = []

    for _, r in t4.iterrows():
        s, soft = r["System"], r["Software"]

        ci_rows.append({
            "System": s,
            "Software": soft,
            "nMBE [%]": fmt_ci(
                get_ci(ci, s, "GTI", soft, "nMBE_percent")
            ),
            "CV(RMSE) [%]": fmt_ci(
                get_ci(ci, s, "GTI", soft, "CVRMSE_percent")
            ),
            "RMSE [W/m²]": fmt_ci(
                get_ci(ci, s, "GTI", soft, "RMSE")
            ),
            "RE [%]": fmt_ci(
                get_ci(ci, s, "GTI", soft, "RE_percent")
            ),
        })

        p_rows.append({
            "System": s,
            "Software": soft,
            "nMBE [%]": fmt_num(r["nMBE_percent"]),
            "CV(RMSE) [%]": fmt_num(r["CVRMSE_percent"]),
            "RMSE [W/m²]": fmt_num(r["RMSE"]),
            "RE [%]": fmt_num(r["RE_percent"]),
            "Paired RMSE comparison": fmt_p(
                p_lookup(paired, s, "GTI")
            ),
        })

    pd.DataFrame(ci_rows).to_csv(
        OUT / "Table4_GTI_uncertainty_CI30d.csv",
        index=False,
    )
    pd.DataFrame(p_rows).to_csv(
        OUT / "Table4_GTI_robustness_pHolm30d.csv",
        index=False,
    )

    # --------------------------------------------------------------
    # TABLE 5
    # --------------------------------------------------------------
    ci_rows = []
    p_rows = []

    for _, r in t5.iterrows():
        s, soft = r["System"], r["Software"]

        ci_rows.append({
            "System": s,
            "Software": soft,
            "MBE [°C]": fmt_ci(
                get_ci(ci, s, "Temperature", soft, "MBE")
            ),
            "RMSE [°C]": fmt_ci(
                get_ci(ci, s, "Temperature", soft, "RMSE")
            ),
            "RE [%]": fmt_ci(
                get_ci(ci, s, "Temperature", soft, "RE_percent")
            ),
        })

        p_rows.append({
            "System": s,
            "Software": soft,
            "MBE [°C]": fmt_num(r["MBE"]),
            "RMSE [°C]": fmt_num(r["RMSE"]),
            "RE [%]": fmt_num(r["RE_percent"]),
            "Paired RMSE comparison": fmt_p(
                p_lookup(paired, s, "Temperature")
            ),
        })

    pd.DataFrame(ci_rows).to_csv(
        OUT / "Table5_Temperature_uncertainty_CI30d.csv",
        index=False,
    )
    pd.DataFrame(p_rows).to_csv(
        OUT / "Table5_Temperature_robustness_pHolm30d.csv",
        index=False,
    )

    # --------------------------------------------------------------
    # TABLE 6
    # --------------------------------------------------------------
    ci_rows = []
    p_rows = []

    for _, r in t6.iterrows():
        s, soft = r["System"], r["Software"]

        ci_rows.append({
            "System": s,
            "Software": soft,
            "nMBE [%]": fmt_ci(
                get_ci(ci, s, "Power", soft, "nMBE_percent")
            ),
            "CV(RMSE) [%]": fmt_ci(
                get_ci(ci, s, "Power", soft, "CVRMSE_percent")
            ),
            "Hourly RMSE [W]": fmt_ci(
                get_ci(ci, s, "Power", soft, "RMSE")
            ),
            "Monthly RMSE [kWh/kWp]": fmt_num(
                r["RMSE_month_kWh_per_kWp"]
            ),
            "RE [%]": fmt_ci(
                get_ci(ci, s, "Power", soft, "RE_percent")
            ),
        })

        p_rows.append({
            "System": s,
            "Software": soft,
            "nMBE [%]": fmt_num(r["nMBE_percent"]),
            "CV(RMSE) [%]": fmt_num(r["CVRMSE_percent"]),
            "Hourly RMSE [W]": fmt_num(r["RMSE"]),
            "Monthly RMSE [kWh/kWp]": fmt_num(
                r["RMSE_month_kWh_per_kWp"]
            ),
            "RE [%]": fmt_num(r["RE_percent"]),
            "Paired hourly-RMSE comparison": fmt_p(
                p_lookup(paired, s, "Power")
            ),
        })

    pd.DataFrame(ci_rows).to_csv(
        OUT / "Table6_Power_uncertainty_CI30d.csv",
        index=False,
    )
    pd.DataFrame(p_rows).to_csv(
        OUT / "Table6_Power_robustness_pHolm30d.csv",
        index=False,
    )

    print("\nCREATED ARTICLE TABLE VARIANTS")
    print("=" * 68)
    for name in (
        "Table4_GTI_uncertainty_CI30d.csv",
        "Table4_GTI_robustness_pHolm30d.csv",
        "Table5_Temperature_uncertainty_CI30d.csv",
        "Table5_Temperature_robustness_pHolm30d.csv",
        "Table6_Power_uncertainty_CI30d.csv",
        "Table6_Power_robustness_pHolm30d.csv",
    ):
        print(f"  {OUT / name}")

    print("\nNotes:")
    print(
        "  CI version: 30-day circular moving-block bootstrap, "
        "5,000 replicates, 95% percentile interval."
    )
    print(
        "  p version: Holm-adjusted paired bootstrap p-value for "
        "IDA ICE vs PVsyst hourly RMSE."
    )
    print(
        "  Table 6 monthly RMSE/kWp remains a descriptive point estimate; "
        "the inferential comparison is based on hourly RMSE."
    )
    print(
        "  Original Table4_GTI_recomputed.csv, Table5_Temperature_recomputed.csv "
        "and Table6_Power_recomputed.csv are untouched."
    )


if __name__ == "__main__":
    main()
