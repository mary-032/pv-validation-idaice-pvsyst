from pathlib import Path
import json, math, warnings
import numpy as np
import pandas as pd

# ============================================================
# 05 - Statistical uncertainty and direct model comparison
# ============================================================
# CURRENT Perez-Driesse analysis only.
#
# Implements:
#   * daily residual autocorrelation diagnostics
#   * circular moving-block bootstrap (annual primary: 30 days, shading: 7 days, 5000 reps)
#   * 95% CIs for annual metrics and annual energy bias
#   * paired IDA ICE vs PVsyst bootstrap comparison + Holm correction
#   * paired-comparison sensitivity for 1/7/14/21/30-day blocks
#   * ACF of the daily paired squared-error loss difference
#   * 1/7/14/21/30-day block-length sensitivity
#   * sensitivity to the four agreed power exclusions
#   * weather-bin CIs for Figure 3
#   * full-period shading CIs
#
# IMPORTANT:
#   Bootstrap resampling follows the REAL study chronology
#   Jun 2020 -> May 2021, reconstructed from the synthetic analysis clock.
#   Sensor/calibration uncertainty is intentionally kept separate.
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "derived_data"
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)

ANNUAL_PATH = CANON / "annual_unshaded_analysis.csv"
SHADING_PATH = CANON / "shading_analysis.csv"
CONFIG_PATH = ROOT / "config.json"

N_BOOT = 5000
ANNUAL_PRIMARY_BLOCK_DAYS = 30
SHADING_BLOCK_DAYS = 7
SENSITIVITY_BLOCK_DAYS = [1, 7, 14, 21, 30]
SEED = 20260915
ACF_MAX_LAG = 30

SYSTEMS = ["A", "B", "C"]
SOFTWARE = ["IDA ICE", "PVsyst"]
VARIABLES = {
    "GTI": {
        "m": "GTI_measured_Wm2",
        "IDA ICE": "GTI_IDA_Wm2",
        "PVsyst": "GTI_PVsyst_Wm2",
        "unit": "W/m²",
    },
    "Temperature": {
        "m": "Tp_measured_C",
        "IDA ICE": "Tp_IDA_C",
        "PVsyst": "Tp_PVsyst_C",
        "unit": "°C",
    },
    "Power": {
        "m": "P_measured_W",
        "IDA ICE": "P_IDA_W",
        "PVsyst": "P_PVsyst_W",
        "unit": "W",
    },
}
SKY_BINS = [
    ("Overcast/very cloudy", 0.0, 0.2),
    ("Cloudy", 0.2, 0.4),
    ("Mixed/broken", 0.4, 0.6),
    ("Mostly clear", 0.6, 0.75),
    ("Clear", 0.75, None),
]


def load_cfg():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}


CFG = load_cfg()
FALLBACK_EXCLUSIONS = [
    "2021-02-02 12:00:00",
    "2021-02-02 13:00:00",
    "2021-04-02 13:00:00",
    "2021-04-30 13:00:00",
]
POWER_EXCLUSIONS = pd.DatetimeIndex(pd.to_datetime(
    CFG.get("annual", {}).get("power_excluded_timestamps", FALLBACK_EXCLUSIONS)
)).floor("s")


def physical_timestamp(ts):
    """Synthetic Jan-Dec 2021 clock -> real Jun 2020-May 2021 date."""
    out = []
    for t in pd.DatetimeIndex(pd.to_datetime(ts)):
        out.append(t.replace(year=2021 if t.month <= 5 else 2020))
    return pd.DatetimeIndex(out)


def load_data():
    if not ANNUAL_PATH.exists() or not SHADING_PATH.exists():
        raise FileNotFoundError("Canonical annual/shading data missing from derived_data/. Run script 01 first.")

    a = pd.read_csv(ANNUAL_PATH, parse_dates=["timestamp"])
    a["timestamp"] = pd.to_datetime(a["timestamp"]).dt.floor("s")
    a["physical_timestamp"] = physical_timestamp(a["timestamp"])
    a["physical_day"] = a["physical_timestamp"].dt.normalize()

    s = pd.read_csv(SHADING_PATH, parse_dates=["timestamp"])
    s["timestamp"] = pd.to_datetime(s["timestamp"]).dt.floor("s")
    s["physical_day"] = s["timestamp"].dt.normalize()
    return a, s


def day_axis(days):
    unique = pd.DatetimeIndex(sorted(pd.DatetimeIndex(days).normalize().unique()))
    return unique, {d: i for i, d in enumerate(unique)}


