# Revision 2 — Adopted clock convention and archived alignment sensitivity

**Author decision:** 12 November 2026  
**Status:** Temporal convention adopted for the revised manuscript; not an independent authentication of original logger hardware settings.  
**Scope:** 2020–2021 unshaded annual AC-power comparison, manuscript Table 6 and Figure 3, supplementary Table S1 and Figure S1. The separate 2023 shaded campaign is unaffected.

## 1. Temporal convention selected for the manuscript

The authors interpret timestamps in the supplied RISE measured data as **Swedish local civil time**: CET (UTC+1) during standard time and CEST (UTC+2) during daylight-saving time. To match the same physical hourly intervals, the simulation-output hour indices are interpreted on a **fixed-CET (UTC+1) model lookup basis**. The summer-time period therefore requires the one-hour difference in *model-to-measurement matching*; no additional shift is applied to the original observations or to an already corrected PVsyst weather import.

The analysis scenario identifier **`fixed_CET_hypothesis`** refers to the **model lookup clock**, *not* to a measurement logger using fixed CET year-round. This identifier and the source filenames are preserved to avoid breaking reproducibility and source references.

## 2. Evidence, choice, and limits

The convention reflects the authors' understanding of the supplied Swedish civil-time measurement labels and the existing model time-base information. The Step 27 independent GTI-centroid diagnostic supports that interpretation: during the CEST period (210 days), the mean measured irradiance centroid was **13.107 local hours**, compared with the **13.122-hour** expected astronomical noon in Swedish civil time (approximately **−0.9 minutes** difference). If those same labels instead represented fixed CET all year, expected summer solar noon would be about **12.122 hours**, nearly **59.1 minutes** earlier than the measured centroid.

This check is **consistent with** civil-time labels; it does not authenticate the original logger configuration, establish whether export transformations occurred, or prove that every recorded measurement channel had identical clock handling. Original logger configuration records were not available.

The choice is based on the adopted time convention and the independent irradiance-timing evidence, **not on minimizing AC-power RMSE or selecting the alignment that favours one tool**. The article's numerical results and paired bootstrap intervals remain conditional on this time-base interpretation.

See [Step 27 clock evidence](../results/annual_audit/27_CLOCK_PROVENANCE_EVIDENCE_2026-10-28.md), [Step 28 release-candidate note](../results/annual_audit/28_annual_AC_release_candidate_note.md), and the [Revision 2 result map](REVISION2_RESULT_MAP.md).

## 3. Why the alternative is retained but not submitted

During analysis development, the authors also calculated `civil_unshifted`, matching the **same physical measured records** to model outputs without the summer-time lookup adjustment. That alternative reverses the annual hourly-RMSE tool ranking for systems A–C.

It remains archived because it:
1. Records how substantially timestamp interpretation can affect comparative hourly errors.
2. Preserves the original methodological development and statistical record without rewriting results after a manuscript decision.
3. Permits researchers and reviewers to reproduce or inspect both scenarios with the same measured cohort.

This is a valid **computational sensitivity**, not a calculation shown to be erroneous or statistically rejected. Nevertheless, it is **not selected for the manuscript or its supplementary tables/figures**, because it does not represent the authors' adopted model-to-measurement time convention. Full repository verification should continue to check both scenarios, their shared measured observations and their generated aggregate statistics.

## 4. Source-of-truth map for manuscript outputs

| Journal result | Selected computational source | Archived alternative |
| --- | --- | --- |
| Annual AC power and confidence intervals, Table 6 | `results/annual_audit/28_annual_AC_primary_fixed_CET.csv`; `28_annual_AC_primary_and_sensitivity_metrics.csv` filtered to `fixed_CET_hypothesis`; `28_annual_AC_primary_CI30d.csv` | `28_annual_AC_sensitivity_civil_unshifted.csv` and alternative metrics rows |
| Monthly and seasonal validation | `results/revision2/29_*_AC.csv` filtered to `fixed_CET_hypothesis` | Same aggregate files, alternative rows |
| Irradiance-index Figure 3 | `results/revision2/35_Figure3_fixed_CET_AOI_lt80_CANDIDATE.*` and `35_Figure3_primary_source_statistics.csv` | `35_Figure3_civil_unshifted_AOI_lt80_SENSITIVITY.*` |
| Supplementary **Table S1** | `results/revision2/40_supplement/Table_S1a_seasonal_fixed_CET_hypothesis.*` | `Table_S1b_seasonal_civil_unshifted.*` |
| Supplementary **Figure S1** | `results/revision2/40_supplement/Figure_S1a_diurnal_fixed_CET_hypothesis.*` | `Figure_S1b_diurnal_civil_unshifted.*` |

The source filenames ending in `S1a` are deliberately unchanged even though the journal supplement calls these **Table S1** and **Figure S1**. Existing scripts, tests, output manifests, source hashes and historical file references must not be disrupted by an editorial presentation decision.

## 5. Qualifications and unchanged analyses

- The original RISE logger's configuration remains **not independently verified**. The selected convention is an author interpretation supported by the supplied timestamp behaviour.
- The 30-day paired moving-block bootstrap confidence intervals describe sampling variability **within the adopted alignment**. They do not include clock-convention uncertainty or independently establish hardware time settings.
- The 4,478-hour annual common matched cohort, 3,593-hour Figure 3 AOI-filtered cohort, all original figures, statistics, code, CSVs and manifests remain unchanged by this *documentation-only* decision.
- The inferred 2023 **System C shading** measurement-time reindexing is a different experiment and separate uncertainty. Its as-recorded sensitivity remains part of the shading audit.
- The DJF/MAM/JJA/SON seasonal groupings are **conventional descriptive calendar-month choices**, not observed local meteorological season onset/ends. Alternative month boundaries have not been evaluated.
- Final author approval, original-file access and redistribution permissions are distinct publication-release gates; this record does not certify them.

## 6. Historical audit status

Older Step 23/26/27/28 reports and the dated Step 38/39 manuscript audits document contemporaneous evidence and recommendations. This author decision supersedes their **recommendations on journal presentation** where they called for reporting both clock scenarios, but **does not alter their results or underlying evidence**.

For current use, see the [Revision 2 reproducibility guide](REVISION2_REPRODUCIBILITY.md), [Step 35 documentation](../results/revision2/README_STEP35.md), [Step 40 documentation](README_STEP40_SEASONAL_DIURNAL.md), and [release-readiness checklist](RELEASE_READINESS.md).
