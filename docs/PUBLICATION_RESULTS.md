# Revision 2 — publication-results index

**Curated 17 November 2026.** This is the **first stop for reproducing the tables and figures selected for the Results in Engineering manuscript**, not a claim of an independently audited final source release.

## Adopted clock and sample definition

The supplied RISE measured timestamps are interpreted as **Swedish local civil time: CET in winter and CEST in summer**. Simulation output intervals use a **fixed-CET model time base**. The series are matched on the same physical hourly interval, applying the one-hour summer-time model lookup when appropriate. The code identifier `fixed_CET_hypothesis` refers to the **model clock**, not to a measurement logger using fixed CET throughout the year.

The article uses **only this adopted alignment**. It has 4,478 matched astronomical-daylight hourly observations per system, with no residual-based exclusion. Figure 3 uses an additional AOI<80° criterion, leaving 3,593 observations per system. The adopted alignment is described in [the author decision](REVISION2_CLOCK_CONVENTION_DECISION.md) and the [full source reproducibility guide](REVISION2_REPRODUCIBILITY.md). The original physical logger configuration has not been independently authenticated.

## Submitted article and supplement — source of truth

| Journal result | Selected source file(s) | Script / important qualification |
| --- | --- | --- |
| **Table 6 — annual AC hourly power** | [Step 28 primary paired data](../results/annual_audit/28_annual_AC_primary_fixed_CET.csv), [primary rows of combined metrics](../results/annual_audit/28_annual_AC_primary_and_sensitivity_metrics.csv), [paired 30-day CIs](../results/annual_audit/28_annual_AC_primary_CI30d.csv) | Step 28; IDA ICE *Produced power* hourly mean (not sampled `.prn`), PVsyst `E_Grid`. Select `fixed_CET_hypothesis` rows. |
| **Table 6 — monthly energy RMSE** | [Step 29 monthly RMSE](../results/revision2/29_monthly_RMSE_AC.csv) and [monthly energy sums](../results/revision2/29_monthly_energy_AC.csv) | Step 29; 12 matched calendar-month sums normalized by installed DC peak (kWh/kWp); select `fixed_CET_hypothesis`. |
| **Figure 3 — tilted irradiance-index errors** | [Adopted plot PDF](../results/revision2/35_Figure3_fixed_CET_AOI_lt80_CANDIDATE.pdf), [30-row primary statistics](../results/revision2/35_Figure3_primary_source_statistics.csv), [plot/QC manifest](../results/revision2/35_Figure3_manifest.json) | Step 35; 3,593 selected hours/system; bins are **not** independently observed cloud-cover categories. |
| **Supplementary Table S1 — seasonal CV(RMSE)/nMBE** | [Step 40 source CSV](../results/revision2/40_supplement/Table_S1a_seasonal_fixed_CET_hypothesis.csv), [formatted source](../results/revision2/40_supplement/Table_S1a_seasonal_fixed_CET_hypothesis.md) | Step 40; repository label **S1a** is published as **S1**; DJF/MAM/JJA/SON are conventional month-based groups, not independently tested meteorological-season boundaries. |
| **Supplementary Figure S1 — composite diurnal residuals** | [Adopted plot PDF](../results/revision2/40_supplement/Figure_S1a_diurnal_fixed_CET_hypothesis.pdf), [hourly residual statistics](../results/revision2/40_supplement/Figure_S1_diurnal_source_statistics.csv) | Step 40; repository source label **S1a** is published as **S1**; 25–75% shading represents distributions, **not confidence intervals**. Select `fixed_CET_hypothesis` rows in the shared statistics CSV. |
| **Supplementary Table S2 — absolute irradiance-index errors** | [Step 35 primary source statistics](../results/revision2/35_Figure3_primary_source_statistics.csv) | Step 35; select `fixed_CET_hypothesis` and `Eext_positive_AOI_lt80`; report per-bin n, mean measured W, and each model's RMSE and MAE (W). |

### Numerical anchors (do not copy from legacy results)

| System | IDA ICE hourly RMSE (W) | PVsyst hourly RMSE (W) | 95% paired difference CI (W) | Monthly RMSE IDA / PVsyst (kWh/kWp) |
| --- | ---: | ---: | --- | --- |
| A | 149.98 | 252.46 | −124.95 to −73.58 | 4.17 / 7.15 |
| B | 242.51 | 311.47 | −96.18 to −41.01 | 4.00 / 2.41 |
| C | 190.03 | 245.00 | −72.68 to −36.00 | 7.87 / 9.80 |

All paired 95% intervals in this table exclude zero in favour of IDA ICE **within the adopted alignment**. The bootstrap does not establish the historical logger settings or propagate structural model/input uncertainty.

## Quick, read-only validation

From the repository root, with Python 3.11 or later; requires no third-party packages or simulation licences:

```bash
python scripts/41_verify_publication_outputs.py
```

This verifies Table 6's annual and monthly numbers, paired CIs, the Figure 3 AOI-filtered bin counts, selected Table S1 values, diurnal observation totals for Figure S1, and the source of Table S2. It **does not write or regenerate any file**. For a full re-computation and its independent limitations, follow [Revision 2 reproducibility](REVISION2_REPRODUCIBILITY.md) and the existing Step 29/35/40 CI checks.

## Historical calculations are not article outputs

The `civil_unshifted` alignment remains generated by Steps 28, 29, 35 and 40 for **historical reproducibility, not for manuscript presentation**. Its alternative Figure 3, S1b table, and S1b figure remain at their generator-controlled paths so that reproducibility tests and manifests remain valid. The alternative is **not demonstrated to be an incorrect computation**; the author-selected time convention is described above.

The **superseded original-generation Figure 3** and its old bin CSV were relocated byte-for-byte to [`archive/legacy_figure3/`](../archive/legacy_figure3/). Earlier `01–11` outputs and dated audit notes are historical even where retained in their original directories for script compatibility; see [archive index](../archive/PUBLICATION_VS_HISTORY.md).

A static **pre-curation snapshot branch** `archive/pre-publication-curation-20261117` points to commit `74dc2699940d0161c3872d6d5ec2a779f150515d`. It is a preservation branch, **not** a frozen scientific release tag. Readers should cite an actual reviewed commit rather than assume a continuously moving branch is immutable.

The 2023 System C **shading** measured-timestamp inference and its as-recorded sensitivity are separate from the annual CET/CEST convention and remain in the shading analysis.

**Important release limitation:** This is navigation and validation of the *committed* candidate outputs, not proof that original native simulator files, unpublished logger metadata, or redistribution permissions have been independently authenticated.