def block_weights(n_days, block_days, n_boot=N_BOOT, seed=SEED):
    """Circular moving-block bootstrap; each replicate contains n_days sampled days."""
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n_days / block_days)
    W = np.zeros((n_boot, n_days), dtype=np.uint16)
    offsets = np.arange(block_days)
    for b in range(n_boot):
        starts = rng.integers(0, n_days, size=n_blocks)
        idx = ((starts[:, None] + offsets[None, :]) % n_days).ravel()[:n_days]
        W[b] = np.bincount(idx, minlength=n_days)
    return W


def selected_rows(annual, system, variable, software=None, both=False, remove_exclusions=True):
    spec = VARIABLES[variable]
    d = annual[annual["system"] == system].copy()
    d = d[pd.to_numeric(d["GTI_measured_Wm2"], errors="coerce") > 0].copy()
    if variable == "Power" and remove_exclusions:
        d = d[~d["timestamp"].isin(POWER_EXCLUSIONS)].copy()

    needed = [spec["m"]]
    if both:
        needed += [spec["IDA ICE"], spec["PVsyst"]]
    else:
        needed += [spec[software]]
    for c in needed:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.dropna(subset=needed).copy()


def daily_stats(d, mcol, scol, day_map, n_days):
    m = d[mcol].to_numpy(float)
    s = d[scol].to_numpy(float)
    e = s - m
    idx = d["physical_day"].map(day_map).to_numpy(int)
    out = {k: np.zeros(n_days, float) for k in
           ["n", "e", "e2", "ae", "m", "m2", "s"]}
    vals = {
        "n": np.ones(len(d)), "e": e, "e2": e**2, "ae": np.abs(e),
        "m": m, "m2": m**2, "s": s,
    }
    for k, v in vals.items():
        out[k] += np.bincount(idx, weights=v, minlength=n_days)
    return out


def metrics_from_weights(st, W):
    n = W @ st["n"]
    se = W @ st["e"]
    se2 = W @ st["e2"]
    sae = W @ st["ae"]
    sm = W @ st["m"]
    sm2 = W @ st["m2"]
    ss = W @ st["s"]
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_m = sm / n
        rmse = np.sqrt(se2 / n)
        mae = sae / n
        mbe = se / n
        cvrmse = 100 * rmse / mean_m
        nmae = 100 * mae / mean_m
        nmbe = 100 * se / sm
        sst = sm2 - sm**2 / n
        r2 = 1 - se2 / sst
    r2 = np.where(sst > 0, r2, np.nan)
    return {
        "n": n, "RMSE": rmse, "CVRMSE_percent": cvrmse,
        "MAE": mae, "nMAE_percent": nmae, "MBE": mbe,
        "nMBE_percent": nmbe, "RE_percent": nmbe, "R2": r2,
        "sum_measured": sm, "sum_simulated": ss,
    }


def point_metrics(st):
    r = metrics_from_weights(st, np.ones((1, len(st["n"]))))
    return {k: float(v[0]) for k, v in r.items()}


