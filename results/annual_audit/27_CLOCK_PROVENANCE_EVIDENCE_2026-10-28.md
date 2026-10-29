# Step 27 — Annual PV validation clock-provenance assessment

**Study:** RISE Borås, June 2020–May 2021. **Status:** evidence-based interpretation, not authenticated logger documentation. **Input:** uploaded `Ekås_89PD.MET`, archived IDA ICE model configurations, previously reconstructed Step 23 measured GTI observations. No simulation results or input data were modified.

## 1. Directly confirmed from the uploaded PVsyst weather file

The file is a UTF-8 PVsyst 8.0.2 imported-weather `.MET` containing three hourly weather quantities (`GlobHor`, `DiffHor`, `T_Amb`). The header records:

| MET field | Recorded value | Interpretation/evidence boundary |
|---|---|---|
| `NomF` | `Ekås_89PD.MET` | Imported PVsyst meteorological file |
| `SourceM` / `TypeM` | `Custom file` / `Imported` | Imported, rather than generated directly as Meteonorm weather |
| `NomFSource` basename | `Meteo_89_PD.csv` | Identifies import source by name; does not reveal source timestamp convention |
| `NomFormat` | `pvsyst Rise project.MEF` | References the custom import definition, not provided here |
| `Version` | `8.0.2` | Legacy PVsyst treatment applies |
| `TimeZone` | `1.0` | Site legal winter time UTC+1 |
| `HourShift` | `-1` | A one-hour time-label correction was applied at import; per PVsyst legacy documentation, corrected labels are already in the `.MET` |
| `TimeShift` / `TimeShiftImported` | `-17` / `-17` | Minute-level correction metadata; **not** another one-hour or DST correction |
| `IsSourceUt` | `False` | Source is not flagged as UT; not proof of the logger's clock convention |
| `PasAccum` | `60` | Hourly accumulation interval (minutes) |
| `DateDebF` / `DateFinF` | Jan–Dec 1990 | Synthetic calendar used by this imported weather file, not physical measurement year |

The uploaded file contains an original absolute operator/source path. This assessment deliberately retains only the source basename; **do not publish the raw `.MET` without checking path privacy and release permissions**.

PVsyst legacy documentation specifically states that hourly `.MET` records are labeled at the **interval start**, in **legal winter time** (no DST). It further says that large **hour shifts change the weather record labels during import**, while residual **minute shifts alter solar-geometry calculation time**. Consequently, do not add an extra one-hour shift to the already imported `.MET` data merely because its header reports `HourShift=-1`.

Relevant official documentation:
- https://www.pvsyst.com/help/meteo-database/notes-on-meteo/meteonote3-time-shift-in-meteo-files.html
- https://www.pvsyst.com/help/meteo-database/meteo-tables-and-graphs/data-characteristics.html

## 2. Independent measurement-clock check using *measured irradiance*, not simulation error

Source: Step 23 `23_annual_AC_channel_comparison_hourly.csv`; selected System B measured GTI for `civil_unshifted` once, yielding 4,478 daylight-hour records. For each physical date with positive measured GTI, computed the GTI-weighted centroid of local time using **hourly interval midpoints**. Compared this descriptive centroid with approximate astronomical solar noon using the site's longitude 12.884806° E, a leap-year-aware NOAA equation-of-time approximation, and either CET (UTC+1) or CEST (UTC+2) for Swedish legal time. This comparison uses **no IDA ICE/PVsyst power outputs** or optimized shifts.

| Period | Days with positive GTI | Mean measured GTI centroid (local h) | Expected astronomical noon in Swedish civil time (local h) | Mean difference | 95% day-bootstrap CI for difference |
|---|---:|---:|---:|---:|---:|
| CET | 153 | 12.226 | 12.166 | +0.060 h (+3.6 min) | −0.011 to +0.130 h |
| CEST | 210 | 13.107 | 13.122 | −0.015 h (−0.9 min) | −0.116 to +0.091 h |

Under the **hypothesis that all RISE labels were fixed CET**, expected summer solar noon in their time labels would be approximately **12.122 h**, but the measured GTI centroid is **13.107 h**, approximately **59.1 minutes later**. This agrees much better with **Swedish civil CET/CEST labels** than with year-round fixed-CET labels. The observation independently supports the summer-hour offset examined in Steps 21–26.

**Limitations:** Irradiance centroid is a weather-dependent indicator, not a direct clock reading or an exact astronomical noon measurement. The input is already the Step 23 reconstructed hourly measured GTI series, so it inherits the selected sample-start convention, synthetic-to-physical-year mapping and measurements' provenance. Bootstrapped intervals quantify variation across days, **not** the uncertainty in the logger's undocumented time standard. Instrument orientation, local shading, cloudiness and incomplete data can move the centroid. The evidence supports a civil-time interpretation; it does **not** authenticate the original logger configuration.

Outputs: `27_RISE_GTIsolar_noon_daily.csv`, `27_RISE_GTIsolar_noon_summary.csv`, and `27_check_RISE_GTIsolar_noon.py`.

## 3. Cross-source synthesis and proposed decision

- RISE GTI seasonal centroid independently follows the CET/CEST change.
- The saved IDA ICE annual model location and climate definitions specify standard-time settings, and the native IDA weather series uses sequential hours. However, model configuration alone does not prove each report's export time label.
- PVsyst's `.MET` is stored on a legal **winter-time clock**; the metadata records a **pre-existing, uniform -1 hour import adjustment**, distinct from translating measured civil time to fixed-standard time. Its 1990 year label is synthetic.
- The previously audited Step 26 model-versus-measurement results numerically favor a 0-hour winter / −1-hour summer lookup for **both** software exports, with IDA ICE hourly-average `produced_p` matched at **interval end** and PVsyst `E_Grid` at **interval start**. That result is consistent with, but does not independently validate, these interpretations.

**Recommendation:** Treat the fixed-CET model-to-civil comparison as the **best-supported working primary annual interpretation**, retain the no-adjustment case as a **mandatory clock sensitivity**, and disclose that the original RISE logger's time configuration is undocumented. Do not describe this result as an authenticated clock correction or a fresh PVsyst weather-file modification. Before freezing, verify the final selected cohort and full-model output provenance, and reproduce final metrics from a versioned annual raw-reference dataset.

## 4. Remaining optional provenance sources

If available, the historical `Meteo_89_PD.csv` and `pvsyst Rise project.MEF` would let us reconstruct the PVsyst import transformation and look for DST/date-label settings. They are **not required** to interpret the `.MET` header and should not be fabricated or guessed. The lack of original RISE logger documentation must remain a stated limitation.
