# Methods

This document describes the data-processing and analysis methods implemented in the repository for the validation of photovoltaic (PV) simulations performed with IDA ICE and PVsyst.

The associated manuscript should be consulted for the scientific background, detailed system descriptions, and interpretation of the results. This document focuses on the computational workflow required to reproduce the analysis.

---

## 1. Study design

The study compares simulated PV performance from:

```text
IDA ICE 5.1.1.1
PVsyst 8.0.2
```

against measured data from three PV systems installed at the RISE research facility in Borås, Sweden.

The validation consists of two principal parts:

1. annual validation without explicit near-field shading objects;
2. a dedicated near-field shading experiment.

The primary annual comparison evaluates:

- plane-of-array/effective irradiance;
- panel temperature;
- AC power.

The shading comparison focuses on AC power.

---

## 2. PV systems

The three systems are referred to throughout the repository as Systems A, B, and C.

| System | Original RISE ID | Technology | Installation | Nominal power |
|---|---|---|---|---:|
| A | 3 | Monocrystalline silicon | BAPV | 3.9 kWp |
| B | 8 | Monocrystalline silicon with power optimisers | BAPV | 4.8 kWp |
| C | 9 | CIGS thin-film | BIPV | 3.3 kWp |

The systems have a nominal module tilt of 45° and are south-facing.

The site parameters used for solar-geometry calculations are stored in `config.json`.

---

## 3. Annual validation period

The physical annual measurement period is:

```text
1 June 2020 – 31 May 2021
```

The source measurements were recorded at 10-minute resolution.

The comparison between measured values, IDA ICE, and PVsyst is performed at hourly resolution.

Historical processing represented the annual period using a synthetic January–December 2021 analysis time axis. The reconstructed workflow therefore distinguishes between:

```text
analysis timestamp
```

and:

```text
physical timestamp
```

The physical timestamp is used for calculations that depend on the actual day of year, including solar geometry and extraterrestrial irradiance.

---

## 4. Shading validation period

The dedicated shading experiment covers:

```text
1 May 2023 – 19 June 2023
```

The original shading measurements were available at higher temporal resolution.

For direct comparison between IDA ICE and PVsyst, all shading results are evaluated on a common hourly basis.

The shading analysis includes:

```text
5 June 2023  → clear case
15 May 2023  → partly cloudy case
1 May–19 June 2023 → complete shading period
```

The individual days are used as illustrative case studies, while the full period provides the broader quantitative validation.

---

## 5. Measured data

The annual source workbook contains measured:

- plane-of-array irradiance;
- panel temperature;
- AC power;
- ambient temperature.

The original measurement and source-file mapping are documented in:

```text
docs/DATA_PROVENANCE.md
docs/DATA_DICTIONARY.md
```

Measured data are not overwritten during preprocessing. Transformations and alignment corrections are applied programmatically during construction of the canonical datasets.

---

## 6. Irradiance reconstruction

The simulation tools require irradiance components that were not all measured directly.

The primary simulation input uses irradiance reconstructed using the Perez–Driesse approach.

The primary analysis is therefore referred to as:

```text
Perez–Driesse
```

An alternative irradiance reconstruction using Engerer2 is retained as a sensitivity case.

The Engerer2 analysis is not treated as a second primary result. Its purpose is to determine whether conclusions concerning IDA ICE and PVsyst depend on the irradiance-processing method.

All other analysis rules are held as constant as possible between the Perez–Driesse and Engerer2 cases.

---

## 7. Simulation outputs

### 7.1 IDA ICE

The annual IDA ICE exports provide:

- produced AC power;
- panel temperature;
- panel effective irradiance.

The exported files contain an initial state at `Time = 0`.

The annual analysis uses:

```text
Time = 1 ... 8736
```

corresponding to 8,736 hourly values.

Where several panel-temperature or panel-effective-irradiance variables are present within one system, the final parser applies the aggregation implemented in `01_build_canonical_data.py`.

---

### 7.2 PVsyst

The PVsyst annual exports contain 8,760 hourly rows.

Principal variables used are:

- AC/grid power;
- array temperature;
- effective irradiance (`GlobEff`).

The arbitrary calendar years contained in individual PVsyst exports are not used as the authoritative alignment reference.

