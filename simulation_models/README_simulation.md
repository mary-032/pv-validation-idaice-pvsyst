# Simulation Models

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
