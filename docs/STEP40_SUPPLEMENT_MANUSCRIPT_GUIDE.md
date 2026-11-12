# Step 40 — Manuscript integration and reviewer-response guide

**Updated 12 November 2026:** The authors selected CET/CEST-labelled measured intervals matched to fixed-CET model output intervals for the revised article. This replaces an earlier editorial recommendation to include both clock scenarios. The alternative `civil_unshifted` remains calculated and reproducible in GitHub, but is **not selected for the journal supplement**. See [clock decision](REVISION2_CLOCK_CONVENTION_DECISION.md).

**Status:** Real-data Step 40 figures and tables have been generated, tested and visually checked. Reconfirm the article's final page and line numbers in the submission PDF, rather than using those of an earlier working draft.

## Selected supplement materials

| Journal item | Unchanged repository source | Description |
| --- | --- | --- |
| **Table S1** | `results/revision2/40_supplement/Table_S1a_seasonal_fixed_CET_hypothesis.csv` and `.md` | Seasonal hourly CV(RMSE) / nMBE for Systems A–C and both tools |
| **Figure S1** | `results/revision2/40_supplement/Figure_S1a_diurnal_fixed_CET_hypothesis.pdf` (also SVG/PNG) | Composite diurnal mean signed AC-power errors and 25th–75th percentile bands |

The files retain their original **S1a** names because they belong to the complete generated Step 40 output set. The **S1b** files are *archived model-clock sensitivities*, not errors, and are not selected as second supplement figures or tables.

## Manuscript placement and necessary qualifications

- **Section 3.3.1 (Methods):** describe the conventional DJF/MAM/JJA/SON calendar-month groups, their arbitrariness relative to local meteorological seasons, the selected 4,478 matched daylight hours per system, the adopted CET/CEST-to-fixed-CET matching, and grouping of hourly signed residuals by *local measured interval-start hour*.
- **Section 4.1.1 (Results):** refer only to **Table S1** and **Figure S1** when discussing seasonal errors and diurnal patterns. Avoid importing the alternative-clock model ranking from the repository into the article.
- **Conclusion:** describe the dependence of comparisons on metric, temporal aggregation and tested systems without claiming that descriptive seasonal or diurnal patterns prove an electrical or thermal error mechanism.
- **Reviewer 7 replies:** cite Table S1 and Figure S1 plus their manuscript sections and Step 40 provenance, not S1b. Keep the source-level uncertainty distinctions from the reproducibility documentation.

The month boundaries were selected for descriptive comparison and **do not necessarily represent observed Swedish seasonal transitions**. The analysis did not investigate the sensitivity of its seasonal statistics to alternative group boundaries.

## Suggested Methods passage

> To examine seasonal and diurnal variation, the corrected annual hourly AC-power comparison was stratified by conventional calendar seasons (DJF, MAM, JJA and SON) and by local civil-clock hour at the start of each measured interval. These month-based boundaries were selected for descriptive comparison; they do not necessarily coincide with the local onset and end of meteorological seasons, and alternative month groupings were not evaluated. Seasonal RMSE, CV(RMSE) and nMBE were calculated from the common selected 4,478-hour daylight cohort for each system. Mean signed residuals (simulated minus measured) and their 25th–75th percentile range were calculated by measured local hour across observation days. The percentile bands describe residual distributions, not confidence intervals. The journal comparisons use CET/CEST-labelled measurements aligned with fixed-CET simulation-model intervals and introduce no additional exclusions.

## Supplement captions

**Table S1.** Seasonal validation of hourly AC-power predictions for PV Systems A–C under the adopted alignment of Swedish CET/CEST measurements and fixed-CET model-output intervals. Values are CV(RMSE) / nMBE (%); positive nMBE indicates overestimation. The conventional seasons are DJF (winter), MAM (spring), JJA (summer), and SON (autumn), with 703, 1,310, 1,537 and 928 matched daylight hours per system, respectively. The selected winter dataset excludes 31 December 2020. Seasonal groupings are descriptive month-based choices; no separate seasonal bootstrap confidence intervals or sensitivity to other month boundaries are reported.

**Figure S1.** Composite diurnal hourly AC-power prediction errors (simulated minus measured) for (a) System A, (b) System B and (c) System C under the adopted CET/CEST measurement-to-fixed-CET model alignment. The green solid line indicates IDA ICE and blue dashed line PVsyst. Curves show mean errors grouped by local start hour of the measured interval; shaded bands give 25th–75th percentiles of individual hourly residuals across days. Positive error indicates overestimation. All three systems contribute 4,478 paired daylight hours overall, but the count varies by hour of day (33–364). Bands are residual distributions, **not** confidence intervals, and cannot establish the causes of error.

## Suggested Results interpretation

> Seasonal validation revealed large differences among conventional calendar seasons (Table S1). Under the adopted temporal alignment, IDA ICE had lower seasonal hourly CV(RMSE) than PVsyst in all four seasonal groupings for all three systems. In System A, winter CV(RMSE) was 58.8% for IDA ICE and 64.0% for PVsyst, compared with 13.6% and 26.2% in summer. CV(RMSE) uses each season's own mean measured power, which was low in winter; these percentages are not direct measures of absolute power errors. The calendar-month grouping is descriptive, not a test of physical seasonal mechanisms.

> Diurnal residuals also varied over the day (Figure S1). In System A, PVsyst's mean signed error changed from approximately −220 W in the hour beginning 08:00 to +86 W at 16:00; the corresponding IDA ICE errors were +33 W and −45 W. Aggregate annual or monthly errors can conceal hour-dependent cancellation. These descriptive profiles alone do not identify whether temperature, solar geometry, inverter constraints or other phenomena caused the errors.

## Reviewer-response guidance

- **Reviewer 7 Results R3 (diurnal):** cite Supplementary **Figure S1**, manuscript Methods/Results, `results/revision2/40_supplement/Figure_S1_diurnal_source_statistics.csv`, and `scripts/40_build_seasonal_diurnal_supplement.py`. Describe the residual percentile bands as distributions, not significance intervals.
- **Reviewer 7 Results R4 (seasonal):** cite Supplementary **Table S1**, season-specific counts, the missing 31 December 2020 and the conventional month-boundary qualification. Do not claim demonstrated causes related to snow, temperature or wind.
- The **alternative** `civil_unshifted` scenario remains in the repository and the scientific audit history. Do not claim it was erased, found erroneous or statistically rejected merely because it is not selected for journal presentation.
- The distinct **2023 System C shaded-series timestamp sensitivity** remains relevant and is not resolved by the annual CET/CEST convention selection.
