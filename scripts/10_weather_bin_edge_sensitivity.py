from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd

# =============================================================================
# 10 - WEATHER-BIN EDGE SENSITIVITY
# =============================================================================
# Tests whether the Figure 3 weather-condition patterns depend on the exact
# kt_tilt thresholds. Uses the finalized record rules and perturbs every
# internal bin edge by ±0.05:
#
#   1) all edges together: -0.05 / nominal / +0.05
#   2) one edge at a time: each edge ±0.05
#
# Both Perez-Driesse and corrected Engerer2 are evaluated.
# No simulation values, measured data, AOI, or kt_tilt values are altered.
#
# Final weather-bin rules:
#   measured GTI > 0
#   four agreed power timestamps excluded
#   paired nonmissing power, kt_tilt and AOI
#   AOI < configured weather_aoi_limit_deg
#   no upper cap on kt_tilt
# =============================================================================

ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config.json"

PD_CANON = ROOT / "02_canonical_data" / "annual_unshaded_analysis.csv"
E2_CANON = (
    ROOT / "02a_canonical_data_Engerer2"
    / "annual_unshaded_analysis_Engerer2.csv"
)

OUT = ROOT / "03_analysis_output" / "weather_bin_sensitivity"
OUT.mkdir(parents=True, exist_ok=True)

EDGE_SHIFT = 0.05

POWER_EXCLUSIONS = pd.to_datetime([
    "2021-02-02 12:00:00",
    "2021-02-02 13:00:00",
    "2021-04-02 13:00:00",
    "2021-04-30 13:00:00",
])


def require_inputs():
    missing = [
        p for p in (CFG_PATH, PD_CANON, E2_CANON)
        if not p.exists()
    ]
    if missing:
        raise FileNotFoundError(
            "Missing required input(s):\n"
            + "\n".join(f"  - {p.relative_to(ROOT)}" for p in missing)
        )


def load_canonical(path):
    d = pd.read_csv(path, parse_dates=["timestamp"])
    d["timestamp"] = pd.to_datetime(d["timestamp"]).dt.floor("s")
    return d


def load_nominal_bins(cfg):
    bins = []
    for b in cfg["sky_bins"]:
        bins.append({
            "name": str(b["name"]),
            "min": float(b["min"]),
            "max": None if b["max"] is None else float(b["max"]),
        })

    for i in range(1, len(bins)):
        if bins[i - 1]["max"] is None:
            raise ValueError("Only final sky bin may have max=None.")
        if not np.isclose(
            bins[i]["min"], bins[i - 1]["max"], atol=1e-12
        ):
            raise ValueError("Configured sky bins are not contiguous.")

    return bins


def internal_edges(bins):
    return np.array(
        [float(bins[i]["max"]) for i in range(len(bins) - 1)],
        dtype=float,
    )


def bins_from_edges(nominal_bins, edges):
    edges = np.asarray(edges, dtype=float)

    if not np.all(np.diff(edges) > 0):
        raise ValueError(f"Invalid perturbed edges: {edges}")

    out = []
    for i, b in enumerate(nominal_bins):
        lo = (
            nominal_bins[0]["min"]
            if i == 0
            else float(edges[i - 1])
        )
        hi = None if i == len(nominal_bins) - 1 else float(edges[i])
        out.append({"name": b["name"], "min": float(lo), "max": hi})
    return out