def ci(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return tuple(np.percentile(x, [2.5, 97.5])) if len(x) else (np.nan, np.nan)


# ---------- ACF diagnostics ----------

def acf_pair(x, lag):
    x = np.asarray(x, float)
    a, b = x[:-lag], x[lag:]
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    if len(a) < 10 or np.std(a) == 0 or np.std(b) == 0:
        return np.nan, len(a)
    return float(np.corrcoef(a, b)[0, 1]), len(a)


def acf_outputs(annual, days):
    detail, summary = [], []
    for system in SYSTEMS:
        for variable, spec in VARIABLES.items():
            for software in SOFTWARE:
                d = selected_rows(annual, system, variable, software=software)
                d["error"] = d[spec[software]] - d[spec["m"]]
                d["sq_error"] = d["error"]**2
                g = d.groupby("physical_day").agg(
                    daily_mean_error=("error", "mean"),
                    daily_mse=("sq_error", "mean"),
                ).reindex(days)

                for stat in ["daily_mean_error", "daily_mse"]:
                    sig = []
                    acfs = []
                    for lag in range(1, ACF_MAX_LAG + 1):
                        a, n = acf_pair(g[stat].to_numpy(), lag)
                        threshold = 1.96 / np.sqrt(n) if n else np.nan
                        significant = bool(np.isfinite(a) and np.isfinite(threshold) and abs(a) > threshold)
                        sig.append(significant); acfs.append(a)
                        detail.append({
                            "System": system, "Variable": variable, "Software": software,
                            "Daily_statistic": stat, "lag_days": lag, "acf": a,
                            "n_pairs": n, "approx_95pct_threshold": threshold,
                            "significant": significant,
                        })
                    stable = np.nan
                    for i in range(len(sig) - 2):
                        if not any(sig[i:i+3]):
                            stable = i + 1
                            break
                    persistence = ACF_MAX_LAG if np.isnan(stable) else max(0, int(stable) - 1)
                    summary.append({
                        "System": system, "Variable": variable, "Software": software,
                        "Daily_statistic": stat,
                        "first_3lag_stable_nonsignificant_start": stable,
                        "estimated_persistence_days": persistence,
                        "acf_lag1": acfs[0], "acf_lag7": acfs[6], "acf_lag14": acfs[13],
                    })
    return pd.DataFrame(detail), pd.DataFrame(summary)


def paired_loss_acf_outputs(annual, days):
    """
    ACF of the DAILY PAIRED SQUARED-ERROR LOSS DIFFERENCE:

        d_day = MSE_IDA,day - MSE_PVsyst,day

    This is the most directly relevant dependence diagnostic for the paired
    model-comparison question. Positive d_day favors PVsyst; negative d_day
    favors IDA ICE.

    The ACF is diagnostic only; the inferential results themselves come from
    the paired moving-block bootstrap.
    """
    detail = []
    summary = []

    for system in SYSTEMS:
        for variable, spec in VARIABLES.items():
            d = selected_rows(
                annual,
                system,
                variable,
                both=True,
            ).copy()

            d["sqerr_IDA"] = (
                d[spec["IDA ICE"]] - d[spec["m"]]
            ) ** 2
            d["sqerr_PVsyst"] = (
                d[spec["PVsyst"]] - d[spec["m"]]
            ) ** 2

            daily = d.groupby("physical_day").agg(
                MSE_IDA=("sqerr_IDA", "mean"),
                MSE_PVsyst=("sqerr_PVsyst", "mean"),
            ).reindex(days)

            daily["paired_loss_difference"] = (
                daily["MSE_IDA"] - daily["MSE_PVsyst"]
            )

            x = daily["paired_loss_difference"].to_numpy(float)

            sig = []
            acfs = []

            for lag in range(1, ACF_MAX_LAG + 1):
                a, n = acf_pair(x, lag)
                threshold = 1.96 / np.sqrt(n) if n else np.nan
                significant = bool(
                    np.isfinite(a)
                    and np.isfinite(threshold)
                    and abs(a) > threshold
                )

                sig.append(significant)
                acfs.append(a)

                detail.append({
                    "System": system,
                    "Variable": variable,
                    "Daily_statistic": "MSE_IDA_minus_MSE_PVsyst",
                    "lag_days": lag,
                    "acf": a,
                    "n_pairs": n,
                    "approx_95pct_threshold": threshold,
                    "significant": significant,
                })

            stable = np.nan
            for i in range(len(sig) - 2):
                if not any(sig[i:i+3]):
                    stable = i + 1
                    break

            persistence = (
                ACF_MAX_LAG
                if np.isnan(stable)
                else max(0, int(stable) - 1)
            )

            def lag_value(lag):
                return acfs[lag - 1] if len(acfs) >= lag else np.nan

            summary.append({
                "System": system,
                "Variable": variable,
                "Daily_statistic": "MSE_IDA_minus_MSE_PVsyst",
                "first_3lag_stable_nonsignificant_start": stable,
                "estimated_persistence_days": persistence,
                "acf_lag1": lag_value(1),
                "acf_lag7": lag_value(7),
                "acf_lag14": lag_value(14),
                "acf_lag21": lag_value(21),
                "acf_lag30": lag_value(30),
            })

    return pd.DataFrame(detail), pd.DataFrame(summary)


# ---------- Annual CIs ----------

def annual_cis(annual, days, dmap, W):
    rows = []
    report_metrics = ["RMSE", "CVRMSE_percent", "MAE", "nMAE_percent",
                      "MBE", "nMBE_percent", "RE_percent", "R2"]
    for system in SYSTEMS:
        for variable, spec in VARIABLES.items():
            for software in SOFTWARE:
                d = selected_rows(annual, system, variable, software=software)
                st = daily_stats(d, spec["m"], spec[software], dmap, len(days))
                p, b = point_metrics(st), metrics_from_weights(st, W)
                for metric in report_metrics:
                    lo, hi = ci(b[metric])
                    unit = "%" if metric.endswith("_percent") else ("-" if metric == "R2" else spec["unit"])
                    rows.append({
                        "System": system, "Variable": variable, "Software": software,
                        "Metric": metric, "unit": unit, "n": int(round(p["n"])),
                        "Estimate": p[metric], "CI95_low": lo, "CI95_high": hi,
                        "block_days": ANNUAL_PRIMARY_BLOCK_DAYS, "n_boot": N_BOOT,
                    })
    return pd.DataFrame(rows)


def energy_cis(annual, days, dmap, W):
    rows = []
    spec = VARIABLES["Power"]
    for system in SYSTEMS:
        for software in SOFTWARE:
            d = selected_rows(annual, system, "Power", software=software)
            st = daily_stats(d, spec["m"], spec[software], dmap, len(days))
            p, b = point_metrics(st), metrics_from_weights(st, W)
            eb = 100 * (b["sum_simulated"] - b["sum_measured"]) / b["sum_measured"]
            lo, hi = ci(eb)
            rows.append({
                "System": system, "Software": software, "n": int(round(p["n"])),
                "Measured_energy_kWh": p["sum_measured"] / 1000,
                "Simulated_energy_kWh": p["sum_simulated"] / 1000,
                "Energy_bias_percent": 100 * (p["sum_simulated"] - p["sum_measured"]) / p["sum_measured"],
                "CI95_low": lo, "CI95_high": hi,
                "block_days": ANNUAL_PRIMARY_BLOCK_DAYS, "n_boot": N_BOOT,
                "note": "Daytime-cleaned records only; energy-bias % equals power nMBE numerically.",
            })
    return pd.DataFrame(rows)


# ---------- Paired model comparison ----------

def paired_daily(d, spec, dmap, n_days):
    m = d[spec["m"]].to_numpy(float)
    ida = d[spec["IDA ICE"]].to_numpy(float)
    pvs = d[spec["PVsyst"]].to_numpy(float)
    idx = d["physical_day"].map(dmap).to_numpy(int)
    out = {k: np.zeros(n_days, float) for k in ["n", "m", "ida2", "pvs2"]}
    vals = {
        "n": np.ones(len(d)), "m": m,
        "ida2": (ida-m)**2, "pvs2": (pvs-m)**2,
    }
    for k, v in vals.items():
        out[k] += np.bincount(idx, weights=v, minlength=n_days)
    return out


def paired_effect(st, W):
    n = W @ st["n"]
    sm = W @ st["m"]
    ri = np.sqrt((W @ st["ida2"]) / n)
    rp = np.sqrt((W @ st["pvs2"]) / n)
    dm = ri - rp
    dcv = 100 * dm / (sm / n)
    return n, ri, rp, dm, dcv


def bootstrap_p(boot, observed):
    boot = np.asarray(boot, float)
    boot = boot[np.isfinite(boot)]
    centered = boot - observed
    return (np.sum(np.abs(centered) >= abs(observed)) + 1) / (len(boot) + 1)


def holm(p):
    p = np.asarray(p, float)
    out = np.full(len(p), np.nan)
    valid = np.where(np.isfinite(p))[0]
    order = valid[np.argsort(p[valid])]
    running = 0.0
    m = len(order)
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m-rank)*p[idx]))
        out[idx] = running
    return out