The final workflow reconstructs PVsyst timing from hourly row order and aligns the output to the common analysis time axis.

Night-time inverter-consumption values are not included in the annual daytime validation.

---

## 8. Canonical datasets

The source measurements and simulation exports are converted to common canonical datasets before statistical analysis.

The purpose of the canonical layer is to provide one aligned dataset containing:

- measured values;
- IDA ICE values;
- PVsyst values;
- system identifiers;
- timestamps;
- geometry variables;
- tilted clearness index;
- other analysis metadata.

Canonical datasets are created by:

```bash
python scripts/01_build_canonical_data.py
```

Subsequent analysis scripts use the canonical data rather than parsing the proprietary simulation exports repeatedly.

---

## 9. Time alignment

### 9.1 Civil time

The RISE logger timing was examined during reconstruction of the original workflow.

The final annual analysis interprets the logger time as civil time in:

```text
Europe/Stockholm
```

Daylight-saving-time handling is implemented explicitly in the canonical-data builder.

---

### 9.2 System A measured GTI

A one-hour displacement was identified in the historical System A measured GTI series.

The final reconstruction therefore assigns the System A measured GTI to the following analysis hour.

This is a timing correction only.

No irradiance values are scaled or interpolated.

Systems B and C do not receive this correction.

The supporting evidence is documented in:

```text
docs/DATA_PROVENANCE.md
```

---

### 9.3 System A Engerer2 PVsyst output

A separate timing audit identified a consistent one-hour displacement in the System A Engerer2 PVsyst simulation.

The displacement occurred simultaneously in:

- effective irradiance;
- panel temperature;
- AC power.

The complete System A Engerer2 PVsyst record is therefore shifted uniformly by:

```text
+1 h
```

prior to comparison.

No variable-specific correction, scaling, or interpolation is applied.

The Perez–Driesse System A output and Systems B and C do not receive this correction.

---

## 10. Solar geometry

The final annual analysis uses full azimuth-dependent solar geometry.

For a surface with tilt \(\beta\), solar zenith angle \(\theta_z\), solar azimuth \(\gamma_s\), and surface azimuth \(\gamma_p\), the angle of incidence is based on:

```text
cos(AOI)
=
cos(zenith) cos(tilt)
+
sin(zenith) sin(tilt)
cos(solar azimuth - surface azimuth)
```

The extraterrestrial irradiance normal to the solar beam is calculated from day of year and projected onto the PV plane using the angle of incidence.

An earlier simplified incidence-angle formulation was superseded during the reproducibility reconstruction.

All final weather-condition results use the full azimuth-aware geometry.

---

## 11. Tilted clearness index

The tilted clearness index is calculated as:

```text
kt_tilt =
measured plane-of-array irradiance
/
extraterrestrial irradiance on the tilted plane
```

The physical timestamp is used for the solar-geometry calculation.

No upper limit is imposed on `kt_tilt` in the final weather-condition analysis.

---

## 12. Daytime selection

The annual validation is restricted to daytime observations using:

```text
measured GTI > 0 W/m²
```

The measured irradiance reference is used so that IDA ICE and PVsyst are compared over identical timestamps.

---

## 13. Missing-data handling

For each comparison, records are retained only when the required measured and simulated values are available.

Missing values are not filled using interpolation unless explicitly documented.

The analysis does not use separate model-specific timestamp selections.

---

## 14. Gross-error screening

No residual outliers are removed from the GTI or panel-temperature analyses.

For AC power, gross anomalies are identified using a conservative residual-screening procedure.

Residuals are defined as:

```text
residual = simulated power - measured power
```

A robust standard deviation is estimated from the residual distribution using the median absolute deviation.

A timestamp is classified as a gross anomaly only when:

1. the residual exceeds ten times the robust standard deviation;
2. the condition occurs for both IDA ICE and PVsyst;
3. the residuals have the same sign;
4. the condition occurs simultaneously across all three systems.

This procedure identifies four timestamps:

```text
2 February 2021 12:00
2 February 2021 13:00
2 April 2021 13:00
30 April 2021 13:00
```

The corresponding complete records are removed from the AC-power comparison for:

- measured data;
- IDA ICE;
- PVsyst;
- Systems A, B, and C.

The same cleaned power records are used for:

