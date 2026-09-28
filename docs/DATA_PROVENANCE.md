# pv-validation-idaice-pvsyst
Reproducible data-processing, validation, uncertainty, sensitivity, and figure-generation workflow for comparing PV simulations in IDA ICE and PVsyst against measured data.
# Data provenance

This document describes the origin, transformation, alignment, and status of the datasets used in the validation of PV simulations performed with IDA ICE and PVsyst.

The purpose is to distinguish clearly between:

1. original measurements;
2. simulation exports;
3. historical processed data;
4. reconstructed canonical datasets;
5. sensitivity scenarios;
6. final analysis outputs.

Where preprocessing corrections were required, they are documented explicitly rather than applied silently.

---

## 1. PV systems

Three PV systems installed at the RISE research facility in Borås, Sweden, were evaluated.

| System | Original system ID | Technology | Installation | Nominal power |
|---|---|---|---|---:|
| A | 3 | Monocrystalline silicon | BAPV | 3.9 kWp |
| B | 8 | Monocrystalline silicon with SolarEdge P405 optimisers | BAPV | 4.8 kWp |
| C | 9 | CIGS thin-film | BIPV | 3.3 kWp |

All three systems have a nominal module tilt of 45° and are south-facing.

The site coordinates used for solar-geometry calculations are:

```text
Latitude:   57.719231°
Longitude:  12.884806°
Altitude:   170 m
Time zone:  Europe/Stockholm
```

---

## 2. Annual measured data

The annual validation period covers:

```text
1 June 2020 – 31 May 2021
```

The primary original measurement workbook is:

```text
RISE_raw10min_389.xlsx
```

The original measurements are recorded at 10-minute resolution.

The source workbook contains separate sheets for Systems 3, 8, and 9, corresponding to Systems A, B, and C in the manuscript.

Principal measured variables include:

- plane-of-array irradiance;
- panel temperature;
- AC power;
- ambient temperature.

The analysis is ultimately performed using hourly values.

### 2.1 Source-sheet mapping

The original workbook contains the following principal columns:

```text
system_3:
Time
Tamb_3
GTI_3
Power_3
Tpanel_3

system_8:
Time
Tamb_8
GTI_8
Power_8
Tpanel_8

system_9:
Time
Tamb_9
GTI_9
Power_9
Tpanel_9
```

Systems B and C use the same measured GTI series in the reconstructed analysis layer.

---

## 3. Historical processed measured-data layer

A historical workbook used in the original analysis workflow is:

```text
Results_PVsyst_E2_hour.xlsx
```

The relevant sheet contains hourly processed measured variables with a synthetic January–December 2021 time axis.

The principal measured columns used from this workbook are:

```text
Date
GTI3M
GTI9M
Tp3M
Tp8M
Tp9M
P3M
P8M
P9M
```

The workbook also contains older simulation results. These simulation columns are not considered authoritative in the final reconstructed analysis.

The historical workbook is retained because its measured-data layer reproduces preprocessing steps that could not be reconstructed exactly from the original 10-minute measurements alone.

---

## 4. Physical time versus analysis time

The physical annual measurement period is June 2020 through May 2021.

Historical processing represented these data on a synthetic January–December 2021 analysis time axis.

The reconstructed workflow therefore distinguishes between:

```text
analysis time
```

and:

```text
physical time
```

The analysis timestamp is retained for compatibility with the historical hourly simulation alignment.

The physical timestamp represents the actual calendar period and is used where true solar geometry and day of year are required.

This distinction is particularly important for:

- solar position;
- extraterrestrial irradiance;
- angle of incidence;
- tilted clearness index.

---

## 5. Time-zone handling

A reconstruction audit compared alternative interpretations of the RISE logger clock.

The data were most consistent with civil time using:

```text
Europe/Stockholm
```

rather than fixed Central European Time.

The canonical-data builder therefore localises the physical timestamps using the Europe/Stockholm time zone.

The daylight-saving-time transition in March 2021 is handled explicitly. The affected transition interval occurs during hours without relevant PV production and does not materially affect the daytime validation dataset.

---

## 6. System A measured GTI alignment correction

During reconstruction of the annual dataset, the measured GTI series for System A was found to be displaced by one hour relative to:

- the IDA ICE irradiance output;
- the PVsyst irradiance output;
- the historical processed analysis layer.

The reconstructed workflow therefore applies a one-hour assignment correction to System A measured GTI.

Conceptually, the historical System A measured GTI value is assigned to the following analysis hour.

This correction is applied only to the measured GTI series used for System A irradiance validation.

It is not a scaling correction and does not alter the measured irradiance magnitude.

Systems B and C use the common measured GTI series without this correction.

The correction was retained because it restored the temporal alignment supported by the reconstructed historical workflow and both independent simulation outputs.

---

## 7. IDA ICE annual simulation exports

