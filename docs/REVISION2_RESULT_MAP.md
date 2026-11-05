# Revision 2 result map and provenance status

**Documentation checkpoint:** 5 November 2026.  
**Repository baseline inspected:** `d89e8d48292c6c422710d53169eb2563029e3bed` (29 October 2026).  
**Status:** **Working Revision 2 manuscript candidate, not a signed-off or immutable release.** No code, numeric outputs, raw data, or historical assets were changed in preparing this map.

> **Read this file before using a result in a manuscript.** The repository contains *two distinct annual analysis generations*. The original `01–11` workflow is retained as methodological history; it must **not** be represented as reproducing the corrected Revision 2 annual AC comparison. The corrected annual AC candidate is stored under `results/annual_audit/28_*`. The shading reconstruction is a *separate* audited chain. Do not combine metrics, confidence intervals, exclusions, or populations from different generations without a documented recomputation.

## 1. At-a-glance source-of-truth matrix

| Analysis component | Current interpretation | Source files | Status and restrictions |
|---|---|---|---|
| **Annual unshaded AC power, conditional working reference** | Original RISE 10-minute AC records re-aggregated to hourly means; IDA ICE hourly electrical-system *Produced power* Table; PVsyst hourly `E_Grid`; 4,478 shared astronomical-daylight hours per system | `results/annual_audit/28_annual_AC_primary_fixed_CET.csv`; `28_annual_AC_primary_and_sensitivity_metrics.csv`; `28_annual_AC_primary_CI30d.csv` | **Revision 2 working candidate**, not final or independently clock-authenticated. Use with the clock alternative below |
| **Annual AC clock alternative** | Same measured physical rows, but models matched under unshifted civil-clock interpretation | `results/annual_audit/28_annual_AC_sensitivity_civil_unshifted.csv`; `28_annual_AC_primary_and_sensitivity_metrics.csv` | **Mandatory sensitivity**: reverses all three hourly-RMSE tool rankings. Do not silently discard |
| **Annual AC method/source audits** | Measured-power reconstruction; output-channel tests; hourly Table matching; independent GTI solar-noon check | `results/annual_audit/23_*`, `26_*`, `27_*`; scripts `20_*`, `23_*`, `26_*`, `27_*`, `28_*` | Diagnostic chain; Step 23 power metrics are **not** the Step 28 primary output because Step 23 used sampled channels |
| **Shaded 2023 experiment** | Corrected System A obstruction relocation; System C measured-power clock sensitivity; hourly AC and period energy | `derived_data/shading_analysis_final_A3_C9.csv`; `results/Shading_energy_recomputed.csv`; `results/Shading_hourly_diagnostics_recomputed.csv`; `results/Shading_A3_geometry_energy.csv`; `results/Shading_C9_original_vs_reindexed_metrics.csv` | Reconstructed/audited, **conditional** on inferred C time handling and unverified historical PVsyst project geometries. Frozen shading baseline: tag `shading-a3c9-freeze-2026-10-27` / commit `41b6904` |
| **Annual GTI/effective-irradiance comparison** | Existing older processed-cohort diagnostic | `results/Table4_GTI_recomputed.csv` and `Table4_GTI_uncertainty_CI30d.csv` | **Not independent irradiance-transposition validation.** IDA and PVsyst effective-irradiance channels are not demonstrated physically equivalent to each other or to measured incident GTI |
| **Annual module/panel temperature** | Existing processed-cohort comparisons | `results/Table5_Temperature_recomputed.csv` and related uncertainty files | Retained for provenance and qualified hourly agreement; measured back-surface versus model variable observation boundaries are not confirmed equivalent. Different cohort from the new AC result |
| **Old annual AC, monthly RMSE and weather bins** | Original canonical `01–11` analysis generation | `results/Table6_Power_recomputed.csv`; `Monthly_RMSE_recomputed.csv`; `Figure3_weather_bins_recomputed.csv`; `05_*`; `PV_MASTER_RESULTS_CURRENT_PD.*` | **Historical/mixed-generation outputs**, **NOT** current Revision 2 AC or its confidence intervals. Do not substitute into the revised manuscript. Regenerate monthly, bins and uncertainty from Step 28 if retained |
| **Engerer2 and other sensitivities** | Historical scenario sensitivity against the `01–11` canonical baseline | `results/reverse_transposition/`; `results/uncertainty/`; `results/temporal_aggregation/`; `results/weather_bin_sensitivity/` | Preserve, but **not automatically valid for the new Step 28 AC cohort** |
| **Shading figures 4–6** | Illustrative days 5 June 2023 and 15 May 2023, from corrected shaded series | `results/shading_figures/`; `scripts/11_make_figures4_5_6_shading.py` | Inspect final captions/units; these do not measure independent unshaded shading losses |

