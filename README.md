# PV validation: IDA ICE versus PVsyst

> **Phase 2 analytical update (5 November 2026):** Provisional Step 29 monthly energy RMSE, seasonal and composite diurnal AC diagnostics for **both** Step 28 clock hypotheses are now in [results/revision2/](results/revision2/), with an accompanying Python script. These outputs still require independent clean-clone checking. Older Figure 3 and `05_*` uncertainties have **not** been recalculated.


This repository preserves the measured-data processing, simulation exports, numerical analyses, and audit trail accompanying **“Validation of PV Modeling in an Integrated Building Energy Simulation Tool”** (Rynoson, Bales and Battikh).

**Current state (5 November 2026): Revision 2 working candidate, NOT a fully frozen/publication-verified release.** The repository intentionally retains earlier analyses. **The original `01–11` numerical workflow is *not* the authoritative annual AC-power result for Revision 2.**

## Start here

| Need | Read / use |
|---|---|
| **Which values can I use for Revision 2?** | [Revision 2 result map](docs/REVISION2_RESULT_MAP.md) — authoritative-versus-historical file paths, sample counts, clock uncertainty and remaining gaps |
| Reproduce the **corrected annual AC** candidate | [Revision 2 reproduction guide](docs/REVISION2_REPRODUCIBILITY.md) and [Step 28 data](results/annual_audit/) |
| Inspect the shaded 2023 experiment | [Final shading audit](docs/Final_Shading_Audit_2026-10-27.md), [System A chronology](docs/README_A3_SHADING_REBUILD.md), [System C clock sensitivity](docs/README_C9_CLOCK_INTEGRATION.md) |
| Understand source files and variables | [Data provenance](docs/DATA_PROVENANCE.md), [data dictionary](docs/DATA_DICTIONARY.md) |
| Understand earlier methods and outputs | [Historical workflow documentation](docs/REPRODUCIBILITY.md), [results index](results/README_results.md), [archive](archive/README_archive.md) |
| See what is **not yet publication-ready** | [Release-readiness checklist](docs/RELEASE_READINESS.md) |

**Crucial distinction:** `derived_data/annual_unshaded_analysis.csv`, `results/Table6_Power_recomputed.csv`, `results/Monthly_RMSE_recomputed.csv`, `results/Figure3_weather_bins_recomputed.csv`, the original `05_*` inference results, and `results/PV_MASTER_RESULTS_CURRENT_PD.*` all belong to the earlier analytical generation. They remain **preserved for provenance and for explaining the earlier revisions**, but they do not reproduce the corrected Step 28 annual AC comparison. Do **not** use the older master workbook as the Revision 2 master dataset.

## Study design

Three south-facing, 45° PV installations at the RISE research facility in Borås, Sweden:

| Manuscript system | RISE ID | Technology and installation | DC nameplate |
|---|---:|---|---:|
| A | 3 | Monocrystalline silicon, BAPV | 3.9 kWp |
| B | 8 | Monocrystalline silicon, BAPV with SolarEdge optimisers | 4.8 kWp |
| C | 9 | CIGS thin-film, BIPV | 3.3 kWp |

There are two *different* measurement campaigns: **1 June 2020–31 May 2021** for annual unshaded comparisons (original measurements every 10 minutes) and **1 May–19 June 2023** for the near-field shading experiment (original measurements every 30 seconds, compared hourly). The study evaluates PV output, not experimentally validated joint whole-building energy demand and PV operation.

## Corrected annual AC-power analysis — conditional working result

`results/annual_audit/28_annual_AC_primary_fixed_CET.csv` contains the paired comparison observations. The point estimates are in `28_annual_AC_primary_and_sensitivity_metrics.csv`; the three paired 95% RMSE-difference bootstrap intervals are in `28_annual_AC_primary_CI30d.csv`.

The working cohort consists of **4,478 common, complete astronomical-daylight hourly intervals per system**, derived from six original 10-minute AC measurements per interval. Daylight selection uses solar elevation above 0° **at the measured interval start**. No model-residual-based outliers were removed in this corrected AC cohort.

IDA ICE AC generation uses the **hourly-averaged electrical-system “Produced power” results Table**, matched to the preceding physical hour at interval end; it must not be confused with sampled `.prn` electrical-system or inverter output. PVsyst uses hourly `E_Grid`.

| System | IDA ICE RMSE (W) | PVsyst RMSE (W) | Paired difference (IDA − PVsyst, W) | 95% bootstrap interval (W) |
|---|---:|---:|---:|---|
| A | 149.98 | 252.46 | −102.48 | [−124.95, −73.58] |
| B | 242.51 | 311.47 | −68.96 | [−96.18, −41.01] |
| C | 190.03 | 245.00 | −54.97 | [−72.68, −36.00] |

