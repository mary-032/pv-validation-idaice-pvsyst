# Early annual AC provenance: historical Steps 18–25

**Prepared 5 November 2026. Scientific status: historical source diagnostic, NOT an alternative Revision 2 result generation.**

This document describes a limited, publication-oriented curation of local October 2026 provenance audits. The underlying scripts and source reports can remain on the author's machine. The safe aggregate-only snapshot is in [`results/revision2/provenance/`](../results/revision2/provenance/). Its aggregator is [`scripts/36_curate_early_provenance.py`](../scripts/36_curate_early_provenance.py).

## Result hierarchy and non-substitution rule

The working Revision 2 AC reference is **Step 28** (`results/annual_audit/28_*`, hourly electrical-system Table *Produced power* and PVsyst `E_Grid`, paired 4,478 daylight hours/system, fixed-CET clock working hypothesis plus civil-unshifted sensitivity). **Step 29** (`results/revision2/29_*`) supplies the monthly/seasonal/diurnal aggregation; **Step 35** (`results/revision2/35_*`) supplies revised sky-bin Figure 3. These are provisional and not a final frozen publication release. The original logger clock has not been independently authenticated, and 31 December 2020 has no selected matched daylight observations.

Steps 18–25 document *how the corrected quantity was selected*. Step 18/21 **sampled** IDA ICE `produced_p` is not Step 28's **hourly Table** power. For System A under the fixed-CET working hypothesis, historical sampled-IDA RMSE was **249.50 W**, versus **149.98 W** for the end-aligned Table. PVsyst RMSE was **252.46 W** in both those corresponding comparisons. These values must never be swapped into a common confidence-interval table: the Step 18 bootstrap intervals and Step 25 resampling are not identical, even when point estimates agree.

## Verification and data boundaries

| Step | Evidence preserved in the *curated* snapshot | Interpretation |
|---|---|---|
| 18 | Three historical sampled-AC comparison targets | Old IDA sampled channel; initial ``approved`` filename is a historical name, **not current approval** |
| 19 | 17 native PVsyst files discovered in Step 18, 16 metadata records with matching hashes in Step 19 | Native project/variant to export linkage **unverified**; all 16 historical `Version` fields were `[unexpected]` and **no software version is inferred** |
| 20 | Three systems with 52,560 original 10-minute rows each; 36 diagnostic alignment candidates per system | RMSE minimization does not independently authenticate logger or simulation clocks |
| 22 | Sampled IDA `produced_p` native-to-workbook agreement across 8,736 hours; PVsyst finite-pair unit checks | Does **not** verify the hourly Table channel or unit equivalence for excluded/nonfinite pairs |
| 24 | System A: 8,736 consecutive Table hour indices; max 0.05 W difference against the adjacent saved-hour endpoint mean | Does **not** establish original finer-than-hourly integration; the displayed DST clock is not the join key |
| 25 | Selected System A sampled / properly end-aligned Table / PVsyst aggregate metrics under both clocks and end-aligned Table 30-day paired confidence intervals | A-only predecessor to Step 26 and Step 28; same-index Table comparator excluded from public aggregate but preserved in the original local audit |

Step 19 variant comments about tilt/azimuth and project-selected weather are **not** proof of the historical Excel simulation run configuration. The original source `.PRJ`, `.VC*`, `.MET`, `.PAN`, `.GIM` files and Step 18 verbatim excerpts were **not** included. Source weather site coordinates differ slightly from the analytical solar-geometry coordinates; no replacement or correction has been inferred.

## Source handling and publication gate

The curator **reads** twelve local historical CSVs from `results/annual_audit/`, then **writes only compact aggregates** into `results/revision2/provenance/`. It does not update, stage, delete, or recompute the original untracked audits; it never publishes 8,736-row Table traces or paired 4,478-row power series. The source SHA-256 hashes, the exact output hashes, and a `source_release_permissions_confirmed: false` flag are recorded in `36_curation_manifest.json`.

This technical screening is **not permission** to redistribute source-derived data. The author/data owners must approve releasing numerical aggregates if applicable; published files should remain a *draft PR* until those rights are clear. Source Excel files, native PVsyst objects, original operator comments, and raw 10-minute observations remain out of this package.

## Reproduction and checks

With the twelve historical local input CSVs available:

```powershell
& .\.venv313\Scripts\python.exe scripts/36_curate_early_provenance.py
& .\.venv313\Scripts\python.exe scripts/36_curate_early_provenance.py --check-only
```

From a clean checkout containing only the selected public files (no historical source CSVs):

```powershell
& .\.venv313\Scripts\python.exe scripts/36_curate_early_provenance.py --verify-published
& .\.venv313\Scripts\python.exe -m unittest discover -s tests -p 'test_36*.py' -v
```

**Limits:** A clean clone can inspect public aggregates and reproduce hash consistency, but cannot independently regenerate the historical source workbooks/PRNs or authenticate simulation settings from the aggregate snapshot. Avoid suggesting otherwise.

## Open source-script maintenance (separate from these public snapshots)

`18_annual_preflight_and_pvsyst_inventory.py` still writes `18_approved_raw_reference_targets.csv` and some dated headings which were reasonable in the historical audit but must not be represented as current. `19_pvsyst_full_variant_provenance.py` casts the native `Version` token as numeric, producing `[unexpected]` in all 16 provided records. **Neither source script has been silently rewritten here**; original audits are left exactly as supplied. Future maintenance should rename Step 18 headings and replace or omit the Step 19 `Version` parser, then rebuild and re-review the original output files without changing previously frozen numbers. Step 36 deliberately omits misleading Version data from its public results.

For the current source-of-truth map and remaining release blockers, see [Revision 2 result map](REVISION2_RESULT_MAP.md), [Revision 2 reproducibility](REVISION2_REPRODUCIBILITY.md) and [release readiness](RELEASE_READINESS.md).
