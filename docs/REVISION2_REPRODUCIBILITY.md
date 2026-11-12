# Reproducing the Revision 2 annual AC-power candidate

> **12 November 2026 manuscript selection:** The authors adopt Swedish CET/CEST measurement labels matched to fixed-CET model-output intervals (`fixed_CET_hypothesis`). The alternative `civil_unshifted` remains a **required check for complete repository reproducibility**, not a figure, table or additional clock scenario chosen for the submitted article. Original logger settings have not been independently authenticated. See [clock-convention decision](REVISION2_CLOCK_CONVENTION_DECISION.md).

**Status (5 November 2026): audited working candidate, not an independently authenticated or frozen publication release.** This guide complements [REVISION2_RESULT_MAP.md](REVISION2_RESULT_MAP.md). For the **historical `01–11` cohort**, use [REPRODUCIBILITY.md](REPRODUCIBILITY.md) instead.

## A. Read-only verification from the committed files (preferred first step)

The source of the current manuscript's corrected annual AC figures is:

- `results/annual_audit/28_annual_AC_primary_fixed_CET.csv` — paired 4,478-hour-per-system working cohort.
- `results/annual_audit/28_annual_AC_sensitivity_civil_unshifted.csv` — identical measured cohort, alternative model clock.
- `results/annual_audit/28_annual_AC_primary_and_sensitivity_metrics.csv` — model-specific point estimates for both clocks.
- `results/annual_audit/28_annual_AC_primary_CI30d.csv` — paired 30-day moving-block RMSE difference intervals.
- `results/annual_audit/28_annual_AC_release_candidate_manifest.json` — input fingerprints, definitions, caveats.
- `results/annual_audit/28_annual_AC_release_candidate_note.md` — contemporaneous source-audit notes.

These are CSV/JSON/Markdown and can be inspected without IDA ICE or PVsyst licenses. **Do not** use `results/Table6_Power_recomputed.csv`, `results/05_Paired_IDA_vs_PVsyst.csv`, the earlier consolidated master workbook or older weather-bin figure as substitutes.

### Basic environment

```bash
git clone https://github.com/mary-032/pv-validation-idaice-pvsyst.git
cd pv-validation-idaice-pvsyst
python -m venv .venv
# Activate .venv with your operating system's command
python -m pip install -r requirements.txt
```

For strict reproducibility check out a specific reviewed commit or tagged release, rather than moving `main`. There is **not yet a signed-off Revision 2 tag**. This documentation cleanup was prepared against parent `d89e8d48292c6c422710d53169eb2563029e3bed` and is not itself proof that a clean clone passes the entire workflow.

### Minimum numerical verification

A reviewer can read the `28_annual_AC_primary_and_sensitivity_metrics.csv` and confirm:

| System | Primary IDA RMSE (W) | Primary PVsyst RMSE (W) | Same physical sample size |
|---|---:|---:|---:|
| A | 149.98 | 252.46 | 4,478 |
| B | 242.51 | 311.47 | 4,478 |
| C | 190.03 | 245.00 | 4,478 |

The **publication-selected alignment** is `fixed_CET_hypothesis`: Swedish CET/CEST measurement labels matched to fixed-CET model intervals. For a **complete repository audit**, also compare those same measured observations under `civil_unshifted`, verify measured energy per system is invariant and reproduce the model-ranking reversal. This is a **required repository verification**, not an alternative selected for journal presentation. The 30-day paired intervals for `RMSE_IDA - RMSE_PVsyst` describe variability **within** the adopted alignment. For interval and channel semantics, read Steps [23](../results/annual_audit/23_annual_AC_channel_report.md), [26](../results/annual_audit/26_Annual_AC_All_Systems_Hourly_Table_Audit_2026-10-28.md), [27](../results/annual_audit/27_CLOCK_PROVENANCE_EVIDENCE_2026-10-28.md) and [28](../results/annual_audit/28_annual_AC_release_candidate_note.md).

## B. Reconstruction from source files and archived simulator outputs

**Use a disposable clone or working branch**, not the approved source tree, because scripts regenerate outputs. Confirm that all required files are available. The source of the recorded annual AC observations is the original `data/measured/annual/RISE_raw10min_389.xlsx` workbook. The IDA ICE original electrical-system hourly Table exports were stored as `3PD_hourly_avg_powers.xlsx`, `8PD_hourly_avg_powers.xlsx` and `9PD_hourly_avg_powers.xlsx` and were normalized into `results/annual_audit/26_IDA_hourly_mean_normalized.csv`. Check those original Excel exports and SHA-256 fingerprints before claiming full raw-source reproducibility. Other preserved annual model outputs are in `data/ida_ice/annual/Perez_Driesse/` and `data/pvsyst/annual/Perez_Driesse/`.

The stage-specific scripts are:

