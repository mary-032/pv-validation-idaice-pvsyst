# pv-validation-idaice-pvsyst
Reproducible data-processing, validation, uncertainty, sensitivity, and figure-generation workflow for comparing PV simulations in IDA ICE and PVsyst against measured data.
# Known limitations

This document summarises limitations relevant to interpretation and reproduction of the PV-model validation study.

The purpose is not to list every possible uncertainty in PV simulation, but to identify limitations that materially affect this dataset, workflow, or comparison.

---

## 1. Single experimental site

The validation is based on three PV systems located at the same research site in Borås, Sweden.

The systems differ in technology and electrical configuration, but they experience broadly the same climatic environment.

The results therefore provide evidence for the evaluated configurations and climate but should not be interpreted as universal performance rankings of IDA ICE and PVsyst under all sites, climates, technologies, or system layouts.

---

## 2. Limited number of PV systems

Only three systems are included:

- one conventional monocrystalline BAPV system;
- one monocrystalline BAPV system with power optimisers;
- one CIGS BIPV system.

This provides useful technological variation but does not represent the complete range of PV module, inverter, optimiser, BIPV, or mounting configurations.

---

## 3. Auxiliary meteorological data from an off-site station

Some auxiliary meteorological variables used by IDA ICE originate from the Rångedala meteorological station, approximately 16 km from the PV measurement site.

The principal irradiance input and ambient-temperature data used in the validation are measured at the experimental site.

The off-site variables primarily contribute to environmental and thermal boundary conditions, particularly those influencing module temperature.

No independent, sufficiently complete local weather dataset was available for the same period.

The uncertainty associated with the spatial separation of the auxiliary weather source was therefore not quantified through an alternative-weather simulation.

Its influence is partly reflected in the panel-temperature validation and, through the thermal model, in the simulated power error.

This source of uncertainty should nevertheless be regarded as unquantified.

---

## 4. Reverse-transposition uncertainty

The measured solar input did not directly provide all irradiance components required by the simulation software.

Irradiance components were therefore reconstructed from measured plane-of-array irradiance.

Perez–Driesse is used for the primary analysis.

Engerer2 is evaluated as an alternative sensitivity scenario.

The sensitivity analysis demonstrates that the relative irradiance-performance comparison between IDA ICE and PVsyst can depend strongly on the selected reverse-transposition/separation method.

Consequently, claims concerning superiority of one tool for irradiance prediction should not be generalised beyond the evaluated input-processing method.

---

## 5. System A measured GTI alignment correction

Reconstruction of the historical annual workflow identified a one-hour displacement in the measured GTI series used for System A.

The final canonical-data workflow applies a documented one-hour alignment correction.

The correction is supported by comparison with the historical processing layer and both simulation outputs.

However, the original historical processing step responsible for the displacement could not be reconstructed with complete certainty from the original 10-minute measurement file alone.

The correction is therefore retained as a documented provenance-based alignment step.

---

## 6. System A Engerer2 PVsyst timing correction

The System A Engerer2 PVsyst export showed a consistent one-hour temporal displacement across:

- effective irradiance;
- panel temperature;
- AC power.

The entire record is shifted uniformly by +1 h before comparison.

The same displacement was not observed in:

- System A Perez–Driesse;
- System B;
- System C.

Workbook metadata identify a unique meteorological file for the affected simulation:

```text
Ekås_Custom_E2.MET
```

The original `.MET` file is no longer available.

The timing anomaly can therefore be diagnosed from the exported data and metadata but cannot be traced fully to its original meteorological-file construction.

---

## 7. Historical preprocessing cannot be reconstructed exactly for every variable

The historical processed annual workbook reproduces the measured panel-temperature series exactly and the measured irradiance series to a high degree.

The historical measured power series could not be reconstructed exactly from the available raw 10-minute data using simple aggregation and plausible timestamp shifts.

The final workflow therefore retains the historically processed measured-power layer where required.

This choice is documented to avoid presenting a partially reconstructed series as though it were identical to the original analysis input.

---

## 8. Hourly simulation resolution

The annual comparison is performed at hourly resolution.

