# Step 40 — Revision 2 seasonal tables and composite diurnal error figures

**Status:** manuscript/supplement **candidates**, not a signed-off research release.  
**Scientific provenance:** corrected Step 28 matched hourly AC series, checked against Step 29 aggregates. This step is **descriptive postprocessing only**; it does not rerun IDA ICE or PVsyst, infer clocks, select outliers, or replace historical results.

## Why this exists

Reviewer 7 requested seasonal performance metrics and composite diurnal error distributions. Step 29 already contains the season-specific metrics and hourly **means**, but the latter lack observed spread. This builder produces two manuscript-ready seasonal tables and two three-panel composite diurnal figures, with **within-hour interquartile bands** calculated from the same individual Step 28 residuals.

## Inputs and exact cohort

- `results/annual_audit/28_annual_AC_primary_fixed_CET.csv`: working fixed-CET model-clock scenario.
- `results/annual_audit/28_annual_AC_sensitivity_civil_unshifted.csv`: alternative model-clock alignment with identical physical measured hours.
- `results/revision2/29_seasonal_AC.csv`: existing authoritative seasonal CV(RMSE) and nMBE statistics.
- `results/revision2/29_diurnal_AC.csv`: existing authoritative hourly count, mean signed error (MBE), RMSE and MAE, used to **cross-check** the new figure-source summaries.

Exactly **4,478 paired selected daylight hours per system** are used under *each* clock scenario; no extra threshold, residual trimming or shadow-hour mask is introduced. Each hour is a measured **physical interval start** in local civil-clock labels. The selected cohort contains 364 distinct calendar dates, with **31 December 2020 absent**. This is a coverage observation; its source cause has not been independently established.

Seasons are **DJF** (Dec–Feb), **MAM** (Mar–May), **JJA** (Jun–Aug), **SON** (Sep–Nov). For each system and software the sample counts are **703 / 1,310 / 1,537 / 928 hours**, respectively. They sum to 4,478. Seasonal CV(RMSE) and nMBE refer to **hourly AC power** and each season's own mean measured power; they are **not** monthly kWh/kWp energy RMSE.

## Output register

Run outputs go only into `results/revision2/40_supplement/` (or an explicitly selected `--output-dir`):

| Filename | Content |
|---|---|
| `Table_S1a_seasonal_fixed_CET_hypothesis.md` and `.csv` | Six-row fixed-CET table for A–C, IDA ICE/PVsyst, four seasons; each cell `CV(RMSE) / nMBE (%)` |
| `Table_S1b_seasonal_civil_unshifted.md` and `.csv` | Identical table structure using the alternative unshifted civil-clock model alignment |
| `Figure_S1a_diurnal_fixed_CET_hypothesis.pdf/.svg/.png` | Three vertically stacked system panels: mean hourly AC error ± interquartile bands, working clock |
| `Figure_S1b_diurnal_civil_unshifted.pdf/.svg/.png` | Matching three-panel sensitivity graphic for the alternative clock |
| `Figure_S1_diurnal_source_statistics.csv` | **Aggregate**, not row-level: 216 scenario/system/model/hour cells, with sample count, mean, median, 25th and 75th percentiles, hourly RMSE and MAE |
| `40_supplement_manifest.json` | Input SHA-256 hashes and caveats; snapshot of the exact inputs used |

All six columns in each of the S1 tables are generated from Step 29, **without rewriting the source results**. There are 18 local clock-hour groups (05–22) per system/model/scenario. At sparsely observed edge hours the sample count is small (e.g. 33 observations for hour 22); these values describe the *selected daylight cohort*, not a typical 24-hour day.

The line in each figure is mean residual **P_sim − P_meas** (W), positive when simulation exceeds measurement. Transparent bands span **25th to 75th sample percentiles** (type-7 linear interpolation). These are distributions of *individual hourly errors across observation days*, **not** confidence intervals or ±1 standard deviation. A mean curve may occasionally lie outside its IQR because the mean and median are distinct. Plot vertical limits are shared across the three systems within a scenario, but **not necessarily identical across the two scenarios**; compare numerical values rather than apparent vertical heights.

Colors follow Step 35 Figure 3: IDA ICE green (`#77AC30`), PVsyst blue (`#0072BD`). Line styles and symbols provide another distinction.

## Reproduction in PyCharm (Windows PowerShell)

Run from the project root. Use the project's supported virtual environment. No legacy analysis scripts are called.

```powershell
# Optional consistency check on Step 29; does not regenerate data:
& .\.venv313\Scripts\python.exe scripts/29_aggregate_revision2_annual_AC.py --check-only

# Runs the new Step 40 output builder (requires matplotlib for rendering):
& .\.venv313\Scripts\python.exe scripts/40_build_seasonal_diurnal_supplement.py

# Read-only check of output text, source comparisons and plot existence:
& .\.venv313\Scripts\python.exe scripts/40_build_seasonal_diurnal_supplement.py --check-only

# Unit tests use synthetic inputs and the standard library:
& .\.venv313\Scripts\python.exe -m unittest discover -s tests -p "test_40*.py" -v
```

If Step 40 outputs already exist and a **deliberate regeneration** is necessary, pass `--overwrite`. Without that explicit switch, the program refuses to overwrite its own figures/tables. It never writes into the Step 28/29 source directories or any historical file. To inspect newly rendered outputs without writing into the repository, use `--output-dir "C:\temp\revision2_step40_review"`.

`--check-only` checks that all numerical CSV/Markdown/manifest outputs exactly match source-derived content and each published figure exists with nonzero size; figure pixel identity across Matplotlib versions is **not** claimed. Verify the plots visually as well.

## Scientific cautions

1. **Clock sensitivity dominates tool ranking:** under fixed CET, IDA ICE has lower seasonal CV(RMSE) for A–C in DJF/MAM/JJA/SON. Under civil-unshifted, IDA ICE remains lower in DJF, but PVsyst is lower in MAM/JJA/SON for A–C. This is a *conditional* comparison, not evidence establishing the actual logger convention.
2. The **winter values are identical** in both scenarios because the differing daylight-saving-clock treatment does not affect DJF here. That does not authenticate source clocks.
3. High winter CV(RMSE) can result from low mean measured power. It is inappropriate to infer particular causes (snow, bypass-diode activation, thermal inertia, optimizer operation, irradiance transposition) from a seasonal/diurnal chart alone.
4. Neither seasonal table nor figure has **new paired block-bootstrap intervals**. Do not claim significance of season- or hour-specific model differences.
5. `29_seasonal_AC.csv` and `29_diurnal_AC.csv` are the verified aggregation references, but source and model provenance have the qualifications described in `docs/REVISION2_REPRODUCIBILITY.md`; this builder does not independently authenticate original RISE clocks or native PVsyst configuration.
6. The full 10-minute/s sub-hourly behavior is not analyzed; the diurnal figure summarizes **hourly AC prediction errors**.

See `docs/STEP40_SUPPLEMENT_MANUSCRIPT_GUIDE.md` for ready-to-paste captions, recommended manuscript placement and reviewer-response scope.