The authoritative annual IDA ICE exports for the primary Perez–Driesse scenario are:

```text
Syst3_PD.xlsx
Syst8_PD.xlsx
Syst9_PD.xlsx
```

The corresponding Engerer2 sensitivity exports are:

```text
Syst3_E2.xlsx
Syst8_E2.xlsx
Syst9_E2.xlsx
```

The system mapping is:

```text
Syst3 → System A
Syst8 → System B
Syst9 → System C
```

The IDA ICE exports contain 8,737 indexed states from `Time = 0` to `Time = 8736`.

`Time = 0` is treated as the initial state.

The annual analysis uses:

```text
Time = 1 ... 8736
```

giving 8,736 hourly simulation values.

### 7.1 IDA ICE variables

The canonical-data builder extracts:

- produced AC power;
- panel temperature;
- panel effective irradiance.

Where several panel-temperature or panel-effective-irradiance variables are present for a system, the relevant panel values are averaged according to the final parsing procedure implemented in the canonical-data builder.

---

## 8. PVsyst annual simulation exports

The authoritative Perez–Driesse PVsyst exports are:

```text
PVsyst_3_PD_h.xlsx
PVsyst_8_PD_h.xlsx
PVsyst_9_PD_h.xlsx
```

The Engerer2 sensitivity exports are:

```text
PVsyst_3_E2_h.xlsx
PVsyst_8_E2_h.xlsx
PVsyst_9_E2_h.xlsx
```

Each PVsyst export contains 8,760 hourly records.

The calendar years contained in individual PVsyst exports are not treated as authoritative for alignment because different simulation exports used arbitrary calendar years.

Instead, the final preprocessing reconstructs the hourly position from row order and aligns the data to the common analysis timeline.

Principal PVsyst output variables used are:

- AC/grid power;
- array temperature;
- effective irradiance (`GlobEff`).

Night-time inverter consumption values present in some PVsyst exports are not used in the annual daytime validation because the analysis is restricted to observations with measured GTI greater than 0 W/m².

---

## 9. Primary irradiance reconstruction: Perez–Driesse

The primary annual validation uses irradiance components reconstructed using the Perez–Driesse method.

These reconstructed irradiance components form the weather/input case used for the primary IDA ICE and PVsyst simulations.

The Perez–Driesse simulation exports are the authoritative baseline results for the article.

Older Engerer2 results contained in historical workbooks are not used as the primary simulation outputs.

---

## 10. Engerer2 reverse-transposition sensitivity

Engerer2 is used as an alternative irradiance-processing scenario to assess whether conclusions depend on the reverse-transposition/separation method.

The Engerer2 scenario uses the same:

- measured data;
- system definitions;
- analysis timestamps;
- filtering;
- geometry;
- power exclusions;
- statistical methods

as the Perez–Driesse baseline.

Only the irradiance-processing/simulation scenario differs.

Engerer2 is therefore treated as a methodological sensitivity analysis rather than as a second primary analysis.

---

## 11. System A Engerer2 PVsyst timing correction

During the Engerer2 sensitivity analysis, the System A PVsyst output initially showed an implausibly large irradiance discrepancy.

A dedicated timing audit examined:

- effective irradiance;
- panel temperature;
- AC power;
- alternative temporal lags;
- the corresponding Perez–Driesse export;
- Systems B and C.

All three System A Engerer2 PVsyst variables independently preferred the same +1 h temporal shift.

The same pattern was not present for:

- System A Perez–Driesse;
- System B Engerer2;
- System C Engerer2.

The final Engerer2 preprocessing therefore applies a uniform:

```text
+1 h
```

shift to the complete System A PVsyst Engerer2 record.

The correction is applied jointly to:

```text
effective irradiance
panel temperature
AC power
```

No variable-specific correction, interpolation, or value scaling is applied.

### 11.1 Metadata evidence

A separate audit of the PVsyst workbook metadata identified a unique meteorological-file reference for the System A Engerer2 simulation:

```text
Ekås_Custom_E2.MET
```

The corresponding Perez–Driesse export referred to a different meteorological file.

The original `Ekås_Custom_E2.MET` file is no longer available, so the exact origin of the one-hour displacement cannot be independently reconstructed.

The correction is therefore described as an audit-based temporal alignment correction rather than as a confirmed software defect.

The relevant audit scripts are retained in:

```text
scripts/audits/
```

---

## 12. Solar geometry

The final geometry reconstruction uses the full azimuth-dependent incidence-angle equation.

The extraterrestrial irradiance normal to the solar beam is calculated from day of year and projected onto the tilted plane using the calculated angle of incidence.

The tilted clearness index is then calculated from:

```text
measured GTI / extraterrestrial irradiance on the tilted plane
```

The final geometry supersedes an earlier simplified incidence-angle expression that did not fully account for solar azimuth.

