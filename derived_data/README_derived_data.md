# Derived data

This directory contains the canonical and analysis-ready datasets generated from the original measurements, IDA ICE exports, PVsyst exports, and associated processing inputs.

These files are not raw measurements and should not be treated as original source data.

They are the processed datasets used by the statistical analysis scripts in this repository.

---

## Purpose

The derived-data layer provides a reproducible interface between:

```text
raw/source data
```

and:

```text
statistical analysis
```

The source files originate from several formats and software environments, including:

- measured RISE data;
- IDA ICE exports;
- PVsyst exports;
- historical processed workbooks;
- reconstructed solar-geometry inputs.

Rather than requiring every downstream script to parse these sources independently, the workflow first converts them into common canonical datasets.

This makes the analysis:

- easier to audit;
- less dependent on proprietary software formats;
- easier to reproduce;
- less vulnerable to inconsistent preprocessing between scripts.

---

## Canonical-data principle

The canonical datasets contain aligned measured and simulated values on a common analysis timeline.

Where appropriate, they also contain:

- system identifiers;
- nominal system capacity;
- physical timestamps;
- analysis timestamps;
- solar geometry;
- angle of incidence;
- extraterrestrial irradiance;
- tilted clearness index;
- provenance fields;
- documented timing corrections.

The statistical scripts should use these canonical datasets rather than returning to the original simulation exports unless the source reconstruction itself is being audited.

---

## Expected files

The exact filenames may evolve slightly as the repository structure is finalised, but the principal derived datasets are expected to include:

```text
annual_unshaded_analysis.csv
shading_analysis.csv
```

Additional sensitivity datasets may also be included, for example:

```text
annual_unshaded_analysis_Engerer2.csv
```

where appropriate.

---

## `annual_unshaded_analysis.csv`

This is the primary annual canonical dataset.

It represents the Perez–Driesse baseline analysis and contains aligned values for:

- measured data;
- IDA ICE simulation results;
- PVsyst simulation results;
- Systems A, B, and C.

The physical measurement period is:

```text
1 June 2020 – 31 May 2021
```

The common annual analysis contains:

```text
8,736 unique hourly timestamps
3 systems
26,208 system/timestamp rows
```

before variable-specific daytime filtering.

Typical columns include:

```text
system
timestamp
physical_timestamp
kWp

GTI_measured_Wm2
GTI_IDA_Wm2
GTI_PVsyst_Wm2

Tp_measured_C
Tp_IDA_C
Tp_PVsyst_C

P_measured_W
P_IDA_W
P_PVsyst_W

AOI_deg
kt_tilt
```

The exact column definitions are documented in:

```text
docs/DATA_DICTIONARY.md
```

---

## `annual_unshaded_analysis_Engerer2.csv`

Where included, this file contains the annual canonical dataset for the Engerer2 reverse-transposition sensitivity analysis.

It uses the same:

- measured-data layer;
- timestamps;
- solar geometry;
- system identifiers;
- filtering framework;
- power-exclusion rules

as the primary Perez–Driesse analysis.

The purpose of this dataset is to isolate the effect of the alternative irradiance-processing method.

It should not be treated as a second primary dataset.

### System A PVsyst timing correction

The System A Engerer2 PVsyst export contains a documented one-hour temporal displacement.

The canonical Engerer2 dataset therefore applies a uniform:

```text
+1 h
```

shift to the complete System A PVsyst record.

The shift is applied jointly to:

- effective irradiance;
- panel temperature;
- AC power.

No scaling or interpolation is applied.

Systems B and C receive no such shift.

See:

```text
docs/DATA_PROVENANCE.md
```

for the audit trail.

---

## `shading_analysis.csv`

This is the canonical dataset for the shading experiment.

The analyzed period is:

```text
1 May 2023 – 19 June 2023
```

The dataset contains aligned hourly values for:

- measured AC power;
- IDA ICE AC power;
- PVsyst AC power;
- system identifiers;
- timestamps;
- shading-case metadata where applicable.

The principal case-study days are:

```text
5 June 2023  → clear
15 May 2023  → partly cloudy
```

The complete period is also used for quantitative shading validation.

The individual case-study days are illustrative and do not replace the full-period analysis.

---

## Data-processing decisions already represented

The derived datasets may already contain the consequences of documented preprocessing steps.

These include, where applicable:

