# pv-validation-idaice-pvsyst
Reproducible data-processing, validation, uncertainty, sensitivity, and figure-generation workflow for comparing PV simulations in IDA ICE and PVsyst against measured data.
# Data

This directory contains the source data required to reconstruct the canonical datasets used in the validation of PV simulations performed with IDA ICE and PVsyst.

The repository distinguishes between original measurements, simulation outputs, weather/input data, historical processing files, and derived canonical datasets.

Processed datasets generated from these sources are stored separately in `derived_data/`.

## Directory structure

```text
data/
│
├── measured/
│   ├── annual/
│   └── shading/
│
├── ida_ice/
│
├── pvsyst/
│
├── weather/
│
├── historical/
│
└── README_data.md
```

---

## `measured/annual/`

Contains the measured annual validation data from the RISE PV research installation in Borås, Sweden.

The principal source workbook used in the reconstruction is:

```text
RISE_raw10min_389.xlsx
```

The measurement period is:

```text
1 June 2020 – 31 May 2021
```

The original measurements are recorded at 10-minute resolution and include data for the three evaluated PV systems.

Principal measured variables include:

- plane-of-array irradiance;
- panel temperature;
- AC power;
- ambient temperature.

The annual analysis is ultimately performed at hourly resolution.

### Systems

```text
System A / RISE system 3
3.9 kWp
monocrystalline silicon
BAPV

System B / RISE system 8
4.8 kWp
monocrystalline silicon
power optimizers
BAPV

System C / RISE system 9
3.3 kWp
CIGS thin-film
BIPV
```

The precise source-column mapping is documented in `docs/DATA_DICTIONARY.md`.

---

## `measured/shading/`

Contains measurements from the dedicated shading experiment.

The analyzed period is:

```text
1 May 2023 – 19 June 2023
```

The shading measurements were originally recorded at higher temporal resolution and are aggregated to hourly values for the matched IDA ICE/PVsyst comparison.

The shading analysis includes:

- 5 June 2023 as the clear-sky case;
- 15 May 2023 as the partly cloudy case;
- the complete measurement period.

The selected daily cases represent contrasting irradiance conditions during the periods in which the physical shading objects affected the PV arrays.

The daily cases are illustrative. Quantitative shading performance is additionally evaluated over the complete measurement period.

---

## `ida_ice/`

Contains exports and, where redistribution is permitted, supporting files from the IDA ICE simulations.

The annual simulations include both the primary Perez–Driesse irradiance-input case and the Engerer2 sensitivity case.

Known annual result files include:

```text
Perez–Driesse
--------------
Syst3_PD.xlsx
Syst8_PD.xlsx
Syst9_PD.xlsx

Engerer2
--------
Syst3_E2.xlsx
Syst8_E2.xlsx
Syst9_E2.xlsx
```

System correspondence is:

```text
Syst3 → System A
Syst8 → System B
Syst9 → System C
```

The IDA ICE exports include separate result series for:

- produced power;
- panel temperature;
- effective irradiance.

Where multiple panel-temperature or effective-irradiance series exist within a system export, the canonical-data builder applies the finalized aggregation procedure documented in the code.

Shading-related IDA ICE exports are also stored under this directory where redistribution is permitted.

Some raw `.prn` files were used during reconstruction and auditing of the shading simulations.

---

## `pvsyst/`

Contains PVsyst simulation exports and, where redistribution is permitted, supporting project files.

The annual simulations include the primary Perez–Driesse case and the Engerer2 sensitivity case.

Known annual exports include:

```text
Perez–Driesse
--------------
PVsyst_3_PD_h.xlsx
PVsyst_8_PD_h.xlsx
PVsyst_9_PD_h.xlsx

Engerer2
--------
PVsyst_3_E2_h.xlsx
PVsyst_8_E2_h.xlsx
PVsyst_9_E2_h.xlsx
```

The relevant exported quantities include:

- grid/AC power;
- array temperature;
- effective irradiance.

PVsyst export timestamps are reconstructed using row order rather than relying on the arbitrary calendar years contained in individual exports.

### System A Engerer2 timing issue

A reproducibility audit identified a consistent one-hour displacement in the System A Engerer2 PVsyst export.

The displacement affected all three evaluated output variables:

```text
effective irradiance
panel temperature
AC power
```

The complete System A Engerer2 PVsyst record is therefore shifted uniformly by +1 h before matching with the canonical analysis timestamps.

No scaling or interpolation is performed.

The same issue was not found for:

- System A Perez–Driesse;
- System B;
- System C.

See `docs/DATA_PROVENANCE.md` and `scripts/audits/` for the complete audit trail.

---

## `weather/`

Contains weather and irradiance-processing inputs used to construct the simulation weather files, where redistribution is permitted.