| Stage | Script | Action / expected role |
|---|---|---|
| 20 | `scripts/20_rebuild_raw_annual_AC_diagnostic.py` | Non-destructive original 10-minute reconstruction diagnostics |
| 23 | `scripts/23_annual_AC_power_channel_sensitivity.py` | Prepared reference plus sampled-channel comparison and explicit clock scenarios |
| 26 | `scripts/26_recompute_all_annual_AC_hourly_tables.py` | Joins the Stage 23 matched reference to normalized native hourly IDA Table output; computes primary channel metrics and paired inference for both clocks |
| 27 | `scripts/27_check_RISE_GTIsolar_noon.py` | Independent, **descriptive** irradiance-centroid clock sanity check |
| 28 | `scripts/28_build_annual_AC_release_candidate.py` | Packages and consistency-checks the conditional candidate using Step 26 and Step 27 outputs; writes new `28_*` files |

**Execution order matters.** A fully clean rebuild also depends on the intermediate Step 20–23 data preparation and the native IDA Table export files. Read each script's docstring and inspect source availability before running. Stages 26 and 28 cannot regenerate upstream proprietary Table exports that were never exported. No claim is made here that every upstream input is redistributed or that the entire sequence has been independently executed from a fresh clone.

Once Step 23, normalized Step 26 input and Step 27 inputs have been checked, the later stages can be run from the repository root (in a disposable clone):

```bash
python scripts/26_recompute_all_annual_AC_hourly_tables.py
python scripts/27_check_RISE_GTIsolar_noon.py
python scripts/28_build_annual_AC_release_candidate.py
```

**Important:** Step 26 reads `23_annual_AC_channel_comparison_hourly.csv` and `26_IDA_hourly_mean_normalized.csv` from `results/annual_audit/`; Step 28 checks fingerprints and will stop if its anticipated sources have changed. If a stage fails, do not manually modify upstream CSVs to force it to pass. Record the error, source fingerprints and differing output. Never apply the PVsyst weather-import one-hour shift again to `E_Grid`.

### Comparison semantics that must not change silently

1. RISE measured power: original ten-minute data, six valid records per full hourly interval.
2. Daylight: physical astronomical solar elevation > 0° at **measured interval start**.
3. Same **4,478** selected measured rows per system for both declared clock scenarios. The December 2020 selected matched cohort omits 31 December; do not replace the cohort by arbitrary `GTI > 0` hours.
4. Primary IDA: **hourly Table `Produced power` (`EMS/Pprod_log`)**, attributed to its preceding hour; do not substitute single-point `.prn` values or `inverter_o` without a separately labelled sensitivity.
5. PVsyst: `E_Grid` at its source interval semantics.
6. Power error and energy bias use **simulated minus measured**; paired `delta_RMSE` means **IDA minus PVsyst**.
7. No residual-based rejection of annual AC observations in Step 28.
8. `fixed_CET_hypothesis` is the author-selected manuscript scenario (fixed-CET model lookup versus Swedish CET/CEST measurement labels). `civil_unshifted` remains a preserved, scientifically consequential repository sensitivity, not a selected journal result. Original logger settings are not independently authenticated.
9. A 30-day moving-block bootstrap with 5,000 resamples describes conditional temporal sampling variability, **not** undocumented logger settings or other structural uncertainties.

## C. Shading reconstruction is a separate pipeline

The 2023 shading results must not be rebuilt from the annual power series. Read `docs/README_A3_SHADING_REBUILD.md`, `docs/README_C9_CLOCK_INTEGRATION.md` and `docs/Final_Shading_Audit_2026-10-27.md`. The source-specific correction scripts are:

```bash
python scripts/16_rebuild_A3_shading.py
python scripts/17_integrate_C9_shading_clock.py
```

These produce `derived_data/shading_analysis_final_A3_C9.csv` and diagnostic files; the original historical `derived_data/shading_analysis.csv` must remain untouched. The current figures and period-energy summaries are downstream of the audited shaded data, subject to their separate conventions. Before rerunning, inspect the original source paths and use a disposable clone to preserve the frozen baseline.

## D. What cannot presently be called reproduced

- The original `01–11` pipeline's AC power, monthly totals, sky index bins, original `05_*` paired intervals and earlier master workbook are **not** the Step 28 AC release. Running `scripts/02_run_analysis.py` does **not** produce Revision 2 annual AC RMSE.
- The source/effective irradiance variables are not demonstrated physically like-for-like and cannot independently validate transposition models.
- Weather-bin plots, monthly RMSE, weather-bin CI, seasonal/diurnal plots and combined measurement envelopes from the older generation require **separate audited recalculation using the Step 28 cohort** before being described as current Revision 2 evidence.
- The original RISE clock settings and the missing PVsyst source `.MET` import CSV/MEF cannot be reconstructed by selecting the clock alignment with the smallest RMSE.
- Software outputs do not prove the original PVsyst shading geometry, exact cell-bypass circuits, transient inverter behaviour, or independent measured shading-loss fractions.
- The GitHub source repository's availability of third-party measurements or proprietary simulation exports does not itself establish distribution rights.

## E. Release QA and recommended evidence

Run source-to-paired-cohort checks, sample/energy/checksum checks, both clock metrics, 30-day paired inference, and the A/C shading validations. Record a clean-clone Python/package environment, full commands, output SHA-256 fingerprints and a git clean-status check. Distinguish verified sample statistics from unverified original simulator/measurement settings.

See [RELEASE_READINESS.md](RELEASE_READINESS.md) for the remaining tasks and [REVISION2_RESULT_MAP.md](REVISION2_RESULT_MAP.md) for the per-file authority matrix.