- annual power validation;
- monthly energy analysis;
- weather-condition power analysis.

A separate sensitivity analysis evaluates the influence of these exclusions.

---

## 15. Validation metrics

The error convention throughout the repository is:

```text
error = simulated - measured
```

A positive bias therefore represents overprediction and a negative bias represents underprediction.

---

### 15.1 Root mean square error

```text
RMSE =
sqrt(mean((simulated - measured)^2))
```

---

### 15.2 Coefficient of variation of RMSE

```text
CV(RMSE) =
RMSE / mean(measured) × 100
```

---

### 15.3 Mean absolute error

```text
MAE =
mean(abs(simulated - measured))
```

---

### 15.4 Normalised mean absolute error

```text
nMAE =
MAE / mean(measured) × 100
```

---

### 15.5 Mean bias error

```text
MBE =
mean(simulated - measured)
```

---

### 15.6 Normalised mean bias error

The final implementation uses:

```text
nMBE =
sum(simulated - measured)
/
sum(measured)
× 100
```

---

### 15.7 Relative error

The final relative-error implementation uses the same aggregate measured-energy reference:

```text
RE =
sum(simulated - measured)
/
sum(measured)
× 100
```

---

### 15.8 Coefficient of determination

R² is calculated from paired measured and simulated observations.

---

## 16. Monthly energy analysis

The cleaned hourly power records are aggregated to monthly energy.

Hourly power is integrated assuming one-hour intervals and converted from Wh to kWh.

Monthly RMSE is calculated across the 12 monthly energy values and normalised by installed system capacity:

```text
kWh/kWp
```

This metric is included to facilitate comparison with previous PV validation studies that report monthly energy errors.

---

## 17. Weather-condition analysis

Power-model performance is evaluated by sky condition using `kt_tilt`.

The nominal categories are:

| Condition | `kt_tilt` range |
|---|---|
| Overcast / very cloudy | `< 0.20` |
| Cloudy | `0.20–0.40` |
| Mixed / broken | `0.40–0.60` |
| Mostly clear | `0.60–0.75` |
| Clear | `≥ 0.75` |

The weather-bin analysis additionally requires:

```text
AOI < 80°
```

CV(RMSE) and nMBE are calculated separately within each category.

Because the observations are not evenly distributed among sky conditions, sample counts are retained and should be considered when interpreting individual bins.

---

## 18. Weather-bin threshold sensitivity

The internal `kt_tilt` boundaries are perturbed by:

```text
±0.05
```

to determine whether the qualitative weather-condition result depends on the exact threshold values.

Two forms of perturbation are evaluated:

1. all internal boundaries shifted together;
2. each internal boundary shifted individually.

The underlying measured data, simulations, geometry, AOI, and `kt_tilt` values are not altered.

Robustness is assessed using:

- changes in CV(RMSE);
- changes in nMBE;
- bias-sign preservation;
- preservation of the lower-CV(RMSE) tool;
- cloudiest-to-clearest CV(RMSE) pattern;
- rank association between clearness and CV(RMSE).

---

## 19. Temporal dependence and bootstrap uncertainty

Hourly PV observations are temporally autocorrelated.

Uncertainty is therefore estimated using a moving-block bootstrap rather than an independent-observation bootstrap.

Autocorrelation diagnostics are used to examine plausible block lengths.

The primary annual inference uses:

```text
30-day blocks
```

with:

```text
5,000 bootstrap replicates
```

Shorter block lengths are evaluated as sensitivity cases.

The primary paired quantity is:

```text
Delta RMSE =
RMSE_IDA ICE - RMSE_PVsyst
```

Therefore:

```text
Delta RMSE < 0 → IDA ICE has lower RMSE
Delta RMSE > 0 → PVsyst has lower RMSE
```

Bootstrap intervals are reported for the paired RMSE differences.

Holm-adjusted p-values are retained as supplementary inferential information.

---

## 20. Measurement uncertainty

The stated measurement uncertainty bounds are:

```text
GTI                ±2%
AC power           ±1%
Panel temperature  ±0.5 °C
```

These are not treated as probability distributions.

Instead, three systematic measurement scenarios are evaluated:

```text
LOW
NOMINAL
HIGH
```

The same perturbation is applied to the full measured series in each scenario.

