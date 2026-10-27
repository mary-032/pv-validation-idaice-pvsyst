# System C/9 — validated shading-clock sensitivity integration

**Prepared 22 October 2026.** This is a new, non-destructive stage AFTER the already successful System A/3 pole chronology reconstruction (script 16). No simulation rerun is needed.

## Evidence and limits

- Original A/3 middle-to-corner switch: 10 May 2023 at approximately 13:10 local time. The mixed hour ending 14:00 is excluded for A/3 only.
- Measurement-only B/C cross-system daily profiles imply C measurements are early by **2 h on 12–14 June** and **1 h on 15–19 June 2023** (hour-ending labels); other dates do not require a shift. This is an **inferred reference-time reconstruction**, **not a verified logger malfunction**.
- Existing historic C IDA simulated series included 43 independently unexplained hourly shifts. Primary comparison will instead use **unmodified native IDA ICE `inverter_o`** from `simulation_models/shaded/IDAICE/System_C_9/Syst9_PD_Shadow/energy/electrical system.EL-STRING-POWERS.prn`; no simulation output is shifted to fit measurement. The historic C model alignment remains preserved in an audit column.
- PVsyst C simulation and measured GTI stay unchanged. A and B comparison values stay unchanged; the combined table contains 3,600 source rows and a single flagged A transition hour. No power outliers are removed.
- Reindexed C measurement values at target hour `t` are read from the *original* C measured power at `t – shift_h`—never iteratively shifted; an hour ending 00:00 belongs to the preceding operating day.
- The original and reindexed results must both be reported in the manuscript or supplement. The eight daily lag tests use **measurements only**, without consulting either model.
- C measured total energy stays **867.190 kWh**; IDA ICE C simulated energy stays **901.411 kWh** and PVsyst stays **936.660 kWh** over the full 1,200 hours. Energy-bias values will be unchanged even though hourly error statistics change.

## Files to copy to the project

Extract the ZIP **at the repository root**. It includes:

- `scripts/17_integrate_C9_shading_clock.py` (new Python builder)
- `tests/test_17_integrate_C9_shading_clock.py` (six simple unit tests)
- `docs/README_C9_CLOCK_INTEGRATION.md` (these instructions)
- `02_and_11_C9_clock_update.patch` (in the **project root**) — changes only the shading-source paths in scripts 02 and 11, and adds a provenance note; does **not** modify annual logic.
- `docs/reference/C9_prior_clock_sensitivity_1200hr.csv` — prior reference comparison for independent review, **not an input** to the builder.

## Commands — Windows PowerShell in PyCharm

Use your working Python 3.13 environment explicitly, rather than the broken Python 3.15 `.venv`. From `C:\Users\mary\PycharmProjects\pv-validation-idaice-pvsyst`:

```powershell
# Source availability (four True values required):
Test-Path .\derived_data\shading_analysis_rebuilt_A3.csv
Test-Path '.\simulation_models\shaded\IDAICE\System_C_9\Syst9_PD_Shadow\energy\electrical system.EL-STRING-POWERS.prn'
Test-Path .\scripts\17_integrate_C9_shading_clock.py
Test-Path .\02_and_11_C9_clock_update.patch

# First, rebuild and validate the new combined canonical reference:
.\.venv313\Scripts\python.exe .\scripts\17_integrate_C9_shading_clock.py

# Check that script 02/11 edits are clean before applying:
git apply --check .\02_and_11_C9_clock_update.patch
# Only if the preceding check returns no error:
git apply .\02_and_11_C9_clock_update.patch

# Verify the six unit tests (no pytest installation needed):
.\.venv313\Scripts\python.exe -m unittest discover -s tests -p "test_17_integrate_C9_shading_clock.py" -v

# Regenerate ONLY shading results (protect the older annual pipeline):
.\.venv313\Scripts\python.exe -c "import runpy; runpy.run_path('scripts/02_run_analysis.py')['run_shading_analysis']()"

# Regenerate Figures 4–6 from the SAME combined final shading source:
.\.venv313\Scripts\python.exe .\scripts\11_make_figures4_5_6_shading.py

# Inspect changes. No need to commit before reviewing the outputs:
git status --short
```

**Do not apply this patch twice.** If `git apply --check` fails, STOP and share the exact error. Do not run `git apply --reject`, force the patch, or overwrite script 02/11 by hand.

**Do not run `python scripts/01_build_canonical_data.py`** now; it rebuilds the old canonical source, not the approved combined shading reference. Also avoid executing script 02's `__main__` block for the moment, which would rerun the annual tables using the old annual reference.

## Expected outputs

`17_integrate_C9_shading_clock.py` creates:

| File | Purpose |
|---|---|
| `derived_data/shading_analysis_final_A3_C9.csv` | Combined 3,600-row canonical shading dataset (A corrected geometry + C corrected measurement clock) |
| `results/Shading_C9_clock_daily_lag_evidence.csv` | Measured B/C profiles tested at lags 0, 1, 2, 3 h |
| `results/Shading_C9_original_vs_reindexed_metrics.csv` | Side-by-side measured-as-recorded, corrected, raw IDA, and historical IDA results |
| `results/Shading_C9_clock_hourly_audit.csv` | Per-hour original C measurement, source timestamp, adjusted C measurement, raw/historical IDA and PVsyst |

Script 02 then updates `results/Shading_energy_recomputed.csv` and `results/Shading_hourly_diagnostics_recomputed.csv`; script 11 then updates Figure 4, 5, and 6 output files. The illustrative May 15 / June 5 days precede the System C anomaly, so their C curves are *not expected to change*. The longer-period C hourly statistics **do** change.

## Expected System C RMSE cross-check (measured GTI > 0, n = 886)

| Measurement clock | IDA ICE column | IDA ICE RMSE [W] | PVsyst RMSE [W] |
|---|---|---:|---:|
| As recorded | Original native inverter_o | 244.25 | 253.70 |
| As recorded | Historically shifted IDA (sensitivity only) | 182.66 | 253.70 |
| Reindexed | Original native inverter_o **(primary)** | **158.29** | **171.97** |
| Reindexed | Historically shifted IDA (sensitivity only) | 193.69 | 171.97 |

**Required checks** in script 17: 3,600 original rows, A/B unchanged, C energy conserved, all eight B/C measured lag checks, exactly 43 historical C IDA differences, 123 C hourly measurement changes, original IDA native hour-index completeness. Any mismatch raises an error before writing outputs.

## Paper interpretation

This improves the time comparability of the measured reference, but does **not** prove a precise logger failure or independently validate PVsyst shading project geometry for B/C. Distinguish the System C clock **inference** from the 10 May System A pole-movement **documentary evidence**. Retain phase-specific System A results to avoid total-energy cancellation being mistaken for good hourly fit.
