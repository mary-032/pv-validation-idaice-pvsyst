# Step 29 — Manuscript consistency audit after annual AC release-candidate commit

**Audit date:** 29 October 2026
**Repository:** `mary-032/pv-validation-idaice-pvsyst`
**Annual AC release-candidate commit:** `b7eb7a27aaebaa41a83836bb8ee4b592dae542d0`
**Frozen shading baseline:** `41b6904` (tagged `shading-a3c9-freeze-2026-10-27`)
**Manuscript inspected:** `Rynoson_et_al_June2026_Validation_IDAvsPVsyst_SUBMISSION.docx` (June submission draft, not necessarily the most recent local revision).
**Status:** Discrepancy register and proposed revisions only; no original manuscript, historical master table, or frozen shading data were modified.

## 1. Verified annual AC numbers — fixed-CET working primary interpretation

These values are from `results/annual_audit/26_annual_AC_all_systems_metrics.csv` and are reproduced in the Step 28 release candidate. `CVRMSE_pct` is reported as calculated in the committed workflow. All lines use **4,478 paired daylight hours per system**, a daylight mask of solar elevation > 0 at the **measured interval start**, and IDA ICE **hourly Table `produced_p` at the corresponding interval end**. Energy bias is `(simulated energy - measured energy) / measured energy × 100`.

| System | Model | Measured kWh | Simulated kWh | RMSE W | CV(RMSE) % | MBE W | Energy bias % | R² |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A/3 | IDA ICE hourly Table | 3648.541 | 3595.317 | 149.98 | 18.41 | -11.89 | -1.46 | 0.9745 |
| A/3 | PVsyst E_Grid | 3648.541 | 3420.252 | 252.46 | 30.99 | -50.98 | -6.26 | 0.9279 |
| B/8 | IDA ICE hourly Table | 4230.835 | 4381.266 | 242.51 | 25.67 | +33.59 | +3.56 | 0.9541 |
| B/8 | PVsyst E_Grid | 4230.835 | 4218.137 | 311.47 | 32.97 | -2.84 | -0.30 | 0.9242 |
| C/9 | IDA ICE hourly Table | 2809.808 | 3000.470 | 190.03 | 30.29 | +42.58 | +6.79 | 0.9417 |
| C/9 | PVsyst E_Grid | 2809.808 | 3103.015 | 245.00 | 39.05 | +65.48 | +10.44 | 0.9031 |

**Important interpretation:** Under the manuscript's stated 30% CV(RMSE) reference threshold, IDA ICE is below the threshold for A and B, slightly above for C; PVsyst is above for all three. This is a contextual ASHRAE calibration benchmark, not a proof that these PV predictions are accepted or rejected by ASHRAE. The old assertion that both tools meet the hourly criteria is unsupported by this revised cohort.

**Paired 30-day moving-block bootstrap:** IDA ICE minus PVsyst RMSE = A -102.48 W, 95% CI [-124.95,-73.58]; B -68.96 W [-96.18,-41.01]; C -54.97 W [-72.68,-36.00]. Holm-adjusted p values across the three primary AC comparisons are approximately 0.0012 each. This is conditional on the clock alignment and AC model-output definition; it does not quantify those structural uncertainties.

**Mandatory clock sensitivity:** Without the summer model correction (civil-unshifted lookup), hourly IDA ICE RMSEs are A 390.93 W, B 521.09 W, C 378.77 W versus PVsyst A 288.02 W, B 398.41 W, C 294.87 W. **All model rankings reverse**. The RISE GTI-solar-centroid diagnostic supports Swedish CET/CEST source labels, but original logger configuration is undocumented and the raw 10-minute files may have been regularized. Do not call fixed CET conclusively authenticated.

## 2. Required changes to the June submission manuscript

References below are to identifiable text/sections/tables in the June DOCX, not fixed Word page/line numbers. The manuscript may have changed since that version.