This represents a bounded calibration/systematic-uncertainty sensitivity analysis rather than independent random measurement noise at every timestamp.

---

## 21. Combined temporal and measurement uncertainty

For each measurement scenario, the 30-day moving-block bootstrap is repeated.

The final combined envelope is constructed from the outer limits of the scenario-specific bootstrap intervals.

The result is described as:

> a moving-block bootstrap interval enveloped over the stated measurement uncertainty bounds

and not as a fully probabilistic joint 95% confidence interval.

---

## 22. Reverse-transposition sensitivity

The complete annual comparison is repeated using Engerer2-derived simulation inputs.

The Engerer2 analysis uses the same:

- measured-data layer;
- power exclusions;
- geometry;
- daytime filtering;
- metrics;
- bootstrap procedure

as the primary Perez–Driesse analysis.

The results are then compared to determine whether:

- the tool with lower RMSE is preserved;
- statistical significance is preserved;
- conclusions remain stable across irradiance-processing methods.

---

## 23. Temporal-aggregation sensitivity

The same cleaned hourly power records are evaluated at three temporal scales:

```text
Hourly  → power [W]
Daily   → energy [kWh/day]
Monthly → energy [kWh/month]
```

The purpose is to determine whether relative IDA ICE and PVsyst performance depends on whether short-term power agreement or aggregated energy prediction is evaluated.

This analysis does not create new sub-hourly simulations.

---

## 24. Sub-hourly limitation

The reviewer suggestion to evaluate shorter simulation intervals, particularly for shading, was considered.

The PVsyst version available for the study was:

```text
PVsyst 8.0.2
```

The available workflow provides hourly simulation results.

Sub-hourly capability is available in a newer PVsyst version that was not available for this work.

Running IDA ICE at a finer resolution while retaining hourly PVsyst output would not provide a matched comparison.

The validation therefore uses the common hourly resolution and separately evaluates sensitivity to daily and monthly aggregation.

---

## 25. Shading analysis

The shading comparison evaluates measured, IDA ICE, and PVsyst AC power.

The principal outputs are:

- hourly clear-day time series;
- hourly partly cloudy time series;
- daily energy differences;
- full-period energy differences;
- full-period error metrics.

The selected clear and partly cloudy days were chosen based on irradiance conditions during the periods when the physical shading objects affected the PV arrays, rather than solely on daily-average weather conditions.

Systems A and C experience the relevant artificial shading primarily during the morning, while System B is affected later in the day.

Both selected case-study days occur after the final positioning of the System A shading object and therefore use the same System A shading geometry.

---

## 26. Auxiliary weather data

Some auxiliary meteorological variables used by IDA ICE originate from Rångedala, approximately 16 km from the PV site.

The principal on-site irradiance and ambient-temperature inputs are measured at the experimental location.

No independent complete alternative auxiliary-weather dataset was available for the validation period.

The spatial uncertainty associated with the Rångedala variables is therefore acknowledged but not assigned an arbitrary numerical perturbation.

Its influence is partly represented in the panel-temperature validation and subsequently propagated through the PV power calculation.

---

## 27. Configuration

Frozen analysis settings are stored centrally in:

```text
config.json
```

This includes parameters such as:

- site coordinates;
- altitude;
- surface tilt;
- surface azimuth;
- timezone;
- weather-bin definitions;
- AOI threshold;
- predefined power exclusions.

Where possible, scripts read these settings rather than duplicating them internally.

---

## 28. Software environment

Python is used for:

- source-data parsing;
- timestamp reconstruction;
- solar geometry;
- statistical analysis;
- uncertainty analysis;
- sensitivity analysis;
- figure generation;
- workbook generation.

Principal Python packages are listed in:

```text
requirements.txt
```

The repository should be reproduced using a fresh Python environment rather than relying on an existing PyCharm project environment.

---

## 29. Reproducibility and provenance

Detailed provenance for non-obvious corrections and source files is provided in:

```text
docs/DATA_PROVENANCE.md
```

Variable definitions are provided in:

```text
docs/DATA_DICTIONARY.md
```

Known limitations are documented in:

```text
docs/KNOWN_LIMITATIONS.md
```

Step-by-step reproduction instructions are provided in:

```text
docs/REPRODUCIBILITY.md
```
