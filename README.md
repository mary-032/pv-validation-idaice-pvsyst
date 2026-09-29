# pv-validation-idaice-pvsyst

Reproducible data-processing, validation, uncertainty, sensitivity, and figure-generation workflow for comparing photovoltaic (PV) simulations in **IDA ICE** and **PVsyst** against measured data.

This repository accompanies the study:

> **Validation of PV Modeling in an Integrated Building Energy Simulation Tool**

The study evaluates the PV model implemented in IDA ICE against measured data from three PV systems and compares its performance with PVsyst. The analysis includes annual unshaded validation, near-field shading cases, uncertainty analysis, and sensitivity tests related to irradiance reconstruction and analysis methodology.

## Study overview

Three PV systems installed at the RISE research facility in Borås, Sweden, were evaluated:

| System | Technology | Installation | Nominal power |
|---|---|---|---:|
| A | Monocrystalline silicon | BAPV | 3.9 kWp |
| B | Monocrystalline silicon with power optimizers | BAPV | 4.8 kWp |
| C | CIGS thin-film | BIPV | 3.3 kWp |

The annual validation uses measured data covering one year. A separate shading experiment evaluates the ability of the two simulation tools to represent near-field shading from physical obstructions.

The principal validation variables are:

- plane-of-array irradiance / effective irradiance;
- panel temperature;
- AC power output.

Model performance is evaluated using RMSE, CV(RMSE), MBE, nMBE, relative error, monthly RMSE normalized by installed capacity, and additional uncertainty and sensitivity analyses.

## Repository structure

```text
pv-validation-idaice-pvsyst/
│
├── README.md
├── requirements.txt
├── config.json
├── .gitignore
│
├── data/
│   ├── measured/
│   │   ├── annual/
│   │   └── shading/
│   ├── ida_ice/
│   ├── pvsyst/
│   ├── weather/
│   └── historical/
│
├── derived_data/
│
├── scripts/
│   ├── audits/
│   └── ...
│
├── results/
│
├── docs/
│   ├── DATA_DICTIONARY.md
│   ├── DATA_PROVENANCE.md
│   ├── KNOWN_LIMITATIONS.md
│   ├── METHODS.md
│   └── REPRODUCIBILITY.md
│
└── archive/
```

### `data/`

Contains the source data used to construct the analysis datasets, including measured data and simulation exports from IDA ICE and PVsyst.

The annual and shading datasets are kept separate where appropriate.

Some source files may be subject to third-party redistribution restrictions. Where a source file cannot be distributed publicly, its provenance and required role in the workflow are documented instead.

### `derived_data/`

Contains the canonical analysis datasets generated from the source files.

These datasets represent the aligned and processed data used by the statistical analysis scripts. They are included separately from the raw/source files so that the statistical results can be reproduced without repeating all software-specific parsing steps.

### `scripts/`

Contains the Python workflow used for data reconstruction, analysis, uncertainty assessment, sensitivity testing, and generation of manuscript figures and tables.

The numbered scripts are intended to be run in approximately the following order:

```text
00  Check required inputs
01  Build canonical datasets
02  Run primary validation analysis
03  Generate Figure 3
04  Build consolidated/master results
05  Statistical uncertainty analysis
06  Add uncertainty results to Tables 4–6
07  Reverse-transposition sensitivity analysis
08  Measurement + temporal uncertainty analysis
09  Temporal-aggregation sensitivity analysis
10  Weather-bin threshold sensitivity analysis
12  Generate shading Figures 4–6
```

Diagnostic scripts associated with specific data-quality investigations are stored under `scripts/audits/`.

### `results/`

Contains generated analysis outputs, including manuscript tables, figures, uncertainty results, sensitivity analyses, and audit outputs.

Where possible, manuscript numbers are generated programmatically rather than entered manually.

### `docs/`

Contains additional documentation describing the analysis methods, variable definitions, data provenance, known limitations, and reproduction procedure.

### `archive/`

Contains superseded or historical analysis code retained for provenance.

Files in this directory are **not part of the final manuscript reproduction workflow** and should not be used to regenerate the published results.

## Analysis workflow

The workflow separates source data, canonical data, and statistical analysis.

Source measurements and simulation exports are first converted into common canonical datasets. The canonical datasets preserve aligned measured and simulated variables together with the timestamps and geometry variables required for the analysis.

The annual analysis uses daytime observations, defined by measured plane-of-array irradiance greater than 0 W/m².

For GTI and panel temperature, no residual outliers are removed.

For AC power, a conservative gross-error screening procedure was applied. A timestamp was identified as anomalous only when power residuals exceeded ten times the robust standard deviation for both IDA ICE and PVsyst, had the same sign, and occurred simultaneously across all three systems. Four hourly timestamps met this criterion and were excluded consistently across measured and simulated AC power data.

The same cleaned hourly power records are used for the annual power validation, monthly energy analysis, and weather-condition analysis.

## Irradiance reconstruction

The primary analysis uses irradiance components derived using the **Perez–Driesse** approach.

An additional **Engerer2** reconstruction is included as a sensitivity case to determine whether conclusions concerning relative IDA ICE and PVsyst performance depend on the irradiance-processing method.

The Perez–Driesse case is the primary/reference analysis. Engerer2 results are treated as sensitivity results rather than as an alternative primary dataset.