def paired_comparison(annual, days, dmap, W):
    rows = []
    for system in SYSTEMS:
        for variable, spec in VARIABLES.items():
            d = selected_rows(annual, system, variable, both=True)
            st = paired_daily(d, spec, dmap, len(days))
            n0, ri0, rp0, dm0, dc0 = paired_effect(st, np.ones((1, len(days))))
            nb, rib, rpb, dmb, dcb = paired_effect(st, W)
            lo, hi = ci(dmb); clo, chi = ci(dcb)
            observed = float(dm0[0])
            rows.append({
                "System": system, "Variable": variable, "unit_RMSE": spec["unit"],
                "n_common": int(round(n0[0])), "RMSE_IDA": float(ri0[0]),
                "RMSE_PVsyst": float(rp0[0]),
                "Delta_RMSE_IDA_minus_PVsyst": observed,
                "Delta_RMSE_CI95_low": lo, "Delta_RMSE_CI95_high": hi,
                "Delta_CVRMSE_percentage_points": float(dc0[0]),
                "Delta_CVRMSE_CI95_low": clo, "Delta_CVRMSE_CI95_high": chi,
                "bootstrap_p_raw": bootstrap_p(dmb, observed),
                "block_days": ANNUAL_PRIMARY_BLOCK_DAYS, "n_boot": N_BOOT,
            })
    out = pd.DataFrame(rows)
    out["bootstrap_p_Holm"] = holm(out["bootstrap_p_raw"])
    out["significant_Holm_0.05"] = out["bootstrap_p_Holm"] < 0.05
    out["CI_excludes_zero"] = (out["Delta_RMSE_CI95_low"] > 0) | (out["Delta_RMSE_CI95_high"] < 0)
    out["Favored_by_RMSE"] = np.where(out["Delta_RMSE_IDA_minus_PVsyst"] < 0, "IDA ICE",
                                      np.where(out["Delta_RMSE_IDA_minus_PVsyst"] > 0, "PVsyst", "Tie"))
    return out


