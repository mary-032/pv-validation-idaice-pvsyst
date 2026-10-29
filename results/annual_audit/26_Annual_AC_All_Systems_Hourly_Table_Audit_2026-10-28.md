# Step 26 — Annual AC-power validation using native IDA ICE hourly Table exports

**Date:** 28 October 2026
**Status:** Numerically reconciled under two explicitly declared clock hypotheses; **not a final authenticated clock selection or manuscript freeze**.

## Source files and selection

- IDA ICE source files uploaded by the researcher: `3PD_hourly_avg_powers.xlsx`, `8PD_hourly_avg_powers.xlsx`, and `9PD_hourly_avg_powers.xlsx`. These were exported from the existing IDA ICE electrical-system output-object **Table**, with hourly reporting enabled; no resimulation was required. The data are normalized into `26_IDA_hourly_mean_normalized.csv`, which records the original Excel SHA-256 fingerprint for each system.
- Measured RISE AC power and PVsyst `E_Grid`: the previously audited source-matched rows in `23_annual_AC_channel_comparison_hourly.csv`, unchanged. Measured power is reconstructed from six original 10-minute observations per selected hour. Every system has **4,478** astronomical-daylight observations and **365** physical observation dates (June 2020 through May 2021); the daylight screen in this reference is evaluated at the **start** of the measurement interval.
- All three IDA Table files contain 8,736 sequential hourly values. They share the 2020 display-clock DST jump/repetition; **elapsed simulation-hour index**, not displayed civil date, is used for matching.
- The reconstructed RISE reference labels its measured interval at the **start**, `t`. For each model-clock hypothesis, a Step 23 model lookup is defined at `h`; IDA Table hour **`h+1`** represents the preceding hour `(h,h+1]`. This is the interval-end match used in the primary Table diagnostics. The *incorrect* Table same-index diagnostic is preserved but excluded from reported primary comparisons.
- No residual-dependent exclusions or lag optimisation were performed. Existing annual/shading files were not overwritten.

## Fixed-CET hypothesis — annual hourly AC comparison

**Model lookup:** winter (CET) offset 0 h; summer (CEST) offset −1 h, as defined in Step 23. This is a **hypothesis**, not independently proven metadata of the input files.

| System | Measured kWh | IDA ICE Table RMSE W | PVsyst E_Grid RMSE W | IDA − PVsyst RMSE W | 95% paired bootstrap CI W |
|:--|--:|--:|--:|--:|:--|
| A / 3 | 3,648.541 | **149.98** | 252.46 | **−102.48** | [−124.95, −73.58] |
| B / 8 | 4,230.835 | **242.51** | 311.47 | **−68.96** | [−96.18, −41.01] |
| C / 9 | 2,809.808 | **190.03** | 245.00 | **−54.97** | [−72.68, −36.00] |

**Annual energy and error-bias checks** (identical 4,478 selected observations):

| System | IDA Table predicted kWh | IDA energy bias % | PVsyst predicted kWh | PVsyst energy bias % | IDA Table CVRMSE % | PVsyst CVRMSE % |
|:--|--:|--:|--:|--:|--:|--:|
| A | 3,595.317 | −1.46 | 3,420.252 | −6.26 | 18.41 | 30.99 |
| B | 4,381.266 | +3.56 | 4,218.137 | −0.30 | 25.67 | 32.97 |
| C | 3,000.470 | +6.79 | 3,103.015 | +10.44 | 30.29 | 39.05 |

The 30-day circular moving-block bootstrap uses 5,000 draws, 365 chronological physical days, a fixed seed 20261027, and paired day weights for both software outputs. Unadjusted two-sided bootstrap sign-tail p is approximately 0.00040 for all three fixed-CET comparisons; Holm adjustment **over the three primary annual AC software comparisons** gives p ≈ 0.00120 each. This quantifies temporal sampling sensitivity, not all measurement/model-input uncertainties. Sign-tail p is an approximate bootstrap diagnostic, not a permutation test.

## Civil-clock-unshifted hypothesis — opposite ranking

