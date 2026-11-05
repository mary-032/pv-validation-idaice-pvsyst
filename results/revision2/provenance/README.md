# Historical source-provenance aggregates — Step 36

> **NOT authoritative for current manuscript AC metrics.** Derived from local untracked October 2026 Steps 18–25 audits to preserve a limited early evidence trail. Working current analyses: `results/annual_audit/28_*`, `results/revision2/29_*`, `results/revision2/35_*`.

| File | Contents |
|---|---|
| `18_historical_sampled_AC_targets.csv` | Historical sampled-channel comparison targets including the contemporaneous original CI values; **not** new Step 28 Table-power results |
| `19_pvsyst_inventory_consistency.csv` | Source-hash overlap counts only; no verified `Version`, run identity or native metadata text |
| `20_alignment_diagnostic_coverage.csv` | Three-system source coverage and number of alternative alignment candidates; no claim of clock authentication |
| `22_source_channel_consistency.csv` | Sampled `produced_p` match and finite-pair `E_Grid` unit checks, not final hourly-Table equivalence |
| `24_SystemA_hourly_Table_QC.csv` | Aggregate original hourly Table vs saved-endpoint agreement, without raw hourly Table rows |
| `25_SystemA_selected_model_metrics.csv` | Historical selected A-only sampled / end-aligned Table / PVsyst comparisons for both clock scenarios |
| `25_SystemA_hourly_Table_paired_CI30d.csv` | Historical A-only end-aligned Table vs PVsyst RMSE differences and seeded bootstrap intervals for both clocks |
| `36_curation_manifest.json` | Twelve original input hashes, seven published output hashes, interpretation/rights/clock flags |

The original **row-level** `24_SystemA_hourly_table_vs_sampled_audit.csv` and `25_SystemA_interval_corrected_hourly.csv`, **verbatim** `18_pvsyst_project_evidence.csv`, full `.PRJ/.VC*/.MET/.PAN/.GIM` files, and unreviewed personal reference documents are intentionally excluded. The status field on each compact table unambiguously indicates historical diagnostics.

The included source code and tests reproduce the curation from the original local CSVs but do **not** regenerate third-party raw measurements or simulator output. Without those inputs, `--verify-published` checks only public snapshot integrity, not full upstream provenance. Release permissions for source-derived aggregates remain to be determined. See `docs/REVISION2_EARLY_PROVENANCE.md`.
