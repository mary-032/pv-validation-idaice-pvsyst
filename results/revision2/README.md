# Revision 2 AC aggregate diagnostics — Step 29

> **Journal selection (12 November 2026):** The authors use `fixed_CET_hypothesis` (CET/CEST-labelled measurements matched to fixed-CET model intervals). `civil_unshifted` and its results remain archived for complete repository reproduction, **not selected for the article/supplement**. See [clock decision](../../docs/REVISION2_CLOCK_CONVENTION_DECISION.md), [Step 35](README_STEP35.md) and [Step 40](../../docs/README_STEP40_SEASONAL_DIURNAL.md).

**Created:** 5 November 2026. **Updated:** 12 November 2026 (publication clock choice; Steps 35 and 40 now generated). **Status:** audited analytical outputs; final author and source-release approval remain outstanding. This directory contains versioned outputs from the corrected Step 28 annual AC paired series. Earlier monthly, original `05_*` and legacy Figure 3 calculations are preserved separately.

## Source, script and reproducibility

- **Single computation source:** `scripts/29_aggregate_revision2_annual_AC.py`.
- **Fixed-CET working reference:** `results/annual_audit/28_annual_AC_primary_fixed_CET.csv` (Git blob `904faf0e4b6ae17f576fa7d52ac785d5e6cd3dc3`).
- **Alternative clock:** `results/annual_audit/28_annual_AC_sensitivity_civil_unshifted.csv` (Git blob `ee17dd380e83c9e953b3992ae4e52d907e43e234`).
- **Annual point estimate benchmark:** `results/annual_audit/28_annual_AC_primary_and_sensitivity_metrics.csv`.
- **Inputs are original Step 28 reconstructed hourly paired rows**: measured RISE power, IDA ICE hourly electrical-system *Produced power Table*, PVsyst `E_Grid`. These new aggregates are **not** a replacement for raw-file or software-model reconstruction.
- **System DC capacities:** A 3.9 kWp, B 4.8 kWp, C 3.3 kWp.
- **No new outlier rejection, optimizer fitting, time offset selection or simulated output modification.**

Reproduce from the repository root:

```bash
python scripts/29_aggregate_revision2_annual_AC.py --check-only
# or to regenerate:
python scripts/29_aggregate_revision2_annual_AC.py
```

The built-in checks compare the exact selected measured timestamps and values across both clock hypotheses, verify six raw 10-minute samples per selected hour, require 4,478 unique intervals per system, verify 12 calendar months and four seasons, ensure each aggregate partitions the input, and reproduce all six Step 28 IDA/PVsyst annual RMSE pairs.

**Verification boundary:** these files were programmatically aggregated and checked against the Step 28 CSVs when prepared. A separate independent execution of the committed Python script in a clean clone and source-file signature check remains **open**. The script's `--check-only` mode is provided for that sign-off; it should not be described as independently executed until actually tested.

## Output register

| File | Content | Population |
|---|---|---|
| `29_monthly_energy_AC.csv` | Monthly measured/simulated AC energy, difference, hourly W-based RMSE/MAE/MBE and normalized statistics | 12 physical months × 3 systems × 2 models × 2 clocks = **144 rows** |
| `29_monthly_RMSE_AC.csv` | RMSE across the **12 monthly energy errors** in kWh and kWh/kWp | 3 systems × 2 models × 2 clocks = **12 rows** |
| `29_seasonal_AC.csv` | Hourly RMSE, MAE, MBE, CV(RMSE), nMBE, means, energy and bias by meteorological season | 4 seasons × 3 × 2 × 2 = **48 rows** |
| `29_diurnal_AC.csv` | Composite **interval-start local clock hour** reference, measured/simulated mean, count, hourly RMSE, MAE and MBE | Only hour bins with selected daylight data; **216 rows** total |
| `29_source_QC.csv` | Sample counts, 12-month/4-season partition checks, number of observed physical calendar days, measured energy, annual model RMSE | **6 rows** |

### Monthly energy RMSE: do not confuse with hourly power RMSE

For calendar month `m`, the monthly energy error is `ΔE_m = Σ_h(P_sim,h − P_meas,h)/1000` **kWh**, summing only the common Step 28 *selected daylight-hour cohort*. The published summary statistic here is

`RMSE_month[kWh] = sqrt( (1/12) × Σ_(m=1..12) ΔE_m² )`

and its specific equivalent divides by the system DC capacity in kWp. This reproduces the *definition*, not the old measured cohort, of the original MATLAB `Analysis_monthly_RMSE_kWh_kWp.m`. It is **not** `sqrt(mean(hourly power error²))`, and **not necessarily complete all-hour monthly generation energy**. Hours excluded upstream are not reinstated by aggregation. Changing either the cohort or the meaning of a month requires another explicitly named scenario.

### Seasonal and diurnal conventions

- Seasons use calendar **DJF** (December–February), **MAM**, **JJA**, **SON** with physical dates. This is a full year crossing 2020 and 2021, not one calendar-year index.
- Composite diurnal bins are defined by the **hour of the physical measured-interval start**, in the same local wall-clock labels as Step 28. They are **not** shifted to the model-clock hypothesis and cannot be treated as a solar-time-adjusted diurnal series.
- All biases here are `simulated − measured`. `CVRMSE_pct = RMSE_W / mean_measured_W × 100`; `nMBE_pct = MBE_W / mean_measured_W × 100`. The energy percentage bias is equivalent to nMBE for complete paired hourly intervals.
- The source contains **4,478** matched selected intervals per system, spread over **364 distinct physical dates**; **31 December 2020 has no selected interval in the Step 28 cohort**. This is an *observed property of the existing source selection*, **not evidence of the cause**. Before using the aggregates to make claims about whole-year completeness, audit why this date is absent from the selected cohort.
The original RISE logger clock cannot be independently authenticated; the authors selected CET/CEST-labelled measurements matched to fixed-CET simulation intervals for the article and retain `civil_unshifted` as an archived sensitivity. Temporal aggregation can hide substantial signed hourly errors. See the [clock decision](../../docs/REVISION2_CLOCK_CONVENTION_DECISION.md).

## Monthly energy RMSE — working fixed-CET hypothesis

| System | IDA ICE (kWh/kWp) | PVsyst (kWh/kWp) |
|---|---:|---:|
| A | 4.172 | 7.154 |
| B | 3.999 | 2.414 |
| C | 7.868 | 9.800 |

A model may yield smaller hourly power RMSE yet **larger monthly energy RMSE** because temporal summation changes the weight and cancellation of errors. System B is a clear example: IDA ICE's fixed-CET hourly RMSE (242.51 W) is below PVsyst's (311.47 W), but the twelve-month energy RMSE is higher in IDA ICE (3.999 vs 2.414 kWh/kWp). Do not interpret the two summary metrics as contradictory.

## Subsequent analyses and remaining release gates

The tilted irradiance-index Figure 3 was **recomputed in Step 35**, with the corrected azimuth-aware geometry and AOI screen (3,593 selected hours per system). Step 40 also generated and checked the seasonal tables and composite diurnal-error figures using Step 29 aggregates as cross-checks. The journal supplement selects Step 40's primary `S1a` sources as **Table S1** and **Figure S1**; the `S1b` sources are archived alignment sensitivities only. The earlier `Figure3_weather_bins_recomputed.csv` remains historical. No season- or hour-specific bootstrap inference is claimed. Final author manuscript approval, source provenance and publication-release gates remain outstanding.

The Git history, untouched original cohort and older canonical scripts preserve the full revision trail. See `docs/REVISION2_RESULT_MAP.md` and `docs/RELEASE_READINESS.md`.
