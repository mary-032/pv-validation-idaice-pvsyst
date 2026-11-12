# Step 35 — Revision 2 tilted irradiance-index diagnostics and Figure 3

> **Journal selection (12 November 2026):** Figure 3 uses `fixed_CET_hypothesis` with AOI < 80°, meaning Swedish CET/CEST measurement labels matched to fixed-CET model intervals. The `civil_unshifted` figure remains an archived diagnostic, **not** a second submitted figure. Original logger settings remain independently unauthenticated. See [clock decision](../../docs/REVISION2_CLOCK_CONVENTION_DECISION.md).

**Prepared 5 November 2026. Candidate / not a final manuscript release.**

This is a **self-contained replacement for the Step 31 + Step 34 numerical/plotting chain**. Steps 30–34 in a researcher's older working tree are retained as historical diagnostics; they must not be silently overwritten. Step 35 reads the **committed Step 28** hourly measured/simulation reference, original documented Python canonical **geometry only**, and the repository configuration. It does not read any Step 30/31 intermediate file and it does not use their historical measured AC or GTI values.

## Reproduction

From project root:

```powershell
python scripts/35_rebuild_revision2_sky_bins.py
python scripts/35_rebuild_revision2_sky_bins.py --check-only
python -m unittest discover -s tests -p "test_35*.py" -v
```

All outputs are written under `results/revision2/` and named `35_*`. `--check-only` **does not rewrite anything** and independently recalculates the data source and compares all CSV cells against the committed outputs. It needs `numpy`, `pandas`, and the original committed `derived_data/annual_unshaded_analysis.csv`, `config.json`, and both Step 28 hourly releases. Rendering the PNG/PDF/SVG additionally needs `matplotlib`; image bytes can differ across software/font versions even when numerical data agree. The GitHub Actions check is intended as a separate cross-environment test, not proof that the original simulator could be rerun.

## Scientific methods — exact cohort and definitions

The full AC-power reference has **4,478 selected astronomical-daylight hourly intervals for each system**, with six original RISE ten-minute AC observations per interval. The two scenarios (`fixed_CET_hypothesis` and `civil_unshifted`) use *identical physical measured rows* and the same GTI observations, but differ in model-clock matching. This is a structural scientific sensitivity and **the clock interpretation is not independently authenticated**.

The sky index is `kt_tilt = GTI_measured_Wm2 / Eext_tilt_Wm2`. The numerator is the **reconstructed original RISE measured global tilted irradiance** from Step 28. The denominator uses only `Eext_tilt_Wm2`, and the AOI uses only `AOI_deg`, from `derived_data/annual_unshaded_analysis.csv` — the documented azimuth-aware solar geometry originally calculated with `pvlib` on *physical* June 2020–May 2021 clock dates. Its synthetic-year timestamp is explicitly mapped back to those physical dates. **Neither historical simulated power nor the legacy GTI series is used**. This is a replication of the *documented Python canonical geometry convention*, **not** authentication of the older MATLAB `TT_IDA.Eextt` field.

The **working candidate Figure 3** uses `Eext_tilt > 0` and `AOI < 80°`; it retains **3,593 hours/system**. Without the AOI filter, `Eext_tilt > 0` retains **3,932 hours/system**. The `Eext > 100 W/m² and AOI < 80°` selection is also reported as a sensitivity (equivalent to `Eext > 0 and AOI < 80°` for this particular cohort). No residual-based power exclusions are applied and no source observations are invented. Each system/bin uses exactly the same hours for IDA ICE and PVsyst. Bin limits are `[0,0.2)`, `[0.2,0.4)`, `[0.4,0.6)`, `[0.6,0.75)`, `[0.75,∞)`.

**Index regimes are NOT observed cloud-cover categories.** GTI includes diffuse and reflected components, whereas the extraterrestrial denominator is beam projection, so high ratios are possible at grazing angles. Bin labels on the figure are numerical index ranges to avoid overstating ground-truth sky classifications.

All statistical errors use `simulated − measured`, consistent with Revision 2 manuscript Equations 3–5 (4 November 2026), including both `MBE_W` and `nMBE_pct`:

```text
residual_h    = P_model,h − P_measured,h [W]
RMSE_W        = sqrt(mean(residual_h^2))
MAE_W         = mean(abs(residual_h))
MBE_W         = mean(residual_h)
CVRMSE_pct    = 100 × RMSE_W / mean(P_measured_W)
nMBE_pct      = 100 × sum(residual_h) / sum(P_measured_W)
energy_bias_% = nMBE_pct for matched hourly records
```