The primary analysis uses irradiance components reconstructed using the Perez–Driesse method.

An Engerer2 reconstruction is retained as a sensitivity case.

The two irradiance-processing scenarios are kept separate because the Perez–Driesse case is the primary analysis and Engerer2 is used only to evaluate methodological sensitivity.

The simulations also use auxiliary meteorological information.

Some auxiliary weather variables originate from the Rångedala meteorological station, approximately 16 km from the PV measurement site.

These variables primarily influence thermal and environmental boundary conditions rather than replacing the measured on-site irradiance used as the principal solar input.

The use of off-site auxiliary weather data is documented as a study limitation.

### Unavailable historical file

Metadata from the System A Engerer2 PVsyst export reference:

```text
Ekås_Custom_E2.MET
```

The original `.MET` file is no longer available.

The repository does not attempt to reconstruct or fabricate this file.

Its role and the associated timing investigation are documented in `docs/DATA_PROVENANCE.md`.

---

## `historical/`

Contains historical processed datasets required for reconstruction or provenance but not used as authoritative simulation outputs in the final analysis.

An important historical workbook is:

```text
Results_PVsyst_E2_hour.xlsx
```

This workbook contains a historically processed measured-data layer used during reconstruction of the original analysis workflow.

Only the required measured-data columns are used from this workbook.

Older Engerer2 simulation columns contained in the workbook are not used as the final simulation results.

The authoritative annual simulation outputs are the separate Perez–Driesse and Engerer2 files stored in the IDA ICE and PVsyst source directories.

---

## Canonical datasets

The source files in this directory are converted into analysis-ready datasets by:

```bash
python scripts/01_build_canonical_data.py
```

The resulting canonical datasets are stored in:

```text
derived_data/
```

The canonical annual dataset contains one common analysis layer for:

- measured values;
- IDA ICE outputs;
- PVsyst outputs;
- timestamps;
- solar geometry;
- tilted clearness index;
- other variables required by the analysis.

This separation allows subsequent statistical analyses to operate on one documented dataset rather than repeatedly parsing proprietary-software exports.

---

## Timestamp handling

The physical annual measurement period is:

```text
1 June 2020 – 31 May 2021
```

Historical processing used a synthetic January–December 2021 analysis timeline.

The canonical-data workflow therefore distinguishes between the analysis timestamp and the physical timestamp used for solar geometry.

The physical timestamps are used when solar position and extraterrestrial irradiance depend on the true day of year.

The RISE logger timing was evaluated during the reproducibility reconstruction and was found to be most consistent with civil time in:

```text
Europe/Stockholm
```

Daylight-saving-time handling is implemented explicitly by the canonical-data builder.

---

## System A measured GTI alignment

During reconstruction of the annual dataset, the measured GTI series for System A was found to be displaced by one hour relative to the simulation outputs and the historical analysis layer.

The finalized annual preprocessing therefore applies a +1 h assignment correction to the System A measured GTI series.

This correction is documented explicitly because it materially affects the System A irradiance-validation results.

Systems B and C use the shared measured GTI series without this correction.

See `docs/DATA_PROVENANCE.md` for the reconstruction evidence.

---

## Data exclusions

Nighttime observations are excluded from the annual validation by retaining observations where measured plane-of-array irradiance is greater than 0 W/m².

No residual outliers are removed from the GTI or panel-temperature datasets.

For AC power, four gross-error timestamps are excluded consistently across measured data and both simulation tools:

```text
2 February 2021 12:00
2 February 2021 13:00
2 April 2021 13:00
30 April 2021 13:00
```

These timestamps were identified using a conservative residual-screening criterion requiring simultaneously extreme, same-direction residuals for IDA ICE and PVsyst across all three systems.

The exclusions apply to the annual AC-power analysis and analyses derived from the same cleaned power records.

---

## Redistribution and licensing

Not every file used in the original research workflow is necessarily eligible for public redistribution.

Files originating from:

- RISE;
- IDA ICE;
- PVsyst;
- external meteorological providers;

should only be included in the public repository where redistribution rights are clear.

If a required source file cannot be distributed, the repository should retain:

- its expected filename;
- its purpose;
- its provenance;
- the columns or variables required from it;
- instructions for obtaining or recreating it where possible.

Do not replace unavailable original files with reconstructed files unless the reconstruction is explicitly documented.

---

## Source versus derived data

Files under `data/` should be treated as source or provenance material.

Files generated by the Python workflow belong under:

```text
derived_data/
```

or:

```text
results/
```

This distinction is intentional.

Source files should not be silently edited to make them conform to the analysis. Any required correction, alignment, filtering, or transformation should instead be performed programmatically and documented in the analysis scripts.