## 2. Conditional annual AC reference: exactly what the current files show

Use `results/annual_audit/28_annual_AC_primary_and_sensitivity_metrics.csv` for point estimates, `28_annual_AC_primary_CI30d.csv` for paired intervals, and the paired data in `28_annual_AC_primary_fixed_CET.csv`. The currently selected **working** interpretation has a fixed-CET model clock and RISE measurement labels interpreted as Swedish CET/CEST. This is supported by metadata and a descriptive GTI solar-noon diagnostic, **not authenticated by original logger records**.

| System | IDA ICE hourly RMSE (W) | PVsyst RMSE (W) | IDA − PVsyst (W) | Paired 95% CI (W) | IDA energy bias | PVsyst energy bias |
|---|---:|---:|---:|---|---:|---:|
| A / 3 | 149.98 | 252.46 | −102.48 | [−124.95, −73.58] | −1.46% | −6.26% |
| B / 8 | 242.51 | 311.47 | −68.96 | [−96.18, −41.01] | +3.56% | −0.30% |
| C / 9 | 190.03 | 245.00 | −54.97 | [−72.68, −36.00] | +6.79% | +10.44% |

The paired 30-day moving-block bootstrap intervals describe **sampling variation conditional on the selected clock and model-output semantics**. They do **not** include structural clock ambiguity, channel-boundary mismatch, unknown sensor calibration or simulator model error. The alternative `civil_unshifted` scenario has hourly RMSEs:

| System | IDA ICE (W) | PVsyst (W) |
|---|---:|---:|
| A | 390.93 | 288.02 |
| B | 521.09 | 398.41 |
| C | 378.77 | 294.87 |

**Population and conventions:** 4,478 fully observed, matched physical daylight intervals per system, each requiring six valid 10-minute readings. Daylight is evaluated with solar elevation > 0 at the **measured interval start**, not `GTI > 0`. No residual-based outlier trimming is applied to the Step 28 annual AC reference. IDA ICE's primary channel is its hourly-averaged electrical-system *Produced power* Table value for the **preceding hour**, matched at the appropriate interval **end**; do not substitute instantaneous `.prn` sampled `produced_p` or `inverter_o` outputs. PVsyst uses `E_Grid` and its existing import timing correction must **not** be applied a second time.

**Remaining source limitations:** the original RISE logger-time setup, the source PVsyst `Meteo_89_PD.csv` and `pvsyst Rise project.MEF`, and full physical equivalence of model AC outputs to the field meter are not independently authenticated. The `28_annual_AC_release_candidate_manifest.json` explicitly says `RELEASE_CANDIDATE_NOT_FINAL_OR_LOCKED`.

## 3. Non-identical annual cohorts: do not silently combine rows

The earlier `01–11` diagnostic datasets use **different** variable-specific selected populations. For example, the current committed baseline `results/Table4_GTI_recomputed.csv` reports `n = 4635, 5351, 5351` for A/B/C, and `Table5_Temperature_recomputed.csv` reports `n = 4635, 5351, 4828`. The corrected Step 28 AC comparison has `n = 4478` for all systems. Older power, monthly and bin outputs are derived from yet other older selections. They must be labelled by population and provenance.

