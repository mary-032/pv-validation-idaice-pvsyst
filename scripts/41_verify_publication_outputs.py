#!/usr/bin/env python3
"""Read-only regression gates for the adopted manuscript tables and figures.

Checks COMMITTED result files; does not rerun IDA ICE/PVsyst or regenerate data.
Run: python scripts/41_verify_publication_outputs.py
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = "fixed_CET_hypothesis"  # fixed-CET MODEL lookup, CET/CEST measurements
ANNUAL = ROOT / "results/annual_audit"
REV = ROOT / "results/revision2"
SUP = REV / "40_supplement"
EXPECTED = {
    "A": {"IDA": 149.980755052, "PVsyst": 252.463083042,
          "monthly_IDA": 4.171576262, "monthly_PVsyst": 7.154076237,
          "ci": (-124.951938867, -73.582434032),
          "fig3_n": [1685, 657, 568, 383, 300]},
    "B": {"IDA": 242.506640693, "PVsyst": 311.465502732,
          "monthly_IDA": 3.999261064, "monthly_PVsyst": 2.414030482,
          "ci": (-96.180126643, -41.010792389),
          "fig3_n": [1760, 629, 543, 329, 332]},
    "C": {"IDA": 190.032274505, "PVsyst": 244.999560228,
          "monthly_IDA": 7.867862077, "monthly_PVsyst": 9.799608165,
          "ci": (-72.681322048, -36.002520325),
          "fig3_n": [1760, 629, 543, 329, 332]},
}
BINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.75), (0.75, math.inf)]


def rows(path: Path) -> list[dict[str, str]]:
    assert path.is_file(), f"Required publication source missing: {path}"
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def near(actual: object, expected: float, where: str, tol: float = 0.00001) -> None:
    assert math.isclose(float(actual), expected, abs_tol=tol, rel_tol=0), (
        f"{where}: found {actual}, expected {expected}"
    )


def unique(data: list[dict], **filters: str) -> dict:
    matched = [x for x in data if all(x.get(k) == v for k, v in filters.items())]
    assert len(matched) == 1, (filters, f"expected 1 row, found {len(matched)}")
    return matched[0]


def check() -> None:
    annual = rows(ANNUAL / "28_annual_AC_primary_and_sensitivity_metrics.csv")
    ci = rows(ANNUAL / "28_annual_AC_primary_CI30d.csv")
    monthly = rows(REV / "29_monthly_RMSE_AC.csv")
    fig3 = rows(REV / "35_Figure3_primary_source_statistics.csv")
    seasonal = rows(SUP / "Table_S1a_seasonal_fixed_CET_hypothesis.csv")
    diurnal = rows(SUP / "Figure_S1_diurnal_source_statistics.csv")

    for sys, target in EXPECTED.items():
        ida = unique(annual, system=sys, scenario=SCENARIO,
                     output="IDA ICE hourly Table, interval-end")
        pv = unique(annual, system=sys, scenario=SCENARIO, output="PVsyst E_Grid")
        for label, rec in [("IDA", ida), ("PVsyst", pv)]:
            near(rec["RMSE_W"], target[label], sys + " " + label + " hourly RMSE")
            assert int(rec["n"]) == 4478, f"{sys} annual cohort changed"
        paired = unique(ci, system=sys, scenario=SCENARIO)
        near(paired["delta_RMSE_IDA_minus_PVsyst_W"],
             target["IDA"] - target["PVsyst"], sys + " paired delta")
        near(paired["CI95_low_W"], target["ci"][0], sys + " lower CI")
        near(paired["CI95_high_W"], target["ci"][1], sys + " upper CI")
        assert float(paired["CI95_high_W"]) < 0, f"{sys} paired CI crosses zero"
        for label, model in [("IDA", "IDA_ICE"), ("PVsyst", "PVsyst")]:
            rec = unique(monthly, scenario=SCENARIO, system=sys, model=model)
            near(rec["RMSE_month_kWh_per_kWp"], target["monthly_" + label],
                 sys + " " + label + " monthly RMSE")
            assert int(float(rec["n_months"])) == 12

        for idx, (lo, hi) in enumerate(BINS):
            chosen = [x for x in fig3 if
                      x["scenario"] == SCENARIO and x["system"] == sys and
                      x["selection"] == "Eext_positive_AOI_lt80" and
                      math.isclose(float(x["kt_lower_inclusive"]), lo, abs_tol=1e-9) and
                      (math.isinf(hi) and x["kt_upper_exclusive"].lower() in ("", "inf", "infinity") or
                       not math.isinf(hi) and math.isclose(float(x["kt_upper_exclusive"]), hi, abs_tol=1e-9))]
            assert len(chosen) == 2, (sys, idx, len(chosen))
            assert set(r["model"] for r in chosen) == {"IDA ICE", "PVsyst"}
            assert all(int(r["n"]) == target["fig3_n"][idx] for r in chosen)
        assert sum(target["fig3_n"]) == 3593

        for model in ("IDA_ICE", "PVsyst"):
            subset = [x for x in diurnal if
                      x["scenario"] == SCENARIO and x["system"] == sys and x["model"] == model]
            assert len(subset) > 0 and sum(int(x["n"]) for x in subset) == 4478, (
                sys, model, "diurnal cohort changed"
            )

    # Supplement table selected for journal Table S1: 6 model/system rows, not S1b.
    assert len(seasonal) == 6
    a_ida = unique(seasonal, System="A", Software="IDA ICE")
    a_pv = unique(seasonal, System="A", Software="PVsyst")
    assert a_ida["Winter (DJF)"] == "58.8 / +17.3"
    assert a_ida["Summer (JJA)"] == "13.6 / -4.3"
    assert a_pv["Winter (DJF)"] == "64.0 / +11.0"
    assert a_pv["Summer (JJA)"] == "26.2 / -8.4"

    # Source for new Supplementary Table S2: absolute W-valued bin metrics.
    c_low = [x for x in fig3 if x["scenario"] == SCENARIO and x["system"] == "C"
             and x["selection"] == "Eext_positive_AOI_lt80"
             and math.isclose(float(x["kt_lower_inclusive"]), 0.0)]
    near(unique(c_low, model="IDA ICE")["RMSE_W"], 176.1, "S2 C lowest IDA RMSE", 0.06)
    near(unique(c_low, model="PVsyst")["RMSE_W"], 208.9, "S2 C lowest PV RMSE", 0.06)

    assert (REV / "35_Figure3_fixed_CET_AOI_lt80_CANDIDATE.pdf").is_file()
    assert (SUP / "Figure_S1a_diurnal_fixed_CET_hypothesis.pdf").is_file()
    print("PASS: adopted Table 6 (hourly/monthly/paired CI), Figure 3 (all bins),")
    print("      Table S1, Figure S1 and Table S2 anchors; no files modified")
    print("      Annual matched cohort: 4,478 hours/system; Figure 3: 3,593 hours/system")


if __name__ == "__main__":
    check()