The original measurements were available at finer resolution, but the simulation comparison uses a common temporal resolution between IDA ICE and PVsyst.

This limits the ability of the validation to evaluate rapid sub-hourly fluctuations in irradiance and power.

---

## 9. Sub-hourly shading analysis was not possible for both tools

Shorter simulation intervals would be particularly useful for analysing near-field shading because shadow movement can produce rapid changes in PV output.

However, the PVsyst version available for this study was:

```text
PVsyst 8.0.2
```

and the workflow used in this version provides hourly simulation results.

Sub-hourly simulation capability is available in a newer PVsyst version that was not available to the authors during the study.

Running IDA ICE at sub-hourly resolution while retaining hourly PVsyst results would have produced an asymmetric comparison.

The shading validation is therefore performed using a common hourly resolution.

This limitation means that the study does not evaluate the ability of the two tools to reproduce sub-hourly shading dynamics.

---

## 10. Selected shading case-study days are illustrative

Two individual days are shown in detail:

```text
5 June 2023  → clear
15 May 2023  → partly cloudy
```

They were selected because the contrasting irradiance conditions occurred during periods when the physical shading objects affected the arrays.

The days are intended as illustrative case studies rather than as statistically representative samples of all clear or cloudy days.

To reduce dependence on the selected examples, the analysis also evaluates the complete shading period from 1 May to 19 June 2023.

---

## 11. Shading-object configuration changed during the experiment

The position of the System A physical shading object changed during the experimental period.

The reconstructed analysis accounts for the transition.

Both selected case-study days occur after the change and therefore use the same later shading configuration.

Results from the full-period shading analysis span both configurations and should be interpreted accordingly.

---

## 12. Gross-error screening is residual-based

Four annual AC-power timestamps are excluded using a conservative robust-residual screening procedure.

The criterion requires extremely large, same-direction residuals for both IDA ICE and PVsyst simultaneously across all three systems.

This greatly reduces the likelihood that observations are removed merely because one model performs poorly.

However, the screening is still based on model-measurement residuals rather than on an independently documented sensor-failure flag.

The physical cause of the four anomalies is therefore not established.

A separate sensitivity analysis evaluates whether the main conclusions depend on their exclusion.

---

## 13. Sparse observations in some weather-condition bins

The annual data are unevenly distributed across tilted-clearness-index categories.

Most observations occur under overcast to mixed conditions, while comparatively few observations meet the clear-sky criterion.

For example, the finalized System A weather-bin analysis contains substantially fewer clear observations than overcast observations.

Metrics for sparsely populated bins should therefore be interpreted with more caution than metrics for the dominant weather categories.

This is particularly relevant for normalized bias metrics, which can become sensitive when the denominator is small.

---

## 14. Weather-bin thresholds are conventional rather than unique physical boundaries

The weather-condition analysis uses nominal tilted-clearness-index thresholds of:

```text
0.20
0.40
0.60
0.75
```

These categories provide a useful descriptive classification but are not unique physical boundaries between sky states.

A dedicated sensitivity analysis shifts the internal thresholds by ±0.05.

The overall cloudiest-to-clearest error pattern is robust to these perturbations, although individual bin metrics can change when observations move between categories.

---

## 15. Simplified interpretation of weather-bin labels

Terms such as:

```text
Overcast
Cloudy
Mixed
Mostly clear
Clear
```

are descriptive labels assigned according to `kt_tilt`.

They should not be interpreted as direct cloud-observation measurements or formal meteorological cloud classifications.

---

## 16. Measurement uncertainty is represented as bounded scenarios

Measurement uncertainty is assessed using the stated sensor bounds:

```text
GTI                ±2%
AC power           ±1%
Panel temperature  ±0.5 °C
```

These bounds are applied as systematic low/nominal/high perturbations.

No probability distribution is assumed for the sensor uncertainty.

Consequently, the combined measurement-and-temporal uncertainty envelope is not a fully probabilistic joint 95% confidence interval.

It should be interpreted as a moving-block-bootstrap interval enveloped over the stated measurement-uncertainty bounds.

---

## 17. Temporal autocorrelation

