# Revision 2 publication release-readiness register

> **Phase 2 update (5 November 2026):** Source-derived provisional Step 29 monthly-energy RMSE, seasonal and diurnal statistics have been added in `results/revision2/` with a reproducible aggregation script and tests. Their independent execution and manuscript acceptance remain open. The older Figure 3 and `05_*` inferential files remain historical. A source-cohort coverage review is warranted: **31 December 2020 has no selected daylight hour** in the corrected Step 28 cohort; do not infer a missing-source cause without checking.


**Prepared:** 5 November 2026. **Status:** OPEN; no approval, DOI, merged change or final release is asserted.

This is a **work checklist**, not a report that every test below has passed. It separates actions that are safe to address in documentation from changes that require regenerated source-derived analyses or external verification.

## 1. Critical reproducibility blockers

- [ ] **Freeze the authoritative Revision 2 source snapshot:** record the checked Git commit, filenames, SHA-256s, scripts, Python version and dependency lock/requirements. Avoid silently mutating historical `01–11` generated outputs. Do not create a final data release tag before the author-approved manuscript and numerical cohort are fixed.
- [ ] **Clean-clone proof:** demonstrate that the Step 23 → Step 26 → Step 27 → Step 28 route can be run using the distributed source and normalized IDA hourly Table exports; capture full commands and checked output hashes. An available CSV does **not** by itself prove complete rerun from raw data.
- [ ] **Explain the missing inputs:** confirm exact original hourly IDA Table Excel exports (and fingerprints) and whether they can be redistributed; record the missing `Meteo_89_PD.csv` and `pvsyst Rise project.MEF` and the original RISE logger time metadata. Disclose reconstruction limits rather than inventing missing source files.
- [ ] **Clarify AC boundary:** retain `EMS/Pprod_log` hourly-Table primary, `inverter_o` / sampled power sensitivities, and the field AC meter boundary uncertainties. Check that every manuscript table and figure uses the declared output semantics.
- [ ] **Preserve both annual clock interpretations:** include `fixed_CET_hypothesis` and `civil_unshifted` for the same 4,478 physical selected records per system. The rankings reverse and neither the 30-day CIs nor the solar-noon diagnostic authenticates the original logger settings.
- [ ] **Create a consistent result namespace:** either generate `results/revision2/` from source scripts or maintain a reviewed manifest mapping each manuscript table to `annual_audit/28_*` and the separate shaded files. Make old `Table6_Power_recomputed.csv`, `05_*` and `PV_MASTER_RESULTS_CURRENT_PD.*` unambiguously **legacy**. Only rename/move with preserved scripts and updated references; documentation alone must not break old workflows.

## 2. Necessary scientific follow-through (not solved by relabelling files)

- [ ] **Recompute monthly RMSE from Step 28 annual AC** on documented physical months, calendar aggregation and **DC kWp** denominator, including sample/energy coverage. The old `Monthly_RMSE_recomputed.csv` is NOT Step 28-compatible.
- [ ] **Recompute weather-bin errors/Figure 3** from identical Step 28 annual AC rows, documented geometry/index/AOI filtering, bin counts, mean measured power, RMSE and MAE (W), CV(RMSE), nMBE, and necessary clock sensitivity. The current `Figure3_weather_bins_recomputed.csv` and `05_Weather_bin_CI.csv` are earlier-generation results.
- [ ] **Recompute seasonal and composite diurnal diagnostics** on the corrected hourly cohort if referenced in manuscript/reviewer replies, with hourly sample counts and non-causal interpretations.
- [ ] **Audit 30-day inferential and uncertainty overlays** against the Step 28 cohort before reusing historical `05_*`, `Table6_Power_uncertainty_CI30d.csv`, measurement uncertainty envelopes, Engerer2 or temporal-aggregation tables. Statistical intervals cannot capture unsupported structural timing/output interpretations.
- [ ] **Decide irradiance-result presentation:** physically non-equivalent IDA ICE/PVsyst effective channels must not be presented as an independent transposition model ranking. Either obtain comparable incident GTI outputs or label the old irradiance table as a non-like-for-like processing-chain/channel diagnostic.
- [ ] **Document temperature cohort and observation boundary:** measured module back-surface vs modelled cell/panel variables; distinguish the original `n` from corrected AC `n`. Avoid relative Celsius error as if physically meaningful.