def build_schemes(nominal_bins):
    base = internal_edges(nominal_bins)
    schemes = []

    def add(name, kind, edges, edge_index=None, direction=None):
        schemes.append({
            "scheme": name,
            "scheme_type": kind,
            "edge_index": edge_index,
            "direction": direction,
            "edges": np.asarray(edges, dtype=float),
            "bins": bins_from_edges(nominal_bins, edges),
        })

    add("nominal", "nominal", base)

    add(
        "all_edges_minus_0p05",
        "coordinated",
        base - EDGE_SHIFT,
        direction="minus",
    )
    add(
        "all_edges_plus_0p05",
        "coordinated",
        base + EDGE_SHIFT,
        direction="plus",
    )

    for i in range(len(base)):
        for delta, direction in ((-EDGE_SHIFT, "minus"), (EDGE_SHIFT, "plus")):
            e = base.copy()
            e[i] += delta

            if not np.all(np.diff(e) > 0):
                warnings.warn(
                    f"Skipping invalid edge-{i+1} {direction} perturbation."
                )
                continue

            add(
                f"edge_{i+1}_{direction}_0p05",
                "one_at_a_time",
                e,
                edge_index=i + 1,
                direction=direction,
            )

    return schemes


def scheme_table(schemes, nominal_bins):
    rows = []

    for s in schemes:
        r = {
            "scheme": s["scheme"],
            "scheme_type": s["scheme_type"],
            "perturbed_edge_index": s["edge_index"],
            "direction": s["direction"],
        }

        for i, edge in enumerate(s["edges"], start=1):
            r[f"edge_{i}"] = edge
            r[f"edge_{i}_between"] = (
                f"{nominal_bins[i-1]['name']} | {nominal_bins[i]['name']}"
            )

        rows.append(r)

    return pd.DataFrame(rows)


def clean_weather_records(d, system, aoi_limit):
    x = d[d["system"] == system].copy()

    for c in (
        "GTI_measured_Wm2",
        "P_measured_W",
        "P_IDA_W",
        "P_PVsyst_W",
        "kt_tilt",
        "AOI_deg",
    ):
        x[c] = pd.to_numeric(x[c], errors="coerce")

    x = x[x["GTI_measured_Wm2"] > 0].copy()
    x = x[~x["timestamp"].isin(POWER_EXCLUSIONS)].copy()

    x = x.dropna(subset=[
        "P_measured_W",
        "P_IDA_W",
        "P_PVsyst_W",
        "kt_tilt",
        "AOI_deg",
    ])

    x = x[x["AOI_deg"] < float(aoi_limit)].copy()

    # Intentionally no upper kt_tilt cap.
    return x


def stats(measured, simulated):
    m = pd.to_numeric(measured, errors="coerce")
    s = pd.to_numeric(simulated, errors="coerce")
    good = m.notna() & s.notna()

    m = m[good].to_numpy(float)
    s = s[good].to_numpy(float)

    if len(m) == 0:
        return None

    e = s - m
    mean_m = float(np.mean(m))

    rmse = float(np.sqrt(np.mean(e ** 2)))
    mae = float(np.mean(np.abs(e)))
    mbe = float(np.mean(e))

    return {
        "n": len(m),
        "RMSE_W": rmse,
        "CVRMSE_percent": (
            rmse / mean_m * 100 if mean_m != 0 else np.nan
        ),
        "MAE_W": mae,
        "nMAE_percent": (
            mae / mean_m * 100 if mean_m != 0 else np.nan
        ),
        "MBE_W": mbe,
        "nMBE_percent": (
            np.sum(e) / np.sum(m) * 100 if np.sum(m) != 0 else np.nan
        ),
        "measured_energy_kWh": float(np.sum(m) / 1000),
        "simulated_energy_kWh": float(np.sum(s) / 1000),
    }


def run_method(method, d, schemes, aoi_limit):
    rows = []

    for system in ("A", "B", "C"):
        x = clean_weather_records(d, system, aoi_limit)

        for sch in schemes:
            for order, b in enumerate(sch["bins"], start=1):
                mask = x["kt_tilt"] >= b["min"]

                if b["max"] is not None:
                    mask &= x["kt_tilt"] < b["max"]

                bx = x[mask].copy()

                for software, sim_col in (
                    ("IDA ICE", "P_IDA_W"),
                    ("PVsyst", "P_PVsyst_W"),
                ):
                    st = stats(bx["P_measured_W"], bx[sim_col])
                    if st is None:
                        continue

                    rows.append({
                        "Irradiance_method": method,
                        "System": system,
                        "Software": software,
                        "scheme": sch["scheme"],
                        "scheme_type": sch["scheme_type"],
                        "Sky_condition": b["name"],
                        "bin_order": order,
                        "kt_min": b["min"],
                        "kt_max": np.nan if b["max"] is None else b["max"],
                        "mean_kt_tilt": float(bx["kt_tilt"].mean()),
                        "mean_AOI_deg": float(bx["AOI_deg"].mean()),
                        **st,
                    })

    return pd.DataFrame(rows)