def paired_comparison_by_block(annual, days, dmap, W_by_block):
    """
    Repeat the paired IDA ICE vs PVsyst comparison for every requested
    block length.

    Holm correction is applied separately within each block length across
    the nine primary comparisons (3 variables x 3 systems).
    """
    rows = []

    for block in SENSITIVITY_BLOCK_DAYS:
        W = W_by_block[block]
        block_rows = []

        for system in SYSTEMS:
            for variable, spec in VARIABLES.items():
                d = selected_rows(
                    annual,
                    system,
                    variable,
                    both=True,
                )

                st = paired_daily(
                    d,
                    spec,
                    dmap,
                    len(days),
                )

                n0, ri0, rp0, dm0, dc0 = paired_effect(
                    st,
                    np.ones((1, len(days))),
                )
                nb, rib, rpb, dmb, dcb = paired_effect(
                    st,
                    W,
                )

                lo, hi = ci(dmb)
                clo, chi = ci(dcb)
                observed = float(dm0[0])

                block_rows.append({
                    "System": system,
                    "Variable": variable,
                    "unit_RMSE": spec["unit"],
                    "n_common": int(round(n0[0])),
                    "RMSE_IDA": float(ri0[0]),
                    "RMSE_PVsyst": float(rp0[0]),
                    "Delta_RMSE_IDA_minus_PVsyst": observed,
                    "Delta_RMSE_CI95_low": lo,
                    "Delta_RMSE_CI95_high": hi,
                    "Delta_RMSE_CI_width": hi - lo,
                    "Delta_CVRMSE_percentage_points": float(dc0[0]),
                    "Delta_CVRMSE_CI95_low": clo,
                    "Delta_CVRMSE_CI95_high": chi,
                    "Delta_CVRMSE_CI_width": chi - clo,
                    "bootstrap_p_raw": bootstrap_p(dmb, observed),
                    "block_days": block,
                    "n_boot": N_BOOT,
                })

        block_df = pd.DataFrame(block_rows)

        # Multiple-testing correction must be done within the nine tests
        # corresponding to this block length.
        block_df["bootstrap_p_Holm"] = holm(
            block_df["bootstrap_p_raw"].to_numpy()
        )
        block_df["significant_Holm_0.05"] = (
            block_df["bootstrap_p_Holm"] < 0.05
        )
        block_df["CI_excludes_zero"] = (
            (block_df["Delta_RMSE_CI95_low"] > 0)
            | (block_df["Delta_RMSE_CI95_high"] < 0)
        )
        block_df["Favored_by_RMSE"] = np.where(
            block_df["Delta_RMSE_IDA_minus_PVsyst"] < 0,
            "IDA ICE",
            np.where(
                block_df["Delta_RMSE_IDA_minus_PVsyst"] > 0,
                "PVsyst",
                "Tie",
            ),
        )

        rows.append(block_df)

    return pd.concat(rows, ignore_index=True)


# ---------- Robustness ----------

def block_sensitivity(annual, days, dmap, W_by_block):
    rows = []
    for system in SYSTEMS:
        for variable, spec in VARIABLES.items():
            for software in SOFTWARE:
                d = selected_rows(annual, system, variable, software=software)
                st = daily_stats(d, spec["m"], spec[software], dmap, len(days))
                p = point_metrics(st)
                for block in SENSITIVITY_BLOCK_DAYS:
                    b = metrics_from_weights(st, W_by_block[block])
                    for metric in ["RMSE", "CVRMSE_percent", "nMBE_percent"]:
                        lo, hi = ci(b[metric])
                        rows.append({
                            "System": system, "Variable": variable, "Software": software,
                            "Metric": metric, "Estimate": p[metric],
                            "CI95_low": lo, "CI95_high": hi, "CI_width": hi-lo,
                            "block_days": block, "n_boot": N_BOOT,
                        })
    return pd.DataFrame(rows)


def exclusion_sensitivity(annual):
    rows = []
    spec = VARIABLES["Power"]
    for system in SYSTEMS:
        for software in SOFTWARE:
            vals = {}
            for label, remove in [("final_with_4_exclusions", True), ("no_exclusions", False)]:
                d = selected_rows(annual, system, "Power", software=software, remove_exclusions=remove)
                m = d[spec["m"]].to_numpy(float); s = d[spec[software]].to_numpy(float); e = s-m
                rmse = np.sqrt(np.mean(e**2)); meanm = np.mean(m)
                vals[label] = {
                    "n": len(d), "RMSE": rmse,
                    "CVRMSE_percent": 100*rmse/meanm,
                    "nMBE_percent": 100*np.sum(e)/np.sum(m),
                }
            for metric in ["RMSE", "CVRMSE_percent", "nMBE_percent"]:
                a, b = vals["final_with_4_exclusions"][metric], vals["no_exclusions"][metric]
                rows.append({
                    "System": system, "Software": software, "Metric": metric,
                    "n_final": vals["final_with_4_exclusions"]["n"],
                    "n_no_exclusions": vals["no_exclusions"]["n"],
                    "Final_with_4_exclusions": a, "Without_exclusions": b,
                    "Difference_final_minus_unexcluded": a-b,
                })
    return pd.DataFrame(rows)