## 3. Shading verification and manuscript alignment

- [ ] Show **System A pre-/post-move** energy errors, not only the nearly cancelling period total. Physical pole shift: 10 May 2023 ~13:10; mixed 13:00–14:00 interval excluded only for A.
- [ ] Report System C **as-recorded and inferred reindexed** measured-power scenarios together. The inferred time shift is not independently authenticated; use the **native** model output as baseline.
- [ ] If reviewers require **shadow-affected-hour** errors, define a reproducible geometry-based shadow-hour mask and calculate its statistics or explicitly state why such classification is not defensible with available source files. Daylight-wide RMSE is *not* a substitute.
- [ ] Confirm original PVsyst configuration files and geometries if available. Otherwise preserve the explicit limit that the original PVsyst shading geometries were not independently authenticated.
- [ ] Check the energy and figures against the frozen shading tag `shading-a3c9-freeze-2026-10-27`; confirm plot axes/captions use kW for instantaneous power, kWh for energy, and the correct 2023 dates.

## 4. Documentation, licensing and editorial checks

- [ ] Replace any claims in older readmes that the `01–11` analytical generation is the *final* Revision 2 annual AC reference; keep prior material as historical and explain why its metrics differ.
- [ ] Update the detailed reproducibility, source/data and script docs to link to `docs/REVISION2_RESULT_MAP.md`, with **explicit legacy warnings** so readers do not follow them as the corrected annual AC pipeline.
- [ ] Maintain a verified manifest of **all publication tables and figures** linking article identifier, script, input cohort, resulting file, source checksum, timestamp/timezone and scenario.
- [ ] Review `config.json` status: its old four gross-error timestamps are original `01–11` parameters, **not** a Step 28 exclusion list. Do not silently rewrite them and invalidate historical scripts.
- [ ] Confirm that public distribution of RISE records, software-generated data/exports, datasheets and any PDFs is permitted under the underlying agreements. `LICENSE.md` does not itself grant third-party data permissions.
- [ ] Verify cross-references, tables, source years, uncertainty captions, reviewer replies and manuscript figures; remove promises of computations that have not actually been produced.
- [ ] Keep original version/build labels (IDA ICE 5.1.1 / 5.1.1.1 beta and PVsyst 8.0.2) consistent with preserved executable source and exported metadata, not assumptions.
- [ ] Run tests in a fresh environment and capture machine-readable QA output. Existing `tests/test_17_integrate_C9_shading_clock.py` is a targeted test only, not a whole-repository integration test.
- [ ] Publish a version tag, optional Zenodo DOI, updated `CITATION.cff` and release notes **only once** the numerical and manuscript snapshots are signed off.

## 5. Historical file retention policy

**Keep:** original measurements and exports (subject to sharing rights); original `01–11` scripts and canonical datasets; historical `05_*` statistical outputs; prior master workbook; previous figures; shading source audits; source reports; original prior version tags and commit history. Never falsify provenance by overwriting earlier metrics under the same names.

**Option for later cleanup:** move immutable older *generated* files into `results/legacy_pre_step28/` **only after** updating every affected script and reference and ensuring the historical workflow can still be reproduced. Otherwise leave them in place and label them as historical: that is safer than a cosmetic reorganization that breaks reproducibility.

**Add rather than overwrite:** a date/versioned `results/revision2/` package, an evidence/manifest table, machine-readable release tests and a documented history explaining why output semantics, daylight masking and clock alignment changed.

## 6. Release decision

The corrected 4,478-hour AC work is an **audited working candidate**, and the geometry/clock shading corrections are documented. **The repository is not yet a single unified manuscript reproduction pipeline.** Documentation can remove ambiguity now; the missing regenerated monthly/weather-bin/inference artifacts and source-level verification must not be represented as completed until checked.

This checklist is intended to be updated with dates, Git commit IDs and exact evidence paths for each closed item.