def tool_comparison(metrics):
    keys = [
        "Irradiance_method",
        "System",
        "scheme",
        "scheme_type",
        "Sky_condition",
        "bin_order",
        "kt_min",
        "kt_max",
    ]

    ida = metrics[metrics["Software"] == "IDA ICE"][
        keys + ["n", "CVRMSE_percent", "nMBE_percent"]
    ].rename(columns={
        "n": "n_IDA",
        "CVRMSE_percent": "CVRMSE_IDA_percent",
        "nMBE_percent": "nMBE_IDA_percent",
    })

    pvs = metrics[metrics["Software"] == "PVsyst"][
        keys + ["n", "CVRMSE_percent", "nMBE_percent"]
    ].rename(columns={
        "n": "n_PVsyst",
        "CVRMSE_percent": "CVRMSE_PVsyst_percent",
        "nMBE_percent": "nMBE_PVsyst_percent",
    })

    out = ida.merge(pvs, on=keys, how="inner", validate="one_to_one")

    out["Delta_CVRMSE_IDA_minus_PVsyst_pp"] = (
        out["CVRMSE_IDA_percent"] - out["CVRMSE_PVsyst_percent"]
    )

    out["Favored_by_CVRMSE"] = np.where(
        out["Delta_CVRMSE_IDA_minus_PVsyst_pp"] < 0,
        "IDA ICE",
        np.where(
            out["Delta_CVRMSE_IDA_minus_PVsyst_pp"] > 0,
            "PVsyst",
            "Tie",
        ),
    )

    return out


def nominal_vs_perturbed(metrics):
    nominal = metrics[metrics["scheme"] == "nominal"][
        [
            "Irradiance_method",
            "System",
            "Software",
            "Sky_condition",
            "bin_order",
            "n",
            "CVRMSE_percent",
            "nMBE_percent",
        ]
    ].rename(columns={
        "n": "Nominal_n",
        "CVRMSE_percent": "Nominal_CVRMSE_percent",
        "nMBE_percent": "Nominal_nMBE_percent",
    })

    out = metrics[metrics["scheme"] != "nominal"].merge(
        nominal,
        on=[
            "Irradiance_method",
            "System",
            "Software",
            "Sky_condition",
            "bin_order",
        ],
        how="left",
        validate="many_to_one",
    )

    out["Delta_n_vs_nominal"] = out["n"] - out["Nominal_n"]
    out["Delta_CVRMSE_pp_vs_nominal"] = (
        out["CVRMSE_percent"] - out["Nominal_CVRMSE_percent"]
    )
    out["Delta_nMBE_pp_vs_nominal"] = (
        out["nMBE_percent"] - out["Nominal_nMBE_percent"]
    )

    out["nMBE_sign_preserved"] = (
        np.sign(out["nMBE_percent"])
        == np.sign(out["Nominal_nMBE_percent"])
    )

    return out