# ---------- Weather bins ----------

def weather_ci(annual, days, dmap, W):
    rows = []
    for system in SYSTEMS:
        base = annual[annual["system"] == system].copy()
        base = base[pd.to_numeric(base["GTI_measured_Wm2"], errors="coerce") > 0]
        base = base[~base["timestamp"].isin(POWER_EXCLUSIONS)].copy()
        base["kt_tilt"] = pd.to_numeric(base["kt_tilt"], errors="coerce")
        base["AOI_deg"] = pd.to_numeric(base["AOI_deg"], errors="coerce")
        base = base[base["kt_tilt"].notna() & base["AOI_deg"].notna() & (base["AOI_deg"] < 80)]

        for label, lower, upper in SKY_BINS:
            b0 = base[base["kt_tilt"] >= lower] if upper is None else base[(base["kt_tilt"] >= lower) & (base["kt_tilt"] < upper)]
            for software in SOFTWARE:
                scol = VARIABLES["Power"][software]
                d = b0.copy()
                d["P_measured_W"] = pd.to_numeric(d["P_measured_W"], errors="coerce")
                d[scol] = pd.to_numeric(d[scol], errors="coerce")
                d = d.dropna(subset=["P_measured_W", scol])
                if not len(d):
                    continue
                st = daily_stats(d, "P_measured_W", scol, dmap, len(days))
                p, boot = point_metrics(st), metrics_from_weights(st, W)
                nlo, nhi = ci(boot["nMBE_percent"]); clo, chi = ci(boot["CVRMSE_percent"])
                rows.append({
                    "System": system, "Sky_condition": label, "kt_min": lower, "kt_max": upper,
                    "Software": software, "n": int(round(p["n"])),
                    "Measured_energy_kWh": p["sum_measured"]/1000,
                    "mean_kt_tilt": float(d["kt_tilt"].mean()),
                    "nMBE_percent": p["nMBE_percent"], "nMBE_CI95_low": nlo, "nMBE_CI95_high": nhi,
                    "CVRMSE_percent": p["CVRMSE_percent"], "CVRMSE_CI95_low": clo, "CVRMSE_CI95_high": chi,
                    "block_days": ANNUAL_PRIMARY_BLOCK_DAYS, "n_boot": N_BOOT,
                })
    return pd.DataFrame(rows)


# ---------- Full-period shading ----------

def shading_ci(shading):
    days, dmap = day_axis(shading["physical_day"])
    W = block_weights(len(days), SHADING_BLOCK_DAYS, seed=SEED+900)
    rows = []
    for system in SYSTEMS:
        base = shading[shading["system"] == system].copy()
        base = base[pd.to_numeric(base["GTI_measured_Wm2"], errors="coerce") > 0]
        for software, scol in [("IDA ICE", "P_IDA_W"), ("PVsyst", "P_PVsyst_W")]:
            d = base.copy()
            d["P_measured_W"] = pd.to_numeric(d["P_measured_W"], errors="coerce")
            d[scol] = pd.to_numeric(d[scol], errors="coerce")
            d = d.dropna(subset=["P_measured_W", scol])
            st = daily_stats(d, "P_measured_W", scol, dmap, len(days))
            p, boot = point_metrics(st), metrics_from_weights(st, W)
            for metric in ["RMSE", "CVRMSE_percent", "nMBE_percent"]:
                lo, hi = ci(boot[metric])
                rows.append({
                    "System": system, "Software": software, "Metric": metric,
                    "n": int(round(p["n"])), "Estimate": p[metric],
                    "CI95_low": lo, "CI95_high": hi,
                    "block_days": SHADING_BLOCK_DAYS, "n_boot": N_BOOT,
                    "period": "full shading period",
                })
    return pd.DataFrame(rows)


# ---------- Saving ----------

def save(df, name):
    path = OUT / name
    df.to_csv(path, index=False)
    print(f"Wrote {path.relative_to(ROOT)}")


def excel_bundle(tables):
    path = OUT / "05_STATISTICAL_INFERENCE.xlsx"
    try:
        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
            for name, df in tables.items():
                sheet = name[:31]
                df.to_excel(writer, sheet_name=sheet, index=False)
                ws = writer.sheets[sheet]
                ws.freeze_panes(1, 0)
                for j, col in enumerate(df.columns):
                    lengths = [len(str(x)) for x in df[col].head(200) if pd.notna(x)]
                    width = min(max(max([len(str(col))] + lengths) + 2, 10), 32)
                    ws.set_column(j, j, width)
        print(f"Wrote {path.relative_to(ROOT)}")
    except Exception as exc:
        warnings.warn(f"Excel bundle not written; CSV files are complete. Reason: {exc}")


