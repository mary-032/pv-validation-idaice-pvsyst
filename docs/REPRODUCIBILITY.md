# pv-validation-idaice-pvsyst
Reproducible data-processing, validation, uncertainty, sensitivity, and figure-generation workflow for comparing PV simulations in IDA ICE and PVsyst against measured data.
# Reproducibility guide

This document describes how to reproduce the data processing, statistical analysis, uncertainty analyses, sensitivity analyses, and figures associated with the PV validation study.

The workflow is designed so that the analysis can be reproduced at two levels:

1. **full reconstruction**, beginning with the original measurements and simulation exports;
2. **analysis-only reproduction**, beginning with the canonical datasets.

The second option is useful when proprietary or third-party source files cannot be redistributed.

---

## 1. Repository

Clone the repository:

```bash
git clone https://github.com/mary-032/pv-validation-idaice-pvsyst.git
```

Enter the repository:

```bash
cd pv-validation-idaice-pvsyst
```

---

## 2. Python environment

A clean Python environment is recommended.

For example:

```bash
python -m venv .venv
```

### Windows

Activate with:

```bash
.venv\Scripts\activate
```

### Linux/macOS

Activate with:

```bash
source .venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

The principal dependencies are:

```text
numpy
pandas
matplotlib
scipy
pvlib
openpyxl
xlsxwriter
```

The package versions used during repository preparation are listed in `requirements.txt`.

---

## 3. Configuration

The central analysis configuration is:

```text
config.json
```

Do not modify this file when attempting to reproduce the published results.

It contains frozen settings including:

- site location;
- altitude;
- module tilt and azimuth;
- timezone;
- weather-condition bins;
- AOI threshold;
- power-exclusion timestamps.

Changes to `config.json` constitute a new analysis scenario rather than a reproduction of the archived results.

---

## 4. Repository data layers

The intended public repository separates data into three conceptual layers.

### Source data

```text
data/
```

Contains original measurements, simulation exports, weather/input data, and historical provenance files where redistribution is permitted.

### Canonical data

```text
derived_data/
```

Contains analysis-ready datasets generated from the source files.

### Results

```text
results/
```

Contains statistical outputs, uncertainty results, sensitivity results, tables, and figures.

---

## 5. Repository path structure

The active analysis workflow uses the public repository structure directly. All active Python scripts determine the repository root from their own file location and use repository-relative paths; no user-specific absolute paths are required.

The main path convention is:

- `data/` contains source and provenance inputs used by the analysis.
- `derived_data/` contains canonical datasets generated from the source inputs.
- `results/` contains statistical results, sensitivity analyses, summary tables, and publication figures.
- `scripts/` contains the active reproducibility workflow.
- `scripts/audits/` contains diagnostic and provenance audits that support specific preprocessing decisions but are not required for routine regeneration of the main results.
- `config.json` in the repository root contains shared analysis settings.
- `archive/` contains superseded or historical material and is not part of the active reproducibility workflow.

The active scripts no longer depend on the legacy working-directory folders used during development, such as `01_source_inputs/`, `02_canonical_data/`, `02a_canonical_data_Engerer2/`, `03_analysis_output/`, or `03a_analysis_output_Engerer2/`. These names may occur in archived historical material but should not be used when reproducing the published analysis.

The recommended procedure is to run the scripts from the repository root. Because each active script resolves the repository root from its own location, the workflow does not depend on the current working directory.

Generated files should not be manually moved between stages. Each script reads the outputs of the preceding stages from `derived_data/` or `results/` and writes its own outputs to the corresponding repository directory.

---

# Part A — Full reconstruction

## 6. Required source files

A full reconstruction requires access to the original measurement and simulation files.

Some source files may not be publicly redistributed because they originate from third parties or proprietary software.

See:

```text
data/README.md
docs/DATA_PROVENANCE.md
```

for provenance and expected filenames.

---

## 7. Annual measured data

The principal original annual workbook is:

```text
RISE_raw10min_389.xlsx
```

Physical measurement period:

```text
1 June 2020 – 31 May 2021
```

Original resolution:

```text
10 minutes
```

The workbook contains the measured data for Systems A, B, and C.

---

## 8. Historical measured-data reconstruction file

The reconstruction also uses the historical processed workbook:

```text
Results_PVsyst_E2_hour.xlsx
```

Only the required historically processed measured-data layer is used.

Older simulation columns in this workbook are not authoritative simulation results.

---

## 9. Perez–Driesse simulation files

The primary annual IDA ICE exports are:

```text
Syst3_PD.xlsx
Syst8_PD.xlsx
Syst9_PD.xlsx
```

The primary annual PVsyst exports are:

```text
PVsyst_3_PD_h.xlsx
PVsyst_8_PD_h.xlsx
PVsyst_9_PD_h.xlsx
```

---

## 10. Engerer2 sensitivity files

The IDA ICE Engerer2 exports are:

```text
Syst3_E2.xlsx
Syst8_E2.xlsx
Syst9_E2.xlsx
```

The PVsyst Engerer2 exports are:

```text
PVsyst_3_E2_h.xlsx
PVsyst_8_E2_h.xlsx
PVsyst_9_E2_h.xlsx
```

---

## 11. Shading source files

The full shading reconstruction requires:

- measured shading-period data;
- IDA ICE shading simulation exports;
- PVsyst shading simulation exports;
- any supporting source files explicitly listed by `00_check_inputs.py`.

The complete shading period is:

```text
1 May 2023 – 19 June 2023
```

---

## 12. Check the inputs

Before running any analysis, execute:

```bash
python scripts/00_check_inputs.py
```

This script should identify:

- required files that are present;
- missing files;
- unexpected source paths where applicable.

Do not continue to the full reconstruction if required authoritative inputs are missing.

---

## 13. Build the canonical datasets

Run:

```bash
python scripts/01_build_canonical_data.py
```

This step performs the principal reconstruction and alignment operations.

These include, where applicable:

- parsing measured annual data;
- parsing IDA ICE exports;
- parsing PVsyst exports;
- reconstructing hourly timestamps;
- civil-time handling;
- physical timestamp reconstruction;
- System A measured-GTI alignment;
- solar-position calculations;
- angle-of-incidence calculations;
- extraterrestrial tilted irradiance;
- tilted clearness index;
- shading-data alignment.

The resulting canonical datasets should contain:

```text
3 systems
8,736 unique annual analysis timestamps
26,208 annual system rows
```

before variable-specific daytime filtering.

The exact output filenames should be checked against the active Script 01 version.

---

# Part B — Analysis-only reproduction

## 14. Starting from canonical data

If the original proprietary/source files are unavailable, the statistical analysis can begin from the canonical datasets in:

```text
derived_data/
```

or from the corresponding legacy working-directory locations where applicable.

The canonical datasets should be treated as the authoritative analysis inputs.

Do not substitute older processed workbooks or archived simulation results.

---

# Part C — Primary analysis

## 15. Run the primary validation

Execute:

```bash
python scripts/02_run_analysis.py
```

This generates the principal validation outputs, including:

- annual GTI metrics;
- panel-temperature metrics;
- annual AC-power metrics;
- monthly RMSE per kWp;
- weather-condition metrics;
- power-exclusion audit;
- shading results.

The primary annual analysis uses the Perez–Driesse simulation case.

---

## 16. Expected annual selection rules

The primary analysis uses:

```text
measured GTI > 0 W/m²
```

for daytime selection.

### GTI

No residual outliers are trimmed.

### Panel temperature

No residual outliers are trimmed.

### AC power

Four gross-error timestamps are excluded:

```text
2021-02-02 12:00
2021-02-02 13:00
2021-04-02 13:00
2021-04-30 13:00
```

The complete records are excluded consistently from measured, IDA ICE, and PVsyst power.

---

## 17. Weather-condition record selection

The weather-condition analysis uses:

```text
same cleaned AC-power records
+
valid kt_tilt
+
AOI < 80°
```

No upper limit is imposed on `kt_tilt`.

The nominal bins are:

```text
<0.20       Overcast / very cloudy
0.20–0.40   Cloudy
0.40–0.60   Mixed / broken
0.60–0.75   Mostly clear
>=0.75      Clear
```

---

# Part D — Figures and consolidated results

## 18. Generate Figure 3

Run:

```bash
python scripts/03_make_figure3_combined.py
```

The final combined figure contains:

```text
(a) CV(RMSE)
(b) nMBE
```

by weather condition and system.

The final visual convention is:

```text
IDA ICE → blue
PVsyst  → green
```

---

## 19. Build the master results file

Run:

```bash
python scripts/04_build_master_results.py
```

The resulting workbook consolidates the numerical outputs used in the manuscript.

This file is intended as the principal numerical audit source for manuscript tables and figures.

---

# Part E — Statistical uncertainty

## 20. Moving-block bootstrap

Run:

```bash
python scripts/05_statistical_uncertainty.py
```

The primary annual inference uses:

```text
30-day blocks
5,000 bootstrap replicates
```

The script also evaluates alternative block lengths to assess sensitivity to the assumed temporal dependence.

Principal outputs include:

- autocorrelation diagnostics;
- metric confidence intervals;
- paired IDA ICE versus PVsyst RMSE comparisons;
- Holm-adjusted supplementary p-values;
- power-exclusion sensitivity;
- weather-bin uncertainty;
- shading uncertainty.

---

## 21. Build uncertainty-enhanced Tables 4–6

Run:

```bash
python scripts/06_build_tables4_6_uncertainty.py
```

This script adds uncertainty and paired comparison information to the principal annual validation tables without replacing the original point estimates.

---

# Part F — Reverse-transposition sensitivity

## 22. Run the Engerer2 sensitivity analysis

Execute:

```bash
python scripts/07_reverse_transposition_sensitivity.py
```

This constructs and analyses the alternative Engerer2 scenario.

The measured data, geometry, exclusions, filtering, and statistical methods should remain identical to the primary Perez–Driesse analysis.

### System A correction

The script applies a uniform:

```text
+1 h
```

shift to the complete System A Engerer2 PVsyst output.

The correction applies jointly to:

- irradiance;
- panel temperature;
- AC power.

Systems B and C receive no shift.

---

## 23. Audit scripts

The timing/provenance investigation is retained in:

```text
scripts/audits/
```

These scripts are not required for routine reproduction of the final results.

They document the evidence supporting the System A Engerer2 timing correction.

Typical audit scripts include:

```text
07a_audit_Engerer2_SystemA_GTI.py
07b_audit_PVsyst_clock_and_lag.py
07c_audit_PVsyst_export_metadata.py
```

Run these only when independently reviewing the provenance decision.

---

# Part G — Combined measurement and temporal uncertainty

## 24. Measurement uncertainty analysis

Execute:

```bash
python scripts/08_combined_measurement_temporal_uncertainty.py
```

The measurement bounds are:

```text
GTI                ±2%
AC power           ±1%
Panel temperature  ±0.5 °C
```

Each quantity is evaluated using:

```text
LOW
NOMINAL
HIGH
```

systematic measurement scenarios.

For each scenario, the 30-day moving-block bootstrap is repeated.

The final outer limits are reported as a combined uncertainty envelope.

Do not interpret this envelope as a fully probabilistic joint 95% confidence interval.

---

# Part H — Temporal aggregation

## 25. Run the aggregation sensitivity

Execute:

```bash
python scripts/09_temporal_aggregation_sensitivity.py
```

The same cleaned power records are compared as:

```text
Hourly power
Daily energy
Monthly energy
```

This analysis tests whether the relative IDA ICE/PVsyst performance depends on temporal scale.

---

# Part I — Weather-bin threshold sensitivity

## 26. Run the bin-edge sensitivity analysis

Execute:

```bash
python scripts/10_weather_bin_edge_sensitivity.py
```

This shifts the internal tilted-clearness-index bin boundaries by:

```text
±0.05
```

both:

- simultaneously;
- one boundary at a time.

The analysis verifies whether the qualitative weather-dependent results depend strongly on the nominal threshold definitions.

---

# Part J — Shading figures

## 27. Generate Figures 4–6

Execute:

```bash
python scripts/11_make_figures4_5_6_shading.py
```

The script generates plots for:

```text
System A
System B
System C
```

for:

```text
5 June 2023  → clear
15 May 2023  → partly cloudy
```

The visual convention is:

```text
Measured → neutral dark grey
IDA ICE  → blue, distinct line/marker style
PVsyst   → green, distinct line/marker style
```

The IDA ICE and PVsyst styles are intentionally distinguishable in black-and-white printing.

Individual panels are also exported so that simulation screenshots or other figure material can be inserted between the time-series plots during manuscript layout.

---

# Part K — Key QA checks

## 28. Annual canonical-data checks

A successful annual reconstruction should preserve:

```text
Systems: A, B, C
Unique annual timestamps: 8,736
Total system/timestamp rows: 26,208
```

---

## 29. System A GTI check

The final primary System A GTI analysis should use the documented +1 h measured-GTI alignment.

An unexpectedly very large System A GTI error may indicate that the correction has not been applied.

---

## 30. Engerer2 System A check

The corrected System A Engerer2 PVsyst analysis should apply:

```text
+1 h uniform record shift
```

An anomalously large System A PVsyst irradiance RMSE in the Engerer2 case may indicate that the timing correction has not been applied.

---

## 31. Weather-bin checks

The final weather analysis should:

- use full azimuth-dependent AOI;
- apply `AOI < 80°`;
- impose no upper cap on `kt_tilt`;
- retain the five configured bins.

If the weather-bin distribution differs substantially from the archived results, verify the solar-geometry calculation before interpreting the result.

---

## 32. Power exclusions

The power-exclusion audit should confirm removal of exactly the four predefined timestamps.

No additional residual trimming should occur in the primary power analysis.

---

# Part L — Output verification

## 33. Numerical consistency

Before using regenerated results in the manuscript:

1. compare Tables 4–6 against the consolidated master-results file;
2. check monthly RMSE values;
3. check Figure 3 source values;
4. check shading-period energy values;
5. confirm uncertainty intervals;
6. verify that sensitivity analyses use the intended primary or alternative irradiance scenario.

Do not manually copy numbers from earlier workbooks without checking them against the current scripted results.

---

## 34. Figure verification

Publication figures should be generated from the final scripted outputs.

Check:

- axis labels;
- units;
- system labels;
- IDA ICE/PVsyst color consistency;
- black-and-white distinguishability;
- output resolution.

Where figures are assembled manually with simulation screenshots, retain the script-generated plots as the numerical source.

---

# Part M — Clean-clone reproduction test

## 35. Before a formal repository release

Before creating the final repository release, perform a clean-clone test.

Recommended procedure:

1. clone the repository into a new directory;
2. create a new Python virtual environment;
3. install only `requirements.txt`;
4. add the permitted source files in the documented locations;
5. run `00_check_inputs.py`;
6. execute the scripts in numerical order;
7. compare the outputs with the archived master results;
8. confirm that no script depends on:
   - absolute Windows paths;
   - files outside the repository;
   - the original PyCharm project;
   - manually edited intermediate files.

The clean-clone test should be completed before assigning a permanent repository release or archival DOI.

---

# Part N — Reproduction without proprietary software

## 36. Statistical reproducibility

Access to IDA ICE and PVsyst is not required to reproduce the statistical analysis if the canonical datasets are available.

A user can begin from:

```text
derived_data/
```

and run the statistical and plotting scripts.

This reproduces:

- annual metrics;
- monthly metrics;
- weather-bin analysis;
- uncertainty analyses;
- sensitivity analyses that operate on existing simulation results;
- publication plots.

---

## 37. Full simulation reproducibility

Reproducing the original simulations themselves requires access to compatible versions of:

```text
IDA ICE
PVsyst
```

and any project/model/weather files that can legally be shared.

The public repository therefore distinguishes between:

```text
simulation reproducibility
```

and:

```text
analysis reproducibility
```

The canonical datasets are provided to maximise the latter even when proprietary software access is unavailable.

---

# Part O — Troubleshooting

## 38. Missing file error

Run:

```bash
python scripts/00_check_inputs.py
```

and verify the expected filename and path.

Do not rename source files arbitrarily without also updating the corresponding script/configuration.

---

## 39. Unexpected number of annual rows

Verify:

- IDA ICE `Time = 0` initial state handling;
- PVsyst hourly row order;
- timestamp reconstruction;
- daylight-saving-time handling;
- system joins.

---

## 40. Unexpected System A irradiance error

Check the documented System A measured-GTI alignment correction.

---

## 41. Unexpected Engerer2 System A results

Check the uniform +1 h PVsyst timing correction.

---

## 42. Different weather-bin results

Check:

- physical timestamp reconstruction;
- solar azimuth;
- surface azimuth;
- AOI calculation;
- extraterrestrial irradiance;
- AOI < 80° filtering;
- nominal `kt_tilt` thresholds.

---

## 43. Reproduction questions

When reporting a reproduction problem, record:

- operating system;
- Python version;
- package versions;
- script name;
- input-file versions;
- console output;
- traceback/error message;
- whether the run started from original source files or canonical data.

This information is generally sufficient to distinguish software-environment problems from data-provenance problems.