| Priority | Manuscript location | Current issue | Required editorial action |
|---|---|---|---|
| **Critical** | **Abstract** (paragraph beginning “This study aims”) | Quotes historic AC bias ranges of -2.77 to 4.16% for IDA ICE and -7.33 to 8.39% for PVsyst and implies comparable output without the clock caveat. | Replace annual AC quantities with release-candidate energy biases: IDA -1.46% to +6.79%; PVsyst -6.26% to +10.44%. Distinguish annual AC from irradiance and temperature findings; explicitly qualify the ranking by clock assumption. |
| **Critical** | **Materials and methods → Simulation cases and data processing** (paragraph beginning “All measured and simulated data were averaged”) | States night exclusion by `GTI == 0` and a median-based 2-standard-deviation outlier screen; the Step 28 AC cohort instead has six valid raw ten-minute readings per hour, solar elevation >0 at interval **start**, and **no residual-based exclusions documented in Step 26/28**. | Present **variable-specific** filters and AC interval definitions. Do not claim a median residual filter for the release-candidate AC cohort unless separately performed. State 4,478 paired hours/system and explain native IDA Table interval-end vs PVsyst source interval start. Do not retroactively change irradiance, temperature or shading filters. |
| **Critical** | **Table 6: PV AC power generation** | Current nMBE, CVRMSE and monthly RMSE[kWh/kWp] come from the earlier annual workflow. The numerical and measurement basis no longer agree with Step 28. | Replace with an **hourly power table** including RMSE[W], CV(RMSE)[%], MBE[W], energy bias[%] and optionally R² using the exact values above. Do **not** put the new hourly RMSE[W] under the historic monthly RMSE[kWh/kWp] heading. If monthly metric is retained, recompute it from the updated hour-matched data on an explicitly defined calendar and DC kWp denominator. |
| **Critical** | **Results → Unshaded PV modeling** (paragraph beginning “For the evaluation of PV simulation accuracy”) | Says System B is underestimated annually and System C is underestimated; Step 28 has **B +3.56% and C +6.79%** IDA energy biases under the fixed-CET primary. | Rewrite power-bias and relative performance discussion. A specific inverter/optimizer issue may remain relevant, but the explanation that annual System B underproduction proves this issue cannot be retained verbatim. |
| **Critical** | **Conclusion** (paragraph beginning “For PV AC power production”) | Claims both models meet hourly ASHRAE criteria; IDA wins two out of three and has a negative System C bias. None matches the revised primary hourly series. | Replace with model-by-system values and the conditional clock sensitivity. State which calculated CV(RMSE) values cross the 30% reference, and avoid a categorical software superiority conclusion. |
| **High** | **Results → Sky conditions, Figure 3 and its interpretation** | Sky-bin CVRMSE/nMBE and statements of systematic negative System C bias are based on old analysis; latest normalized hourly cohort differs. | Recalculate cloud-bin statistics and re-render Figure 3 using **exactly** the Step 28 primary cohort and a documented tilted clearness index source. Retain old plot only as historical analysis, not as the revised primary. The current Step 28 release does **not** provide these recomputed bins. |
| **High** | **Results → Monthly RMSE literature comparison** | Text claims range 2.38 to 11.28 kWh/kWp based on a previous monthly aggregate workflow and describes normalization by installed **AC power** elsewhere. | Recompute monthly aggregate RMSE from revised primary data. Ensure the denominator is installed **DC peak capacity (kWp)** and define whether there are 12 monthly error values, which calendar months, and how night/daylight selection enters. Until calculated, omit the historical range and any direct literature claim that relies on it. |
| **High** | **Statistical analysis methods** | Manuscript's nMBE/RE equations may use different denominators from Step 26's `(sum predicted - sum measured)/sum measured`. | Verify equations and sign convention before labeling the reported **energy bias** as `nMBE` or `RE`. The audited output column is `energy_bias_pct`, not proof of correspondence to the June formulas. Clarify that the 30-day paired-bootstrap CIs are for *RMSE difference*, not for mean bias or unmodeled clock uncertainty. |
| **High** | **Results and discussion → Full shaded-period Table 9** | Old shaded-period energy values do not fully match the frozen shading audit: A -0.1% vs -0.461% IDA / -0.030% PVsyst; B -7.5% vs -4.990% IDA; B PV -1.912%; C +3.946% / +8.011%. | Update Table 9 separately from the **frozen shading** outputs. Preserve 1,199 valid hours for A, 1,200 for B and C. Disclose the 10 May 2023 A pole relocation and inferred System C clock-reindexed sensitivity; the latter is not independently authenticated. Do not recompute frozen shading sources. |
| **Medium** | **Shading figure/table cross-references** | Narrative refers to “Figure 3 through Figure 5” when shading images are captioned Figures 4–6, and cites Table 6/7 although the day tables are Tables 7/8. | Repair cross-references after numerical updates. Inspect day figures/captions, especially the 2020 vs 2023 dates and A relocation, against the frozen outputs. |
| **Medium** | **Irradiance Table 4, temperature Table 5, related paragraphs and Abstract** | These are **not** recalculated by the AC release-candidate script and may use the historical measurement cohort and outlier logic. | Leave untouched provisionally, but conduct a **separate consistency review** before claiming the entire annual dataset was reprocessed in the same way. Do not silently replace irradiance or temperature numbers with AC figures. |
| **Medium** | **Weather input provenance / time alignment** | Manuscript says both tools used hourly historic weather; lacks explanation of the synthetic simulation-year index, model standard time, the PVsyst `.MET` imported `HourShift = -1`, and measured CET/CEST interpretation. | Add a concise timing/provenance subsection, clearly distinguishing calendar-year labels from the physically matched June 2020–May 2021 measurement period. Note missing original logger and PVsyst import CSV/MEF. Do not apply a second PVsyst `HourShift`. |
| **Medium** | **Software output definition** | “Simulated AC power” hides a material IDA ICE distinction. | Name IDA ICE `Electrical system → Produced power` (`EMS/Pprod_log`) from the **hourly Table** (preceding-hour average) as the provisional primary comparison to the RISE AC meter; `inverter_o` (`Invert_1/Pnet`) is a separate sensitivity and not interchangeable. |