def gradient_table(metrics):
    rows = []

    for keys, g in metrics.groupby(
        [
            "Irradiance_method",
            "System",
            "Software",
            "scheme",
            "scheme_type",
        ],
        sort=False,
    ):
        method, system, software, scheme, scheme_type = keys

        g = g.sort_values("bin_order")
        cv = g["CVRMSE_percent"].to_numpy(float)

        ranks_x = pd.Series(
            g["bin_order"].to_numpy(float)
        ).rank().to_numpy(float)

        ranks_y = pd.Series(cv).rank().to_numpy(float)

        rho = (
            float(np.corrcoef(ranks_x, ranks_y)[0, 1])
            if len(cv) > 1 and np.std(ranks_y) > 0
            else np.nan
        )

        rows.append({
            "Irradiance_method": method,
            "System": system,
            "Software": software,
            "scheme": scheme,
            "scheme_type": scheme_type,
            "n_bins": len(g),
            "CVRMSE_cloudiest_percent": float(cv[0]),
            "CVRMSE_clearest_percent": float(cv[-1]),
            "Cloudiest_minus_clearest_CVRMSE_pp": float(cv[0] - cv[-1]),
            "Cloudiest_CVRMSE_gt_clearest": bool(cv[0] > cv[-1]),
            "Spearman_bin_order_vs_CVRMSE": rho,
            "Negative_clearness_gradient": (
                bool(rho < 0) if np.isfinite(rho) else False
            ),
            "Strictly_nonincreasing_CVRMSE": bool(
                np.all(np.diff(cv) <= 0)
            ),
        })

    return pd.DataFrame(rows)


def robustness_summary(metrics, tc, compare, gradient):
    rows = []

    for method in metrics["Irradiance_method"].unique():
        c = compare[compare["Irradiance_method"] == method]

        t = tc[tc["Irradiance_method"] == method].copy()

        nominal_rank = t[t["scheme"] == "nominal"][
            [
                "System",
                "Sky_condition",
                "bin_order",
                "Favored_by_CVRMSE",
            ]
        ].rename(columns={
            "Favored_by_CVRMSE": "Nominal_favored"
        })

        pert = t[t["scheme"] != "nominal"].merge(
            nominal_rank,
            on=["System", "Sky_condition", "bin_order"],
            how="left",
            validate="many_to_one",
        )

        pert["ranking_preserved"] = (
            pert["Favored_by_CVRMSE"] == pert["Nominal_favored"]
        )

        gd = gradient[
            gradient["Irradiance_method"] == method
        ]

        rows.append({
            "Irradiance_method": method,
            "nMBE_sign_preserved_fraction": float(
                c["nMBE_sign_preserved"].mean()
            ),
            "tool_CVRMSE_ranking_preserved_fraction": float(
                pert["ranking_preserved"].mean()
            ),
            "max_abs_CVRMSE_change_pp": float(
                c["Delta_CVRMSE_pp_vs_nominal"].abs().max()
            ),
            "median_abs_CVRMSE_change_pp": float(
                c["Delta_CVRMSE_pp_vs_nominal"].abs().median()
            ),
            "max_abs_nMBE_change_pp": float(
                c["Delta_nMBE_pp_vs_nominal"].abs().max()
            ),
            "median_abs_nMBE_change_pp": float(
                c["Delta_nMBE_pp_vs_nominal"].abs().median()
            ),
            "cloudiest_gt_clearest_fraction_all_schemes": float(
                gd["Cloudiest_CVRMSE_gt_clearest"].mean()
            ),
            "negative_gradient_fraction_all_schemes": float(
                gd["Negative_clearness_gradient"].mean()
            ),
            "strictly_nonincreasing_fraction_all_schemes": float(
                gd["Strictly_nonincreasing_CVRMSE"].mean()
            ),
        })

    return pd.DataFrame(rows)


def write_excel(schemes_df, metrics, tc, compare, gradient, summary):
    path = OUT / "10_WEATHER_BIN_EDGE_SENSITIVITY.xlsx"

    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        sheets = {
            "Edge_schemes": schemes_df,
            "Metrics": metrics,
            "Tool_comparison": tc,
            "Nominal_vs_perturbed": compare,
            "Qualitative_gradient": gradient,
            "Robustness_summary": summary,
        }

        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
            ws = writer.sheets[name[:31]]
            ws.freeze_panes(1, 0)

            for j, col in enumerate(df.columns):
                lengths = [
                    len(str(v))
                    for v in df[col].head(200)
                    if pd.notna(v)
                ]
                width = max([len(str(col))] + lengths)
                ws.set_column(j, j, min(max(width + 2, 10), 42))

    print(f"Wrote {path.relative_to(ROOT)}")


