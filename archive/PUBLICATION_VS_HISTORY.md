# Publication outputs versus archived methodological history

**Archive navigation, 17 November 2026.** For current manuscript numbers start at [Publication-results index](../docs/PUBLICATION_RESULTS.md), not in this directory.

## Preserved pre-cleanup snapshot

The branch [`archive/pre-publication-curation-20261117`](https://github.com/mary-032/pv-validation-idaice-pvsyst/tree/archive/pre-publication-curation-20261117) preserves commit `74dc2699940d0161c3872d6d5ec2a779f150515d`, immediately before the reader-facing publication-output curation. This branch is a historical snapshot, **not** a publication release, Git tag or alternative source of truth for the revised manuscript.

## Physically archived former Figure 3

The old weather-bin output is retained **byte-for-byte** under [`archive/legacy_figure3/`](legacy_figure3/):

- `Figure3_combined_weather_bins.pdf`
- `Figure3_combined_weather_bins.png`
- `Figure3_combined_weather_bins.svg`
- `Figure3_weather_bins_recomputed.csv`

These were outputs of the earlier `01–11` analysis and must **not** be used for the new Figure 3. The old `scripts/03_make_figure3_combined.py` remains in `scripts/` for historical reproduction and, if deliberately run, may recreate output files under their *old* `results/` paths. Do not commit those regenerated historical results as current sources.

## Annual clock-alignment development

- **Selected publication alignment:** measured Swedish CET/CEST timestamps matched to fixed-CET model indices; see [decision](../docs/REVISION2_CLOCK_CONVENTION_DECISION.md).
- **Retained diagnostic:** `civil_unshifted`, which is scientifically consequential but *not selected* for the manuscript. It is stored in the **generator-controlled** locations under `results/annual_audit/` and `results/revision2/` so that existing Steps 28, 29, 35 and 40 remain reproducible.
- **Alternative figures:** `results/revision2/35_Figure3_civil_unshifted_AOI_lt80_SENSITIVITY.*` and `results/revision2/40_supplement/Figure_S1b_diurnal_civil_unshifted.*`, as well as `Table_S1b_seasonal_civil_unshifted.*`, are **audit artifacts only**, never journal figures/tables.
- **Historical reports:** the dated [Step 38 Figure 3 history](../docs/REVISION2_FIGURE3_HISTORY.md), [Step 39 manuscript audit](../docs/REVISION2_MANUSCRIPT_CONSISTENCY_20261106.md), [Step 27 clock-provenance diagnostic](../results/annual_audit/27_CLOCK_PROVENANCE_EVIDENCE_2026-10-28.md), and [Step 28 source note](../results/annual_audit/28_annual_AC_release_candidate_note.md) reflect their original states. Their older *publication-presentation* recommendations are superseded by the author decision and publication index, but their data and limitations remain intact.

## What was deliberately not moved or deleted

- Source files, source-audit/clock scenarios and `28_*` cohort calculations.
- Step 29 monthly/seasonal/diurnal mixed-scenario CSVs and their deterministic checker.
- Step 35 and Step 40 mixed-scenario statistics, presentation images, manifests and test requirements.
- The independent 2023 System C shading timestamp checks.
- Original model exports and older `01–11` scientific calculation steps.

These files are intentionally retained in the **active computational provenance tree** rather than moved into `archive/`: moving or silently editing their paths would break regeneration, hash checks, and source traceability. "Archived" means **not selected for journal presentation**, not deleted, demonstrated erroneous, or rewritten from later knowledge.