- hourly aggregation;
- timestamp reconstruction;
- civil-time interpretation;
- physical-time reconstruction;
- System A measured-GTI alignment;
- System A Engerer2 PVsyst timing correction;
- solar-geometry reconstruction;
- angle-of-incidence calculation;
- tilted clearness-index calculation.

These corrections should not be applied a second time by downstream analysis scripts.

---

## What is not removed from the canonical data

The canonical annual dataset is intended to preserve the common aligned records before variable-specific statistical selection.

In particular:

- GTI residual outliers are not removed;
- panel-temperature residual outliers are not removed;
- power records are not broadly trimmed based on residual magnitude.

The four predefined AC-power gross-error timestamps are applied by the analysis workflow where required.

This distinction allows the effect of those exclusions to be audited separately.

---

## Daytime filtering

The annual statistical validation uses:

```text
GTI_measured_Wm2 > 0
```

to define daytime observations.

The canonical dataset itself may contain nighttime records.

This allows downstream analyses to apply the same documented selection rule explicitly.

---

## Weather-condition variables

The annual canonical dataset includes or supports calculation of the variables needed for the weather-condition analysis.

The principal quantity is:

```text
kt_tilt
```

defined as measured plane-of-array irradiance divided by extraterrestrial irradiance projected onto the tilted PV plane.

The final weather analysis additionally uses:

```text
AOI_deg < 80
```

The nominal weather-condition classes are:

```text
kt_tilt < 0.20       Overcast / very cloudy
0.20–0.40            Cloudy
0.40–0.60            Mixed / broken
0.60–0.75            Mostly clear
>=0.75               Clear
```

No upper cap is applied to `kt_tilt`.

---

## Relationship to the analysis scripts

The derived datasets are used by the downstream scripts for:

- annual validation;
- monthly energy analysis;
- weather-condition analysis;
- uncertainty analysis;
- paired IDA ICE versus PVsyst comparison;
- reverse-transposition sensitivity;
- measurement-uncertainty sensitivity;
- temporal-aggregation sensitivity;
- weather-bin threshold sensitivity;
- figure generation.

This means a researcher who has access to the canonical datasets does not need access to the original IDA ICE or PVsyst project files to reproduce the statistical analysis.

---

## Reproducing the derived data

The canonical datasets are generated using:

```bash
python scripts/01_build_canonical_data.py
```

A full reconstruction requires the original source files documented in:

```text
data/README.md
```

and:

```text
docs/DATA_PROVENANCE.md
```

Before reconstruction, run:

```bash
python scripts/00_check_inputs.py
```

to verify that the required source files are available.

---

## Reproducing the analysis without source files

If the canonical datasets are provided in this directory, the main statistical analysis can begin from:

```bash
python scripts/02_run_analysis.py
```

without regenerating the proprietary-software exports.

This distinction is important because access to IDA ICE and PVsyst is not required to reproduce the statistical analysis once the canonical datasets have been created.

---

## Authoritative status

For the final repository release:

```text
annual_unshaded_analysis.csv
```

should be treated as the authoritative Perez–Driesse annual analysis dataset.

Where included:

```text
annual_unshaded_analysis_Engerer2.csv
```

should be treated as the authoritative Engerer2 sensitivity dataset.

```text
shading_analysis.csv
```

should be treated as the authoritative shading-analysis dataset.

Older processed workbooks and historical intermediate files should not be substituted for these datasets.

---

## Provenance

The derived datasets are generated from multiple source layers, including measured and simulated data.

Important non-obvious provenance decisions are documented in:

```text
docs/DATA_PROVENANCE.md
```

These include:

- physical versus analysis timestamps;
- System A measured-GTI timing correction;
- Perez–Driesse versus Engerer2 status;
- System A Engerer2 PVsyst timing correction;
- historical processed measured-data usage;
- shading-object configuration changes;
- AC-power gross-error screening.

---

## Editing policy

Derived-data files should not be manually edited to alter analysis results.

If a correction is required:

1. update the appropriate source-processing script;
2. regenerate the canonical dataset;
3. document the change;
4. rerun downstream analyses.

Manual spreadsheet edits should not be part of the reproducible workflow.

---

## Versioning

Changes to the canonical datasets that affect manuscript results should be committed together with:

- the script change that generated them;
- updated result files;
- a clear Git commit message describing the change.

For formal publication or archival release, the canonical datasets should correspond exactly to the tagged repository version associated with the manuscript.