def main():
    require_inputs()

    cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
    nominal_bins = load_nominal_bins(cfg)
    schemes = build_schemes(nominal_bins)
    schemes_df = scheme_table(schemes, nominal_bins)

    aoi_limit = float(
        cfg["annual"]["weather_aoi_limit_deg"]
    )

    print("\nWEATHER-BIN EDGE SENSITIVITY")
    print("=" * 78)
    print(f"Internal edge shift: ±{EDGE_SHIFT:.2f}")
    print(f"AOI limit: {aoi_limit:g}°")
    print("No upper cap on kt_tilt.")

    print("\nNOMINAL BINS")
    print("-" * 78)

    for i, b in enumerate(nominal_bins, start=1):
        hi = "∞" if b["max"] is None else f"{b['max']:.3f}"
        print(f"{i}. {b['name']}: [{b['min']:.3f}, {hi})")

    print(
        f"\nSchemes evaluated: {len(schemes)} "
        "(nominal + coordinated ±0.05 + one-at-a-time ±0.05)."
    )

    datasets = {
        "Perez-Driesse": load_canonical(PD_CANON),
        "Engerer2": load_canonical(E2_CANON),
    }

    parts = []

    for method, d in datasets.items():
        print(f"\nRunning {method}...")
        parts.append(
            run_method(
                method,
                d,
                schemes,
                aoi_limit,
            )
        )

    metrics = pd.concat(parts, ignore_index=True)
    tc = tool_comparison(metrics)
    compare = nominal_vs_perturbed(metrics)
    gradient = gradient_table(metrics)
    summary = robustness_summary(
        metrics, tc, compare, gradient
    )

    outputs = {
        "10_Weather_bin_edge_schemes.csv": schemes_df,
        "10_Weather_bin_edge_sensitivity_metrics.csv": metrics,
        "10_Weather_bin_tool_comparison.csv": tc,
        "10_Weather_bin_nominal_vs_perturbed.csv": compare,
        "10_Weather_bin_qualitative_gradient.csv": gradient,
        "10_Weather_bin_robustness_summary.csv": summary,
    }

    print("\nOUTPUTS")
    print("-" * 78)

    for filename, df in outputs.items():
        path = OUT / filename
        df.to_csv(path, index=False)
        print(f"Wrote {path.relative_to(ROOT)}")

    write_excel(
        schemes_df,
        metrics,
        tc,
        compare,
        gradient,
        summary,
    )

    print("\nROBUSTNESS SUMMARY")
    print("-" * 78)
    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    print("\nCOORDINATED ±0.05: CV(RMSE) CLOUDINESS GRADIENT")
    print("-" * 78)

    coordinated = gradient[
        gradient["scheme"].isin([
            "all_edges_minus_0p05",
            "nominal",
            "all_edges_plus_0p05",
        ])
    ]

    print(
        coordinated[
            [
                "Irradiance_method",
                "System",
                "Software",
                "scheme",
                "CVRMSE_cloudiest_percent",
                "CVRMSE_clearest_percent",
                "Cloudiest_CVRMSE_gt_clearest",
                "Spearman_bin_order_vs_CVRMSE",
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.5g}",
        )
    )

    print("\nDONE")
    print("=" * 78)
    print(
        "If the cloudiest-to-clearest CV(RMSE) gradient and the main nMBE "
        "patterns remain stable, the qualitative Figure 3 interpretation does "
        "not depend strongly on the exact nominal bin thresholds."
    )


if __name__ == "__main__":
    main()
