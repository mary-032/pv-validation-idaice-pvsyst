# RISE System A/3 shading chronology and original-source reconciliation

**Evidence as of 22 October 2026**

- Geometry: pole was moved **10 May 2023 approximately 13:10 Swedish local time**, supported by contemporaneous correspondence and photos timestamped 13:15:16 and 13:15:25.
- IDA ICE original configuration names: `Syst3_PD_Shadow_middle` (first) and `Syst3_PD_Shadow_corner` (after move).
- PVsyst original exports provided by the author: `PVsyst_3_SH1_h.CSV` (**middle**) and `PVsyst_3_SH2_h.CSV` (**corner**).
- AC output in **the archived IDA ICE shading analysis** is `inverter_o` from `energy/electrical system.EL-STRING-POWERS.prn`. This is **not** the `produced_p` channel in `energy/electrical system.EL-POWERS.prn`, and the latter must not be substituted. The inverter channel reproduces the original 1,200 archived System A rows **exactly**, including the historically assumed 11 May switch.
- The existing IDA ICE hour-ending label corresponds to the PRN elapsed-hour index = hours since 2023-01-01 00:00 **minus one**; this mapping is verified by 1,200 exact value matches. PVsyst `E_Grid` rows are labelled by hour **start**; its arbitrary 1990 reference year is ignored and the month/day/hour sequence is matched to 2023.
- The hour **13:00–14:00 on 10 May** is mixed geometry, so exclude the record **ending 14:00** from primary System A energy and hourly error statistics, including both the measured and simulated sum. Preserve it in the canonical dataset and sensitivity work.
- This work alters **only System A/3**. Existing System B/C results remain unchanged; approved System C timing sensitivity remains a separate later integration task.

## Files in the zip

- `data/pvsyst/shaded/PVsyst_3_SH1_h.CSV` — original SH1 export
- `data/pvsyst/shaded/PVsyst_3_SH2_h.CSV` — original SH2 export
- `scripts/16_rebuild_A3_shading.py` — non-destructive source-specific builder; generates 3,600-row canonical CSV and result tables
- `02_run_analysis_A3_geometry_update.patch` — patches script 02 to read the versioned canonical file and correctly exclude the mixed hour

## PyCharm workflow

1. Unzip contents at your repository **root** (preserves relative paths).
2. From repository root, inspect the patch with `git apply --check 02_run_analysis_A3_geometry_update.patch`. Then run `git apply 02_run_analysis_A3_geometry_update.patch`.
3. Check that archived `derived_data/shading_analysis.csv` and both original IDA ICE model PRNs exist locally.
4. Run `python scripts/16_rebuild_A3_shading.py`.
5. Run `python scripts/02_run_analysis.py`.
6. Review:
   - `derived_data/shading_analysis_rebuilt_A3.csv`
   - `results/Shading_A3_geometry_energy.csv`
   - `results/Shading_A3_geometry_hourly.csv`
   - `results/Shading_A3_source_reconciliation.csv`
   - regenerated `results/Shading_energy_recomputed.csv` and `results/Shading_hourly_diagnostics_recomputed.csv`.
7. To regenerate illustrative shading figures from the revised canonical file, change `SOURCE` in `scripts/11_make_figures4_5_6_shading.py` from `shading_analysis.csv` to `shading_analysis_rebuilt_A3.csv`. The selected May 15 and June 5 A curves are unaffected by the May 10 correction, but reading the same source is important for reproducibility.
8. **Do not push/commit** until comparing the regenerated tables against the companion workbook.

The separate old `scripts/01_build_canonical_data.py` still writes `derived_data/shading_analysis.csv`; do not change it for this reconstruction. Always run **script 16 after script 01** if rebuilding the entire pipeline. The patched script 02 reads the versioned output of script 16. The main annual reconstruction also needs its own future integration and is not modified by this patch.

## Results reproduced for System A/3

All energy figures are kWh, with model-minus-measured sign:

| Physical period | Hours | Measured | IDA ICE (inverter_o) | PVsyst (SH1/SH2) | IDA bias | PVsyst bias |
|---|---:|---:|---:|---:|---:|---:|
| Middle, before relocation | 229 | 202.883 | 225.849 | 204.532 | +11.32% | +0.81% |
| Corner, after relocation | 970 | 815.699 | 788.036 | 813.745 | -3.39% | -0.24% |
| Combined, excluding mixed hour | 1199 | 1018.582 | 1013.885 | 1018.277 | -0.46% | -0.03% |

The A/3 daylight hourly AC RMSE (GTI > 0, transition excluded) is **275.87 W** for IDA ICE and **267.08 W** for PVsyst (931 paired hours). The near-zero aggregate energy bias must not be conflated with absence of phase-specific errors.

**Source limitations:** The mixed hour is not reconstructible as one fixed-geometry simulation; this hour is deliberately omitted from the primary comparison. The System A reconstruction uses the archived measured series unchanged. The complete original field timestamp series still needs the independent annual source audit for the annual analyses; this is a separate case.
