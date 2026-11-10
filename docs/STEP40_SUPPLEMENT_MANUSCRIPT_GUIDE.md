# Step 40 — Manuscript integration and reviewer-response guide

**Manuscript reference:** `Revision2_clean_20261110.pdf` (33 pages); page positions below may shift when the Word draft is edited. **Do not claim figures or tables were produced until Step 40 runs successfully and the plots have been visually checked.**

## Recommended placement

- **Methods, Section 3.3.1 (around page 13):** after the monthly energy RMSE definition and before the `k_t,tilt` stratification. Describe the seasons, clock-hour grouping, signed-error convention, common 4,478-hour cohort, and the 25–75th percentile residual bands.
- **Results and discussion, Section 4.1.1 (around page 20):** after the paragraph about monthly versus hourly aggregation and immediately **before** the Figure 3 discussion. Briefly compare winter/summer relative errors and note the seasonal ranking change under the alternate clock. Then refer to the daytime residual shapes without mechanistic attribution.
- **Supplement:** `Table S1a` and `Table S1b` (fixed-CET and civil-unshifted respectively), `Figure S1a` and `Figure S1b` (likewise). Avoid disturbing main-text Figure 4–6 numbering and Table 7–9 numbering.
- **Conclusion:** optionally add one sentence that seasonal and diurnal residuals reveal time-dependent errors, conditional on the clock scenario.

## Suggested Methods passage

> To examine seasonal and diurnal variation, the corrected annual hourly AC-power comparison was stratified by meteorological season (DJF, MAM, JJA and SON) and by the local clock hour at the start of each measured physical interval. Seasonal RMSE, CV(RMSE) and nMBE were calculated from the same paired 4,478-hour daylight cohort per system, using the measurement-referenced definitions given above. The diurnal analysis grouped the signed hourly AC-power residuals (simulated minus measured) by clock hour and summarized their mean and 25th–75th percentile range. These distributions represent variation across available observation days, rather than uncertainty in the mean. Both the working fixed-CET and unshifted civil-clock alignments were evaluated without additional exclusions.

## Supplementary table captions

**Table S1a.** Seasonal hourly AC-power validation for systems A–C under the working fixed-CET model-clock interpretation. Each entry is CV(RMSE) / nMBE (%), with positive nMBE denoting overestimation. The sample counts per system and model are 703 (winter), 1,310 (spring), 1,537 (summer) and 928 (autumn) paired daylight hours. The selected winter sample excludes 31 December 2020. Seasonal point estimates are descriptive; no within-season model-difference confidence intervals are reported.

**Table S1b.** Same as Table S1a under the alternative unshifted civil-clock interpretation, using the identical physical measured observations. The two scenarios reflect uncertainty in model-to-measurement clock matching rather than statistical resampling.

## Supplementary figure captions

**Figure S1a.** Composite diurnal hourly AC-power prediction errors (simulated minus measured) for (a) System A, (b) System B and (c) System C under the working fixed-CET model-clock interpretation. Lines show mean signed errors for IDA ICE and PVsyst; transparent bands show the 25th–75th percentiles of the errors across available observation days. Hours refer to the start of the matched measured interval in local clock time. Sample counts vary by hour due to daylight selection (33–364 observations per hour per system). Positive errors indicate overproduction. The bands are not confidence intervals, and the curves do not establish error mechanisms.

**Figure S1b.** Same as Figure S1a under the alternative unshifted civil-clock interpretation. The measured physical cohort is unchanged; only the model-to-measurement alignment differs. Note that vertical scales may differ between Figures S1a and S1b.

## Suggested main-text Results passage

> Seasonal performance differed substantially (Tables S1a–S1b). Under the working fixed-CET interpretation, IDA ICE had lower hourly CV(RMSE) than PVsyst in every season for all three systems. Relative errors were largest in winter, when mean measured power was low; for System A, winter CV(RMSE) was 58.8% for IDA ICE and 64.0% for PVsyst, compared with 13.6% and 26.2%, respectively, in summer. Because CV(RMSE) is normalized by the seasonal mean measured power, these percentages do not directly indicate the magnitude of absolute power errors. Under the alternative unshifted civil-clock interpretation, PVsyst had lower seasonal CV(RMSE) in spring, summer and autumn for all three systems, while the winter ranking was unchanged. This further highlights the clock sensitivity of tool comparisons.
>
> Composite diurnal residuals (Figures S1a–S1b) also varied by hour of day. For example, under the fixed-CET interpretation, System A PVsyst mean error shifted from approximately −220 W at the hour starting 08:00 to +86 W at 16:00, while IDA ICE errors at those hours were +33 W and −45 W, respectively. The observed within-hour distributions indicate that temporal averaging can conceal signed error cancellation. The available data do not establish whether the diurnal patterns are caused by temperature lag, solar geometry, inverter constraints or other mechanisms.

## Response-letter update: Reviewer 7 Results R3/R4

- **R3 — diurnal curves:** cite Figures S1a/S1b and explain that mean error and interquartile bands were calculated **from Step 28 hourly rows** and cross-checked against Step 29. Emphasize that variations are not assigned to thermal or electrical causation without supporting measurements. Avoid claiming that error bands are statistical confidence intervals.
- **R4 — seasonal nMBE/CV(RMSE):** cite Tables S1a/S1b, explicit season samples, missing 31 December 2020, and both clock scenarios. Clarify that the changing ranking is due to alignment assumptions and does not isolate weather, snow or thermal causes.
- **Avoid overclaiming:** Supplemental results are *descriptive* and retain both clock scenarios. Do not claim a formal irradiance-matched causal experiment, seasonal statistical significance, independent logger validation, or quantified shadow-specific losses.