def main():
    print("\nSTATISTICAL UNCERTAINTY AND MODEL COMPARISON")
    print("="*72)
    print(f"Bootstrap replicates: {N_BOOT:,}")
    print(f"Annual primary block: {ANNUAL_PRIMARY_BLOCK_DAYS} days")
    print(f"Shading block length: {SHADING_BLOCK_DAYS} days")
    print(f"Sensitivity blocks:   {SENSITIVITY_BLOCK_DAYS}")
    print(f"Random seed:          {SEED}")

    annual, shading = load_data()
    days, dmap = day_axis(annual["physical_day"])
    print(
        f"Physical chronology:  "
        f"{days.min().date()} -> {days.max().date()} "
        f"({len(days)} days)"
    )

    W_by_block = {
        b: block_weights(
            len(days),
            b,
            seed=SEED + 100*b,
        )
        for b in SENSITIVITY_BLOCK_DAYS
    }
    W = W_by_block[ANNUAL_PRIMARY_BLOCK_DAYS]

    print("\n1/9 Individual-model ACF diagnostics...")
    acf_detail, acf_summary = acf_outputs(
        annual,
        days,
    )

    print("2/9 Paired-loss-difference ACF diagnostics...")
    paired_acf_detail, paired_acf_summary = (
        paired_loss_acf_outputs(
            annual,
            days,
        )
    )

    print("3/9 Annual metric CIs...")
    annual_ci = annual_cis(
        annual,
        days,
        dmap,
        W,
    )

    print("4/9 Annual energy-bias CIs...")
    energy_ci = energy_cis(
        annual,
        days,
        dmap,
        W,
    )

    print("5/9 Primary paired IDA ICE vs PVsyst comparison...")
    paired = paired_comparison(
        annual,
        days,
        dmap,
        W,
    )

    print("6/9 Paired comparison across all block lengths...")
    paired_by_block = paired_comparison_by_block(
        annual,
        days,
        dmap,
        W_by_block,
    )

    print("7/9 Individual-model block-length sensitivity...")
    block_sens = block_sensitivity(
        annual,
        days,
        dmap,
        W_by_block,
    )

    print("8/9 Exclusion sensitivity + weather-bin CIs...")
    excl = exclusion_sensitivity(annual)
    weather = weather_ci(
        annual,
        days,
        dmap,
        W,
    )

    print("9/9 Full-period shading CIs...")
    shade = shading_ci(shading)

    tables = {
        "ACF_Summary": acf_summary,
        "Paired_Loss_ACF": paired_acf_summary,
        "Annual_CI": annual_ci,
        "Annual_Energy": energy_ci,
        "Paired_Comparison_30d": paired,
        "Paired_By_Block": paired_by_block,
        "Block_Sensitivity": block_sens,
        "Exclusion_Sensitivity": excl,
        "Weather_Bin_CI": weather,
        "Shading_Full_CI": shade,
    }

    print("\nOUTPUTS")
    print("-"*72)
    save(
        acf_detail,
        "05_ACF_daily_residuals.csv",
    )
    save(
        acf_summary,
        "05_ACF_summary.csv",
    )
    save(
        paired_acf_detail,
        "05_ACF_paired_loss_difference.csv",
    )
    save(
        paired_acf_summary,
        "05_ACF_paired_loss_summary.csv",
    )
    save(
        annual_ci,
        "05_Annual_metric_CI.csv",
    )
    save(
        energy_ci,
        "05_Annual_energy_bias_CI.csv",
    )
    save(
        paired,
        "05_Paired_IDA_vs_PVsyst.csv",
    )
    save(
        paired_by_block,
        "05_Paired_IDA_vs_PVsyst_by_block.csv",
    )
    save(
        block_sens,
        "05_Block_length_sensitivity.csv",
    )
    save(
        excl,
        "05_Power_exclusion_sensitivity.csv",
    )
    save(
        weather,
        "05_Weather_bin_CI.csv",
    )
    save(
        shade,
        "05_Shading_full_period_CI.csv",
    )
    excel_bundle(tables)

    # --------------------------------------------------------------
    # Individual-model ACF summary
    # --------------------------------------------------------------
    persistence = pd.to_numeric(
        acf_summary["estimated_persistence_days"],
        errors="coerce",
    )

    print("\nINDIVIDUAL-MODEL ACF / BLOCK-LENGTH CHECK")
    print("-"*72)
    print(
        f"Median persistence:          "
        f"{persistence.median():.1f} days"
    )
    print(
        f"75th percentile persistence: "
        f"{persistence.quantile(.75):.1f} days"
    )
    print(
        f"Maximum persistence:         "
        f"{persistence.max():.1f} days"
    )

    # --------------------------------------------------------------
    # Paired-loss ACF summary
    # --------------------------------------------------------------
    paired_persistence = pd.to_numeric(
        paired_acf_summary[
            "estimated_persistence_days"
        ],
        errors="coerce",
    )

    print("\nPAIRED LOSS-DIFFERENCE ACF")
    print("-"*72)
    print(
        "Diagnostic variable: daily MSE_IDA - daily MSE_PVsyst"
    )
    print(
        f"Median persistence:          "
        f"{paired_persistence.median():.1f} days"
    )
    print(
        f"75th percentile persistence: "
        f"{paired_persistence.quantile(.75):.1f} days"
    )
    print(
        f"Maximum persistence:         "
        f"{paired_persistence.max():.1f} days"
    )
    print()
    print(
        paired_acf_summary[
            [
                "System",
                "Variable",
                "estimated_persistence_days",
                "acf_lag1",
                "acf_lag7",
                "acf_lag14",
                "acf_lag21",
                "acf_lag30",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4g}",
        )
    )

    # --------------------------------------------------------------
    # Primary 30-day paired results
    # --------------------------------------------------------------
    print("\nPRIMARY 30-DAY PAIRED IDA ICE vs PVSYST")
    print("-"*72)
    cols = [
        "System",
        "Variable",
        "Delta_RMSE_IDA_minus_PVsyst",
        "Delta_RMSE_CI95_low",
        "Delta_RMSE_CI95_high",
        "bootstrap_p_Holm",
        "Favored_by_RMSE",
        "significant_Holm_0.05",
    ]
    print(
        paired[cols].to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    # --------------------------------------------------------------
    # Block-length robustness of paired inference
    # --------------------------------------------------------------
    print("\nPAIRED COMPARISON — BLOCK-LENGTH ROBUSTNESS")
    print("-"*72)

    robustness = paired_by_block[
        [
            "block_days",
            "System",
            "Variable",
            "Delta_RMSE_CI95_low",
            "Delta_RMSE_CI95_high",
            "bootstrap_p_Holm",
            "CI_excludes_zero",
            "significant_Holm_0.05",
            "Favored_by_RMSE",
        ]
    ].copy()

    print(
        robustness.to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    print("\nSIGNIFICANT COMPARISONS BY BLOCK LENGTH")
    print("-"*72)
    sig_counts = (
        paired_by_block
        .groupby("block_days")
        .agg(
            n_CI_excluding_zero=(
                "CI_excludes_zero",
                "sum",
            ),
            n_Holm_significant=(
                "significant_Holm_0.05",
                "sum",
            ),
        )
        .reset_index()
    )
    print(sig_counts.to_string(index=False))

    # Identify comparisons whose inference changes across block lengths.
    stability = (
        paired_by_block
        .groupby(["System", "Variable"])
        .agg(
            CI_result_stable=(
                "CI_excludes_zero",
                lambda x: x.nunique() == 1,
            ),
            Holm_result_stable=(
                "significant_Holm_0.05",
                lambda x: x.nunique() == 1,
            ),
            all_blocks_favor_same_tool=(
                "Favored_by_RMSE",
                lambda x: x.nunique() == 1,
            ),
        )
        .reset_index()
    )

    changed = stability[
        ~(
            stability["CI_result_stable"]
            & stability["Holm_result_stable"]
            & stability["all_blocks_favor_same_tool"]
        )
    ]

    print("\nBLOCK-LENGTH INFERENCE STABILITY")
    print("-"*72)
    if len(changed) == 0:
        print(
            "All nine paired comparisons retain the same inferential "
            "classification across 1/7/14/21/30-day blocks."
        )
    else:
        print(
            "The following comparisons change inferential classification "
            "for at least one block length:"
        )
        print(
            changed.to_string(
                index=False
            )
        )

    print("\nDONE")
    print("="*72)
    print(
        "Delta RMSE < 0 favors IDA ICE; "
        "Delta RMSE > 0 favors PVsyst."
    )
    print(
        "Use the paired-loss ACF together with the "
        "1/7/14/21/30-day paired-bootstrap sensitivity to select the "
        "primary reporting block length."
    )
    print(
        "For the paper, emphasize effect size + 95% CI; use "
        "Holm-adjusted p-values as supplementary significance evidence."
    )
    print(
        "Sensor/calibration uncertainty is not mixed into these CIs; "
        "treat it separately if needed."
    )


if __name__ == "__main__":
    main()