The GTI/effective-irradiance data are not a like-for-like validation of transposition and should not support claims of software superiority for transposition accuracy. Panel sensors measure module back-surface temperature, not directly junction temperature.

## 4. Shading reconstruction and uncertainty

The separate May–June 2023 experiment uses hourly comparisons based on 30-second field data. System A's pole moved on **10 May 2023 about 13:10**; exclude the mixed 13:00–14:00 interval **for A only** (1,199 hourly intervals). B and C each retain 1,200 full-period intervals.

| System | IDA ICE full-period energy difference | PVsyst full-period energy difference |
|---|---:|---:|
| A | −0.46% | −0.03% |
| B | −4.99% | −1.91% |
| C | +3.95% | +8.01% |

System A's period-wide bias **masks different geometric strata**: IDA ICE before move +11.32%, after move −3.39%; PVsyst +0.81% and −0.24%, respectively. Source: `results/Shading_A3_geometry_energy.csv`.

System C's measurement-only cross-system lag diagnostic suggests reindexing measured AC power on selected June days. **This is inferred, not a verified logger correction.** With native IDA inverter output, daylight RMSE changes from **244.25/253.70 W** (IDA/PVsyst, as recorded) to **158.29/171.97 W** (measurement reindexed); energy totals remain unchanged. Source: `results/Shading_C9_original_vs_reindexed_metrics.csv`. The independent field-unshaded 2023 counterfactual needed to quantify measured shading loss was not available. Original PVsyst project geometries could not be directly authenticated from their archived sources.

Consult `docs/Final_Shading_Audit_2026-10-27.md` and `docs/README_C9_CLOCK_INTEGRATION.md`; do not equate period energy agreement to validated bypass-diode mechanisms or shading-loss percentages.

## 5. What is *not* reproduced by the current Revision 2 candidate

The following **must not be advertised as regenerated from the Step 28 annual cohort** until rebuilt and checked:

1. Annual `Table6_Power_recomputed.csv`, the existing `PV_MASTER_RESULTS_CURRENT_PD.xlsx` and its `*_LONG.csv` export;
2. `Monthly_RMSE_recomputed.csv`, `Figure3_weather_bins_recomputed.csv` and `Figure3_combined_weather_bins.*`;
3. historical `05_Annual_metric_CI.csv`, `05_Paired_IDA_vs_PVsyst.csv`, `Table6_Power_uncertainty_CI30d.csv`, and old sensor/temporal/Engerer2 AC sensitivities;
4. any seasonal or diurnal analysis promised in the reviewer response but not generated from the corrected reference.

These files remain accessible intentionally for provenance. Treat `results/README_results.md` and `docs/RELEASE_READINESS.md` as guides; do **not** rename old values or copy them into new files to make the results agree. New outputs require audited code, reproducible regeneration, and explicit versioned filenames.

## 6. Historical-preservation policy

- **Never overwrite original RISE, IDA ICE or PVsyst source files**, and do not delete Git history.
- Keep `archive/` and older generated outputs available. Where a historical result remains in `results/` for script compatibility, label it **legacy generation** in documentation instead of silently moving it.
- Do not modify `config.json` to redefine historical `01–11` thresholds as if they described the Step 28 AC cohort.
- When a corrected output is created, use a new output name/namespace, record script inputs and checksums, and identify superseded outputs in this map.
- Freeze an approved release with a Git tag and, where practicable, a DOI. This document deliberately does **not** claim that such a release already exists.

## 7. Independent verification checklist

At minimum, compare the `28_*` metrics to the paired rows; verify 4,478 per system under both scenarios; confirm model-output channel and interval orientation; confirm measured-energy identity between the two clock scenarios; verify the 30-day paired intervals; check A relocation and C as-recorded sensitivity; and confirm that older `01–11` files were not silently replaced. See `docs/RELEASE_READINESS.md` for outstanding tasks.

**Provenance of this map:** statements above were checked against committed repository audit reports, CSVs and scripts. This documentation update itself is not an independent end-to-end recomputation of raw measurements or numerical simulation.