## Solar geometry and weather-condition analysis

The tilted clearness index is calculated using measured plane-of-array irradiance and extraterrestrial irradiance projected onto the module plane using full solar geometry, including solar azimuth.

The nominal sky-condition classes are:

| Condition | Tilted clearness index |
|---|---|
| Overcast / very cloudy | `kt_tilt < 0.20` |
| Cloudy | `0.20 ≤ kt_tilt < 0.40` |
| Mixed / broken | `0.40 ≤ kt_tilt < 0.60` |
| Mostly clear | `0.60 ≤ kt_tilt < 0.75` |
| Clear | `kt_tilt ≥ 0.75` |

The weather-bin analysis additionally restricts observations to angles of incidence below 80°.

A dedicated sensitivity analysis shifts the internal bin boundaries by ±0.05 to test whether the qualitative results depend on the exact thresholds.

## Uncertainty and sensitivity analyses

The repository includes several analyses intended to assess the robustness of the comparison between IDA ICE and PVsyst.

Temporal dependence is addressed using a moving-block bootstrap. A 30-day block length is used for the primary annual inference, with shorter block lengths evaluated as sensitivity cases.

Measurement uncertainties are evaluated using systematic low, nominal, and high measurement scenarios corresponding to the stated sensor uncertainty bounds:

- GTI: ±2%;
- AC power: ±1%;
- panel temperature: ±0.5 °C.

The measurement bounds are treated as bounded sensitivity scenarios rather than as assumed probability distributions.

Additional sensitivity analyses examine:

- Perez–Driesse versus Engerer2 irradiance reconstruction;
- hourly, daily, and monthly temporal aggregation;
- weather-bin threshold selection.

## Shading analysis

A separate measurement period from 1 May to 19 June 2023 is used to evaluate near-field shading.

The shading analysis includes:

- a clear-sky case on 5 June 2023;
- a partly cloudy case on 15 May 2023;
- the complete shading measurement period.

The selected daily cases were chosen to represent contrasting irradiance conditions during the periods when the physical shading objects affected the PV arrays.

Both case-study days use the same later System A shading-object configuration.

The case-study figures are intended to illustrate the temporal shading behaviour, while the complete-period analysis provides the broader quantitative comparison.

The available PVsyst version used for the study provides hourly simulation results. Consequently, the shading comparison is performed at a common hourly resolution for both tools.

## Important data-processing notes

Several data-alignment and provenance issues identified during the reproducibility audit are documented explicitly rather than hidden in the processing workflow.

In particular:

- System A measured GTI required a one-hour alignment correction identified through reconstruction of the historical processing workflow.
- The System A Engerer2 PVsyst export exhibited a consistent one-hour displacement across irradiance, panel temperature, and AC power. The complete record was therefore shifted uniformly by +1 h before comparison.
- The corresponding Perez–Driesse PVsyst simulation and Systems B and C did not exhibit this displacement.
- No variable-specific scaling or interpolation was applied as part of this correction.

Further details are provided in `docs/DATA_PROVENANCE.md` and in the audit scripts.

## Configuration

Analysis constants and frozen methodological settings are stored in:

```text
config.json
```

This includes parameters such as site geometry, timezone, weather-bin definitions, analysis thresholds, and predefined gross-error timestamps.

Centralizing these settings helps ensure that the individual analysis scripts use consistent assumptions.

## Installation

Clone the repository and create a Python environment of your choice.

Install the required Python packages with:

```bash
pip install -r requirements.txt
```

The analysis uses packages including NumPy, pandas, SciPy, matplotlib, pvlib, openpyxl, and XlsxWriter.

## Reproducing the analysis

After installing the dependencies and making the required source data available in the expected folders, begin by running:

```bash
python scripts/00_check_inputs.py
```

If all required inputs are present, construct the canonical datasets with:

```bash
python scripts/01_build_canonical_data.py
```

The primary analysis can then be generated with:

```bash
python scripts/02_run_analysis.py
```

Subsequent scripts generate the manuscript outputs and sensitivity analyses.

See `docs/REPRODUCIBILITY.md` for the complete reproduction procedure and expected outputs.

## Software

The simulations evaluated in the study were performed using:

- **IDA ICE 5.1.1.1**
- **PVsyst 8.0.2**

Python is used for reproducible data processing, statistical analysis, uncertainty analysis, and figure generation.

## Data provenance and limitations

The repository distinguishes between:

1. original measurements;
2. software simulation exports;
3. reconstructed/canonical datasets;
4. final analysis outputs.

Known limitations and unresolved sources of uncertainty are documented in `docs/KNOWN_LIMITATIONS.md`.

These include the use of auxiliary meteorological variables from a station approximately 16 km from the PV site and the hourly temporal resolution of the available PVsyst version.

## Citation

If you use this repository, please cite the associated publication.

Publication details and DOI will be added following publication.

A `CITATION.cff` file will also be provided for machine-readable citation information.

## Authors

Marieke Rynoson  
Dalarna University  
Swedish Solar Electricity Research Centre (SOLVE)

Co-author and affiliation information will be added with the final publication metadata.

## License

A software and data license will be specified after confirming redistribution conditions for all included datasets and proprietary-software-derived files.

Until then, inclusion of a file in this repository should not be interpreted as granting rights beyond those explicitly stated by its original owner or provider.