| System | IDA Table RMSE W | PVsyst RMSE W | IDA − PVsyst RMSE W | 95% paired CI W |
|:--|--:|--:|--:|:--|
| A / 3 | 390.93 | **288.02** | +102.91 | [+55.42, +134.17] |
| B / 8 | 521.09 | **398.41** | +122.68 | [+69.53, +157.66] |
| C / 9 | 378.77 | **294.87** | +83.90 | [+45.87, +109.87] |

**This reversal prevents a robust software ranking until the clock assumptions are independently authenticated** from original RISE logging conventions and both simulators' input/output time bases. Matching prior results or minimizing RMSE is not independent proof.

## Source and calculation quality control

1. **8,736 Table rows** per system; consecutive indices 1 to 8736. Each file's `used_power` is identically zero, and `grid_power = −produced_p` in all rows. No missing Table values among the selected 4,478 hours in either clock scenario.
2. For **4,114 independent paired daylight indices** per system and scenario, the Table value is equal to `(sampled_produced_p[h] + sampled_produced_p[h+1]) / 2` to display rounding (maximum absolute discrepancy ≈ 0.05 W). This agrees with the separately audited System A Table behavior, but **does not prove independent subhourly energy integration**.
3. A's new 149.980755 W IDA Table RMSE, 252.463083 W PVsyst RMSE, and 30-day CI [−124.951939, −73.582434] W reproduce the existing Step 25 audit numerically.
4. Historical sampled-output RMSEs in the same cohort also reproduce Steps 21–23: fixed-CET IDA sampled 249.50 / 335.11 / 263.39 W for A/B/C; the Table means yield 149.98 / 242.51 / 190.03 W. **Do not overwrite the historical results**: retain them as output-resolution sensitivity analyses.

## Limitations and release gates

- **The CET/CEST mapping remains conditional.** Confirm the original RISE timestamp basis, the IDA ICE weather time-base and its output-object Table representation, and the PVsyst imported `.MET` time-zone/time-label conventions without RMSE-based lag tuning.
- **The Table hourly averages are an output-object reporting product.** Their close match to adjacent-endpoint arithmetic means is consistent with linear interpolation/averaging of saved hourly points; this should not be described as verified continuous-time or 10-minute simulator integration.
- **Power channel definition:** IDA ICE `produced_p` is the electrical-system generated/exported production meter (`EMS/Pprod_log`), compared against PVsyst `E_Grid` and RISE measured AC power. The distinct inverter-component `inverter_o` remains a documented sensitivity case. Exact physical metering boundary should still be confirmed against RISE instrumentation documentation.
- **Daylight boundary:** the approved reference uses solar elevation >0 at the measurement interval **start**, giving 4,478 selected hours. A midpoint interpretation yields 4,461 hours (as already documented in Step 23). Do not relabel this mask as “hour ending.”
- Bootstrap 95% ranges exclude sensor calibration, site/model parameter uncertainty and uncertainty in the alignment hypothesis.
- **Shading freeze:** commit `41b6904`, tag `shading-a3c9-freeze-2026-10-27`; not modified.

## New outputs

| File | Purpose |
|:--|:--|
| `26_IDA_hourly_mean_normalized.csv` | All 26,208 values from the three original IDA Table spreadsheets; per-file SHA-256 fingerprints |
| `26_annual_AC_all_systems_hourly.csv` | 26,868 paired measured/model rows, both clock hypotheses, all three systems |
| `26_annual_AC_all_systems_metrics.csv` | RMSE, MAE, CVRMSE, MBE, energy bias, R², sampled and hourly Table sensitivities |
| `26_annual_AC_all_systems_paired_CI30d.csv` | Paired bootstrap CI and primary power-only Holm correction |
| `26_annual_AC_all_systems_CET_CEST.csv` | Winter/summer segmentation |
| `26_annual_AC_source_QC.csv` | Integrity and independent neighbor-sample checks |
| `26_recompute_all_annual_AC_hourly_tables.py` | Portable read-only reproducibility script (Python standard library + NumPy) |

**Suggested next research task:** independently verify time-base semantics from the logger and source weather/meteorological files before selecting a clock scenario. Then make a versioned, reproducible primary annual AC table, update the annual statistical inference, and only afterward revise manuscript claims.
