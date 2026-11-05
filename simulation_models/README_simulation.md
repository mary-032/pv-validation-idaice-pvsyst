# Simulation Models

> **Revision 2 provenance status (5 November 2026):** These are preserved model and supporting files, not proof that every original model configuration can be independently re-executed. The exact software build and source-model input parameter records require author verification; the archived original PVsyst 2023 shading project geometries could not be fully authenticated. The revised annual AC comparison uses IDA ICE *hourly electrical-system Produced power Table* exports in the Step 26–28 reconstruction, rather than simply the historical `inverter_o` or sampled `.prn` channels. See [Revision 2 result map](../docs/REVISION2_RESULT_MAP.md) and [Revision 2 reproduction guide](../docs/REVISION2_REPRODUCIBILITY.md). Working parameter spreadsheets should not be represented as independently checked manufacturer/source configuration records.


This folder contains the simulation model files and supporting information used for the comparison of IDA ICE and PVsyst.

The simulation files are organised into two main cases:

- `annual/` – models and weather files used for the full-year unshaded simulations
- `shaded/` – models and weather files used for the partial-shading simulations

Within these folders, IDA ICE and PVsyst files are stored separately. See the individual README files in each subfolder for further information on the model and weather-file structure.

## System information

The `system_information/` folder contains supporting documentation used when setting up the simulation models:

- `RISE_2021_slutrapport-systemtester-solel.pdf` – the published RISE report describing the tested PV systems
- `PVparameters_IDA ICE.xlsx` – working notes containing the PV module parameters used in the IDA ICE models
- `InverterParameters_IDA ICE.xlsx` – working notes containing inverter and optimizer parameters used in the IDA ICE models

The Excel files are internal working notes created during model setup and are included for transparency and reproducibility. They are not intended as polished documentation.