The denominator is `n × mean(measured)` — **not** historical MATLAB's `(n−1) × mean(measured)`. Positive nMBE means overprediction. The older Step 31 `nMBE_measured_minus_sim_pct` had the **opposite sign** and an `n−1` denominator. The Step 35 values correct both differences; CV(RMSE), absolute RMSE/MAE, measured power, and sample counts remain numerically consistent with the Step 31 diagnostic.

## Output map

| Output | Role |
|---|---|
| `35_sky_bin_statistics_all_scenarios.csv` | **180 rows:** 2 clock scenarios × 3 systems × 3 geometry screens × 2 tools × 5 regimes, including counts, mean measured and predicted power, RMSE/MAE/MBE (W), CV(RMSE), nMBE and paired energy |
| `35_Figure3_primary_source_statistics.csv` | **30 rows** filtered from the 180-row table for the working figure; suitable as supplementary summary |
| `35_sky_bin_QC.csv` | **6 rows** covering cohort matching, AOI eligibility, undefined projection, date coverage and fraction of annual selected AC energy retained |
| `35_annual_AC_date_coverage.csv` | **1,095 rows**: the 365 calendar dates × 3 systems, showing selected AC coverage and the missing day |
| `35_Figure3_fixed_CET_AOI_lt80_CANDIDATE.*` | Compact paired CV(RMSE)/nMBE diagram in SVG, PNG and PDF formats |
| `35_Figure3_civil_unshifted_AOI_lt80_SENSITIVITY.*` | Archived alternative-alignment diagnostic; preserve for reproducibility, not selected for the manuscript/supplement |
| `35_Figure3_manifest.json` | Recomputed input hashes, definitions, output list and limitations |

All figure scripts use the **consistent historical MATLAB colour mapping**: **IDA ICE = green** (`#77AC30`), **PVsyst = blue** (`#0072BD`). This replaces the accidental reversal in the uploaded local Step 34 script. The figures are **candidates**, not author-approved final figures.

## Distinct physical dates and the missing 31 December 2020

The Step 28 source has 4,478 matched daylight hours but **364 distinct dates**, excluding physical **2020-12-31**. This date absence is identical across A/B/C and both clock scenarios. The preserved `scripts/01_build_canonical_data.py` source explains that the historical IDA model timestamps run from elapsed hour 1 through **8,736 → synthetic 2021-12-31 00:00**, while the PVsyst source spans 8,760 rows. The common IDA/model match therefore does not provide a full daylight series for **synthetic 31 December**, which maps to physical 31 December 2020. This is a **supported structural explanation of the absent comparison date**, not proof that RISE collected no data that day. Source simulation outputs for that day were not reconstructed; do not impute the absent intervals.

Consequences: **December 2020 and the reported 12-month energy errors cover a truncated matched cohort**, not complete all-hour calendar-month production. The comparison is still valid for its explicitly selected paired hours, but do not report it as complete-year generation without further evidence/qualification. If an additional model export for the missing day can ever be authenticated, it requires a new analysis version and regeneration of all dependent results.

## Interpretation, evidence and limitations

Within the selected fixed-CET/AOI-filtered cohort, IDA ICE has the lower within-bin CV(RMSE) in **14 of 15** system × bin comparisons. The highest-index System C bin favours PVsyst. Under the `civil_unshifted` scenario, the hourly ranking reverses broadly; statistical within-bin significance has **not** been tested. In the lowest-index System C bin, measured power averages about **132 W**, while RMSE is **176 W** (IDA ICE) and **209 W** (PVsyst). This explains why the corresponding CV(RMSE) can reach **133%/158%** without treating it as an error percentage of nameplate capacity.

The original RISE logger settings, native MATLAB `TT_IDA.Eextt`, PVsyst weather-import source inputs and complete source-model system boundaries are not independently verified. Both clock scenarios remain reproducible repository diagnostics, but the manuscript selects the CET/CEST-measurement-to-fixed-CET-model alignment (see [author decision](../../docs/REVISION2_CLOCK_CONVENTION_DECISION.md)). The `35_*` data remain a release candidate pending the final author sign-off on figures, captions and the manuscript; no shaded data, older annual masters or original measurements are altered.

**Selected publication caption guidance:** Figure 3 uses the fixed-CET-model/AOI<80° asset (IDA ICE green, PVsyst blue), with 3,593 paired selected hours per system. Define the five lower-inclusive tilted irradiance-index regimes and per-bin sample counts, explain that they are not independent cloud-cover observations, and state that positive nMBE means simulated overestimation. The alternative `civil_unshifted` Figure 3 is an archived sensitivity, not a manuscript figure; see the [clock decision](../../docs/REVISION2_CLOCK_CONVENTION_DECISION.md).