## 3. Suggested replacement annual AC Results paragraph (conditional, for author review)

> For the annual unshaded AC-power comparison, hourly values were reconstructed from six valid 10-minute measurements and compared with the IDA ICE electrical-system hourly Table output and PVsyst grid-energy output on a shared cohort of 4,478 daylight hours per system. Using the working alignment in which model time remains on Central European standard time and the reconstructed measurement timestamps follow CET/CEST, IDA ICE produced hourly RMSEs of 150.0, 242.5 and 190.0 W for Systems A, B and C, compared with 252.5, 311.5 and 245.0 W for PVsyst. Paired 30-day block-bootstrap confidence intervals for the IDA ICE minus PVsyst RMSE differences excluded zero in all three systems under this alignment. Annual energy biases were -1.46%, +3.56% and +6.79% for IDA ICE, and -6.26%, -0.30% and +10.44% for PVsyst. Crucially, the relative RMSE ranking reverses under an alternative unshifted civil-clock interpretation. The preferred alignment is supported by model weather settings and an independent solar-noon check on measured irradiance, but original RISE logger timestamp documentation was unavailable; therefore comparative accuracy claims are conditional on the stated clock interpretation.

**The paragraph above is not a substitute for a completed monthly analysis, sky-bin recomputation, or a fully revised Table 6.**

## 4. Suggested Methods addendum (conditional, for author review)

> Annual AC power was reconstructed by averaging six valid ten-minute power observations per hour. Records were retained for intervals with solar elevation greater than zero at the measured interval start; this selection yielded 4,478 paired hours for each system. IDA ICE's `Electrical system — Produced power` was exported from the results **Table** at hourly resolution, which represents an average over the preceding interval; each Table record was consequently assigned to the corresponding interval rather than joined by an identical start-label index. PVsyst `E_Grid` output was taken from the hourly export, with the meteorological import's recorded `HourShift` not reapplied. The preferred working clock comparison assumes the model's standard-time sequence and measurement timestamps following CET/CEST. Because logger configuration could not be independently obtained, the alternative unshifted lookup was reported as a sensitivity case. The analysis did not infer the clock offset by maximizing model-to-measurement agreement.

**Clarify actual raw-sample timestamp labeling and averaging further in Methods before submission; documented source consistency alone does not prove native logger semantics.**

## 5. Freeze and workflow boundaries

- **GitHub confirmed:** `b7eb7a27aaebaa41a83836bb8ee4b592dae542d0` adds 27 annual-audit files; base shading commit `41b6904` is unchanged.
- Annual AC status is **release candidate**, not fully final, because logger time basis, native hourly-mean interpretation, and system AC metering boundary are not independently authenticated.
- The **shading** freeze remains separate and its original `inverter_o` output and C9 reindex sensitivity must not be silently replaced by the annual `produced_p` convention.
- To complete a defensible manuscript revision, calculate the monthly RMSE[kWh/kWp], rebuild sky-bin Figure 3/statistics, audit the irradiance/temperature cohorts and cross-references, then integrate the frozen shading Table 9. No new native IDA ICE simulations are indicated by this discrepancy register.

## Primary evidence

1. GitHub annual release-candidate commit `b7eb7a2`, especially `results/annual_audit/26_annual_AC_all_systems_metrics.csv`, `26_annual_AC_all_systems_paired_CI30d.csv`, `28_annual_AC_release_candidate_note.md`, and `28_annual_AC_release_candidate_manifest.json`.
2. `Rynoson_et_al_June2026_Validation_IDAvsPVsyst_SUBMISSION.docx`: Abstract; Methods/Statistical analysis; Tables 4–9; Figure 3; unshaded/shaded Results; Conclusions.
3. Separate frozen shading audit `Final_Shading_Audit_2026-10-27_UPDATED.md` and frozen shading commit `41b6904`.
