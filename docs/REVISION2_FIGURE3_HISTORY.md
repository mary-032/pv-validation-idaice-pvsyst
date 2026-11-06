# Step 38 — Figure 3 development-history audit (Steps 30–34)

**Audit date:** 6 November 2026. **Status:** historical provenance *only*, not a manuscript release or a reconstruction of the original MATLAB Figure 3. The numerical reference for the present Revision 2 candidate remains **Step 35** (`scripts/35_rebuild_revision2_sky_bins.py`, `results/revision2/35_*`). This document corrects outdated historical statements that call Step 34 the selected figure.

## Scope and evidence

The author had eight untracked historical scripts/reports from Steps 30, 31, 32 and 34. All eight SHA-256 fingerprints from the author's PowerShell inventory were independently matched to the previously supplied local audit archive. Three untracked aggregate CSVs from that same archive were also fingerprinted and compared to **the exact Step 35 CSV bytes currently committed to `main`**. Step 38 performs a *read-only* validation of these inputs. It executes **none** of the historical scripts. The original files are not redistributed by this change.

The reproducible comparison is implemented in `scripts/38_audit_figure3_history.py`. Eleven expected historical input SHA-256 values are embedded in the checker to identify the exact historical snapshot. They are not evidence of the source simulation settings, logger clock, missing MATLAB `TT_IDA.Eextt`, or original data-distribution rights.

## Development chronology and substantive differences

| Stage | Source/method | Audit outcome | Scientific status |
|---|---|---|---|
| **30** | Reconstructed physical-hour *midpoint* NOAA solar geometry and an approximate extraterrestrial beam projection; measured Step 28 GTI and AC. Also generated separate monthly energy-error summaries. | 60 provisional sky-statistic rows; 3,844 sky-index-eligible hours/system/model (Eext>0). **All 60 bin counts differ** from Step 35's Eext-positive group; Step 35 has 3,932. The provisional bin errors are not directly comparable. | **Superseded provisional sky analysis.** Consult Step 29 for the separately rebuilt current monthly aggregates; do not substitute Step 30 sky figures. |
| **31** | Legacy canonical azimuth-aware geometry from the existing Python build, rejoined at *physical interval start*; same Step 28 measured GTI/AC, both clocks and three geometry filters. | **180/180 rows match Step 35** by `(scenario, system, selection, model, sky_bin)`. Counts identical; max absolute CV(RMSE) difference **4.9831 × 10⁻¹⁰ percentage points**. | Valid **historical diagnostic**; Step 35 reconstructs its definitive statistics directly from Steps 28 and canonical geometry, **not** from Step 31. |
| **32** | Rendered candidate figures from Step 31: fixed-CET + AOI<80°; fixed-CET without AOI filter; civil-unshifted + AOI<80°. IDA green, PVsyst blue. | **90/90 plotted-source rows match Step 35**, including identical counts; same maximum CV(RMSE) difference as Step 31. | Superseded **figure-selection history**, not a separate model run or original MATLAB reproduction. |
| **33** | Referenced in older `results/annual_audit/README.md` as a method-comparison CSV/note. | **No Step 33 files supplied** in the earlier archive or shown in the current local file inventory. | **Unavailable; cannot claim this intermediate is archived, audited or reproducible.** |
| **34** | Replotted the fixed-CET/AOI-filtered Step 31 rows with a sign flip for nMBE; compact side-by-side figure. | Source SHA-256 matches Step 31. **IDA blue and PVsyst green**, opposite Steps 32 and 35. The sign was flipped, but the old `n−1` normalisation was **not** fixed. | Superseded presentation. **Do not use the Step 34 image or its nMBE values as the current manuscript Figure 3.** |
| **35** | Independent source-to-output rebuild of the Step 28 cohort, original established geometry, primary fixed-CET/AOI<80°, and mandatory civil-clock sensitivity. | 180 rows across all scenarios/filters; 30 primary plot rows; **3,593 eligible hours/system** for primary selection. Uses simulated-minus-measured nMBE with denominator `n`. | **Current working Figure 3 candidate**, still conditional on unknown original logger clock and unverified historical MATLAB `Eextt`. Not final manuscript release. |

**Step 31/32 nMBE correction must include both operations.** Historical `nMBE_measured_minus_sim_pct` is calculated with `(n−1) × mean(measured)` in the denominator, while Step 35 uses `sum(measured) = n × mean(measured)` and the opposite sign:

\[
\mathrm{nMBE}_{35}=-\mathrm{nMBE}_{31/32}\frac{n-1}{n}.
\]

After applying both corrections, the maximum absolute residual against Step 35 is **4.9155 × 10⁻¹⁰ percentage points** across all 180 Step 31 rows and all 90 Step 32 rows. **Negating alone** leaves up to **0.080281 percentage points** (Step 31) and **0.079934 percentage points** (Step 32) of numerical difference. This has no effect on CV(RMSE), matching bin counts, or the selected hourly RMSE ranking.

**Important interpretation:** the tilted index `GTI_measured / Eext_tilt` is *not* an independently measured cloud-cover classification. `Eext_tilt` is a direct-beam plane projection; it can be zero under diffuse irradiance. Filtering `AOI<80°` alters the cohort and is a documented candidate choice, **not** a documented historical MATLAB filter. The working fixed-CET clock cannot be authenticated from the model error ranking; the `civil_unshifted` alternative must be reported where relevant.

## Historical file preservation and publication gate

- **Keep original `scripts/30_*`, `31_*`, `32_*`, `34_*` and `results/annual_audit/30_*` through `34_*` in their existing local historical location.** Do not run the old scripts in the approved checkout: they write into the legacy `results/annual_audit/` area and can change existing hash fingerprints.
- The original `results/annual_audit/README.md` predates Step 35, calls Step 34 selected, and references unavailable Step 33 files. Preserve it as historical evidence locally; **this document and the current Step 35 readme supersede that status**.
- Do **not** stage the raw hourly diagnostics, historical figures, source simulation assets, full source inventories, or large model export files merely to preserve provenance. Source-derived aggregates also require distribution-rights review before public release; this audit publishes no such historical data.
- No original 30–34 code or output is copied into this PR. Only the metadata audit script, its tests, and this interpretation document are intended for integration. The local historical archive is not equivalent to public clean-clone reproducibility.
- Step 30 monthly figures are historically documented, but the **current monthly summaries should be taken from Step 29**, which uses the approved Step 28 cohort. Do not infer equivalence from matching rounded values alone.

## Reproduce checks without historical source files (clean clone)

```powershell
& .\.venv313\Scripts\python.exe scripts/38_audit_figure3_history.py --verify-current
& .\.venv313\Scripts\python.exe -m unittest discover -s tests -p 'test_38*.py' -v
```

These check the committed Step 35 source-table identity and test the conversion and safety logic. **They do not rerun the historical analysis**.

## Reconcile against the author's local historical archive

```powershell
& .\.venv313\Scripts\python.exe scripts/38_audit_figure3_history.py --local-audit
```

The script checks all eleven historical fingerprints and verifies **all 180 Step 31 and 90 Step 32 pairs** against Step 35, as well as the Step 30 selection change and Step 34 palette. By default it writes **nothing**. To keep a private JSON report outside Git, add e.g. `--report-json "$env:TEMP\figure3_step38_audit.json"` (must not already exist). Any local historical fingerprint change is a **review stop**, not an invitation to overwrite old files to force agreement.

This audit establishes **numerical reconciliation of the available source snapshots**. It does not independently validate the PV simulations, original logger clock, the precise MATLAB extraterrestrial denominator or third-party redistribution rights.