This correction changed the assignment of some observations to weather-condition bins and therefore required the weather-bin analysis and Figure 3 to be regenerated.

---

## 13. Weather-condition bins

The primary weather-condition analysis uses the following tilted-clearness-index categories:

| Condition | `kt_tilt` |
|---|---|
| Overcast / very cloudy | `< 0.20` |
| Cloudy | `0.20–0.40` |
| Mixed / broken | `0.40–0.60` |
| Mostly clear | `0.60–0.75` |
| Clear | `≥ 0.75` |

Only observations with:

```text
AOI < 80°
```

are included in the weather-bin analysis.

No upper limit is imposed on `kt_tilt`.

The sensitivity of the weather-bin conclusions to the exact internal thresholds is evaluated separately by shifting the bin edges by ±0.05.

---

## 14. Annual power gross-error screening

No residual outliers are removed from the annual GTI or panel-temperature analyses.

For AC power, a conservative gross-error screening procedure was used.

Power residuals are defined as:

```text
simulated power - measured power
```

A robust standard deviation was estimated from the residual distribution using the median absolute deviation.

A timestamp was classified as a gross anomaly only when:

1. the residual exceeded ten times the robust standard deviation;
2. this occurred for both IDA ICE and PVsyst;
3. the residuals had the same sign;
4. the condition occurred simultaneously across all three PV systems.

The procedure identified four hourly timestamps:

```text
2 February 2021 12:00
2 February 2021 13:00
2 April 2021 13:00
30 April 2021 13:00
```

The complete corresponding records are excluded consistently from:

- measured power;
- IDA ICE power;
- PVsyst power

for Systems A, B, and C.

These exclusions are subsequently used for:

- annual power validation;
- monthly energy analysis;
- weather-condition power analysis.

A separate sensitivity analysis evaluates the effect of retaining versus excluding these observations.

The screening identifies statistical anomalies; it does not establish the physical cause of the anomalous records.

---

## 15. Shading experiment

The shading experiment covers:

```text
1 May 2023 – 19 June 2023
```

The original measurement data were recorded at higher temporal resolution than the annual dataset.

For comparison between IDA ICE and PVsyst, the shading results are analysed on a common hourly basis.

### 15.1 Selected case-study days

Two days are used for illustrative time-series comparisons:

```text
5 June 2023  → clear case
15 May 2023  → partly cloudy case
```

The days were selected to provide contrasting measured irradiance conditions during the periods when the physical shading objects affected the systems.

They are not intended to represent the full shading experiment statistically.

The quantitative shading analysis additionally evaluates the complete 1 May–19 June period.

### 15.2 System A shading-object position

The System A physical shading-object position changed during the experimental period.

The reconstructed shading dataset distinguishes the earlier and later positions.

The transition occurred on:

```text
11 May 2023 at approximately 12:00
```

The selected case-study days, 15 May and 5 June, therefore both use the later System A shading configuration.

This ensures that the clear and partly cloudy illustrative cases use the same System A obstruction geometry.

---

## 16. Canonical datasets

The authoritative processed datasets are generated programmatically from the source material by:

```bash
python scripts/01_build_canonical_data.py
```

The canonical datasets are intended to provide a single analysis-ready layer containing the aligned:

- measured observations;
- IDA ICE results;
- PVsyst results;
- timestamps;
- solar geometry;
- clearness-index variables;
- system metadata.

The statistical scripts operate on these canonical datasets rather than repeatedly parsing the proprietary-software exports.

---

## 17. Authoritative versus historical files

The following distinction is important.

### Authoritative primary simulation outputs

```text
IDA ICE Perez–Driesse:
Syst3_PD.xlsx
Syst8_PD.xlsx
Syst9_PD.xlsx

PVsyst Perez–Driesse:
PVsyst_3_PD_h.xlsx
PVsyst_8_PD_h.xlsx
PVsyst_9_PD_h.xlsx
```

### Authoritative Engerer2 sensitivity outputs

```text
IDA ICE:
Syst3_E2.xlsx
Syst8_E2.xlsx
Syst9_E2.xlsx

PVsyst:
PVsyst_3_E2_h.xlsx
PVsyst_8_E2_h.xlsx
PVsyst_9_E2_h.xlsx
```

### Historical/provenance material

Older processed workbooks, MATLAB scripts, frozen intermediate result files, and superseded Engerer2 outputs are retained only where useful for reconstructing the development of the analysis.

They should not be substituted for the active canonical datasets or the authoritative simulation exports.

---

## 18. Reproducibility principle

Source files are preserved unchanged wherever possible.

Corrections and transformations are applied by code and documented explicitly.

The final analysis therefore separates:

```text
source data
    ↓
canonical reconstruction
    ↓
statistical analysis
    ↓
uncertainty / sensitivity analysis
    ↓
publication outputs
```

This structure is intended to make all consequential preprocessing decisions visible and auditable.