Hourly PV observations are strongly temporally dependent.

Standard statistical methods assuming independent observations would therefore overstate the effective sample size.

The study addresses this using moving-block bootstrap inference.

A 30-day block length is used for the primary annual inference, supported by autocorrelation diagnostics and block-length sensitivity analysis.

The exact dependence scale is nevertheless not known with certainty.

---

## 18. Statistical significance depends on methodological choices

Some IDA ICE versus PVsyst differences are small relative to uncertainty.

The significance of some comparisons changes depending on:

- reverse-transposition method;
- bootstrap block length;
- measurement uncertainty scenario;
- temporal aggregation.

The article therefore distinguishes between:

- numerical differences;
- statistically supported differences;
- conclusions robust across sensitivity scenarios.

Small differences should not be interpreted as universal evidence that one software is intrinsically more accurate.

---

## 19. Temporal aggregation affects relative performance

The relative RMSE ranking of IDA ICE and PVsyst is not generally preserved when moving from:

```text
hourly power
```

to:

```text
daily energy
```

and:

```text
monthly energy
```

This demonstrates that model performance depends partly on the temporal scale and intended application.

Hourly RMSE emphasises short-term agreement, whereas aggregated energy metrics increasingly emphasise cumulative energy prediction.

A single overall statement that one tool is "more accurate" would therefore be inappropriate.

---

## 20. Irradiance outputs are not perfectly identical physical quantities

The closest available irradiance outputs are compared between the two simulation environments.

For IDA ICE, the relevant output is panel effective irradiance.

For PVsyst, the corresponding output is `GlobEff`.

These variables provide useful comparable model outputs but should not be assumed to be physically identical to each other or to an unmodified measured plane-of-array irradiance quantity in every detail.

The irradiance comparison is therefore interpreted as a validation of the closest available effective plane-of-array irradiance outputs.

---

## 21. Model parameter uncertainty was not exhaustively propagated

Not every PV-model parameter was varied systematically.

Module, inverter, optimiser, thermal, and system parameters were selected from the available system specifications and implemented consistently within the respective simulation environments.

A full factorial or probabilistic propagation of parameter uncertainty would require a substantially larger simulation campaign and is outside the scope of the present study.

The sensitivity analysis instead concentrates on uncertainty sources that could be evaluated reproducibly using the available data and completed simulations:

- measurement uncertainty;
- temporal dependence;
- reverse transposition;
- temporal aggregation;
- weather-bin classification.

---

## 22. Software versions

The study evaluates specific software versions:

```text
IDA ICE 5.1.1.1
PVsyst 8.0.2
```

Software behaviour may change in later releases.

The conclusions should therefore be associated with the documented software versions rather than assumed to describe all future versions.

---

## 23. Proprietary software affects complete reproducibility

IDA ICE and PVsyst are proprietary applications.

The repository can reproduce the data processing, statistical analysis, uncertainty analysis, and figures from the exported simulation results.

Complete reproduction from the original simulation models requires access to compatible versions of the proprietary software and, where applicable, redistributable project/model files.

The canonical datasets are therefore provided as an important reproducibility layer independent of access to the proprietary simulation environments.

---

## 24. Redistribution restrictions may limit source-data availability

Some source files originate from:

- RISE;
- IDA ICE;
- PVsyst;
- external meteorological sources.

Possession of these files for research does not necessarily imply permission for unrestricted public redistribution.

Where redistribution rights are unclear, the public repository may provide:

- file names;
- provenance;
- expected variables;
- processing code;
- derived/canonical datasets where permitted

without distributing the original proprietary or third-party source file itself.

---

## 25. Scope of the study

The study is designed as a validation and comparative evaluation of PV modelling in an integrated building-energy simulation environment.

It does not attempt to establish an absolute ranking of IDA ICE and PVsyst for all PV applications.

The most defensible conclusions are those that remain stable across:

- systems;
- uncertainty analyses;
- alternative irradiance processing;
- temporal scales.

Where the sensitivity analyses show that the relative performance changes, this methodological dependence is treated as part of the result rather than as an error to be removed.