**These model rankings are conditional on an incompletely authenticated clock convention.** The selected interpretation treats the model as fixed CET and RISE measurements as Swedish CET/CEST. Under the mandatory alternative *unshifted civil-clock* interpretation, the ranking reverses for all three systems. The bootstrap intervals do not include this structural uncertainty. Original logger setup records and some PVsyst import inputs are unavailable. The existing `28_annual_AC_release_candidate_manifest.json` explicitly records that this is **not a final locked release**.

## Shading experiment

The independently audited shaded-period analysis is stored under `derived_data/shading_analysis_final_A3_C9.csv` and the `results/Shading_*` files. System A's pole moved on **10 May 2023 around 13:10**. Its mixed 13:00–14:00 hour is excluded only for A, leaving 1,199 full-period intervals for A and 1,200 each for B and C.

System C's measured AC power is also examined under an **inferred** timestamp reindexing; the as-recorded measured-series sensitivity is retained. The inferred clock behaviour is not a verified logger fault. Original PVsyst shading project geometries were not independently authenticated, and an independent measured unshaded baseline for 2023 is unavailable. Hourly AC and energy agreement should not be interpreted as uniquely identified shading losses or validated diode/optimizer switching dynamics.

The shaded-case source baseline was frozen at tag `shading-a3c9-freeze-2026-10-27` (commit `41b6904`).

## Scientific boundaries

- **Irradiance:** available effective-irradiance model outputs have different physical definitions and are not like-for-like measured GTI. Earlier GTI RMSE tables are **inverse–forward or channel diagnostics, not independent transposition-model validation**.
- **Temperature:** field sensors measure panel back-surface temperature, which is not automatically the modelled cell-temperature boundary.
- **Annual sample populations:** earlier irradiance and temperature comparison cohorts differ from the revised AC cohort. Never imply all annual tables share 4,478 rows.
- **Bias and uncertainty:** report whether an error is simulated minus measured. A 30-day paired moving-block CI describes conditional sampling variability, not uncertainty in clocks or unavailable physical inputs.
- **Sensitivity analyses:** an analysis computed using the earlier `01–11` cohort must not be represented as having been recomputed on the Step 28 cohort.

## Repository layout

```text
data/                Original RISE measurements, simulation exports and historical input layers
simulation_models/   Historical simulator project assets and component documentation
derived_data/        Processed canonical datasets; several annual files are historical-generation
scripts/             Original 00–11 pipeline and subsequent 16–28 targeted source audits
results/             Legacy outputs, shaded analyses, and results/annual_audit/28_* working AC release
docs/                Provenance map, methods, data dictionary, reproducibility and audit records
archive/             Superseded development scripts (retained, not deleted)
tests/               Existing targeted tests (not a comprehensive release regression suite)
config.json          Settings for the original canonical 01–11 workflow; NOT a Step 28 cohort definition
```

Use [the Revision 2 reproduction guide](docs/REVISION2_REPRODUCIBILITY.md) to work from the corrected AC source files. [The original comprehensive reproduction guide](docs/REPRODUCIBILITY.md) still documents the **historical** canonical analysis; running the old workflow does **not** regenerate the new annual AC-power table.

## Installation and historical reproduction

Use an isolated Python environment and install `requirements.txt`. A clean clone may require third-party or proprietary files for full reconstruction; see [data/README_data.md](data/README_data.md). The `00–11` scripts were used for prior analysis generations and are retained for auditability. They can overwrite historical-generation outputs; do **not** run them expecting to reproduce Revision 2 power metrics. The `20–28` scripts are the corrected annual AC diagnostic chain and should be rerun in a scratch clone/branch with explicit source and output verification.

The source code and original documentation use the MIT License with third-party data restrictions described in [LICENSE.md](LICENSE.md). Presence of third-party data in a public repository does not alone establish redistribution permission; check source agreements before archival release.

## Citation, authors and release status

Citation metadata are in [CITATION.cff](CITATION.cff). Authors: Marieke Rynoson, Chris Bales and Michel Battikh. Cite a **specific reviewed Git commit/tag**, not the continuously changing default branch, for reproducible numerical claims. A DOI and final publication metadata should be added only after formal approval.

**No final Revision 2 release tag or independent clean-clone numerical reproduction is asserted here.** Outstanding tasks are recorded in [docs/RELEASE_READINESS.md](docs/RELEASE_READINESS.md).
