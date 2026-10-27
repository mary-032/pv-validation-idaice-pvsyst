# Final shading analysis — independent consistency and provenance audit
Audit date: 27 October 2026. Subject: RISE Borås PV Systems A/3, B/8, C/9; 1 May–19 June 2023.

## Audit verdict
**PASS for internal numerical consistency and figure-to-data traceability.** Conditional scientific qualification: the System C measurement reindexing is supported by cross-system measurements but its physical/processing cause has not been independently authenticated. Hence the as-recorded/native-output sensitivity must remain available and be discussed alongside the working primary reindexed result. This audit does not cover the separate annual dataset.

## Verified structure and safeguards
- 3,600 rows = 1,200 hours × 3 systems; timestamp–system keys unique; 1,200 unique hour-ending timestamps 2023-05-01 01:00 through 2023-06-20 00:00.
- Exactly one primary-validation exclusion: System A at hour ending 2023-05-10 14:00, with 2,826 W measured power and deliberately blank model columns. The row is retained for provenance.
- System A IDA ICE historical power column exactly reproduces the recorded old middle/corner stitched `inverter_o` series (1,200 of 1,200 hours, maximum difference 0 W). The revised chronology uses middle through hour ending 13:00 on 10 May and corner from hour ending 15:00 onwards.
- System C unmodified native `inverter_o` export has shaded-period energy 901.411219 kWh; archived C IDA power disagrees at exactly 43 historical shifted hours. Original System C inverter source independently checked against the repository.
- C reference: 192 clock-status rows over eight days (2 h offset June 12–14, 1 h June 15–19), of which 123 numerical measured-power values change; archived and reindexed C measured total are both 867.190 kWh, and every operating-day energy total is unchanged. Both measured versions remain in the canonical CSV.
- Independent cross-system measured B/C lag test selected 0 h on June 10–11, 2 h on June 12–14, and 1 h on June 15–19. On shifted dates, scaled correlation at the selected lag was 0.9982–0.9995. This does not establish a logger cause.
- All 18 energy-summary records reproduce the canonical dataset; maximum numerical difference <1.2e-13 in reported energy/bias values.
- All 6 hourly-statistics records independently reproduce power RMSE, MAE, MBE, normalized bias and R²; differences <2.3e-13.
- All 144 plot-source records (24 × 2 days × 3 systems) agree exactly with canonical measured and model power columns, and the six daily-energy checks agree with the energy table to machine precision.
- Three 1-page vector PDF plots were rendered and visually inspected: complete axes, hour-ending convention, correct 2023 dates, legible legends, untruncated power profiles. Figure 6 uses days unaffected by the June 12–19 System C time shift; it is an illustrative-day plot rather than direct evidence of the timing correction.

## Revised full-period AC production
| System | Software | Hours | Measured (kWh) | Simulated (kWh) | Energy bias (%) |
|:--|:--|--:|--:|--:|--:|
| A | IDA ICE | 1199 | 1018.582 | 1013.885 | -0.461 |
| A | PVsyst | 1199 | 1018.582 | 1018.277 | -0.030 |
| B | IDA ICE | 1200 | 1319.352 | 1253.522 | -4.990 |
| B | PVsyst | 1200 | 1319.352 | 1294.120 | -1.912 |
| C | IDA ICE | 1200 | 867.190 | 901.411 | +3.946 |
| C | PVsyst | 1200 | 867.190 | 936.660 | +8.011 |

## Full-period hourly AC error (measured GTI > 0)
| System | Software | n | RMSE (W) | MAE (W) | nMBE (%) | R² |
|:--|:--|--:|--:|--:|--:|--:|
| A | IDA ICE | 931 | 275.873 | 178.010 | -0.457 | 0.93811 |
| A | PVsyst | 931 | 267.083 | 168.968 | -0.025 | 0.94199 |
| B | IDA ICE | 886 | 213.324 | 132.830 | -4.982 | 0.97787 |
| B | PVsyst | 886 | 198.833 | 114.595 | -1.905 | 0.98078 |
| C | IDA ICE | 886 | 158.286 | 95.778 | +3.946 | 0.97385 |
| C | PVsyst | 886 | 171.969 | 111.180 | +8.011 | 0.96913 |

## System C clock sensitivity: compare both sources with ORIGINAL model outputs
All use the same fixed 886-hour positive-measured-GTI mask. `native IDA` means the unmodified C `energy/electrical system.EL-STRING-POWERS.prn` inverter output, not the historically shifted IDA column.
| Measurement scenario | IDA ICE native RMSE (W) | PVsyst RMSE (W) |
|:--|--:|--:|
| As recorded | 244.245 | 253.695 |
| Reindexed (inferred) | 158.286 | 171.969 |

The C energy bias remains +3.946% (IDA ICE) and +8.011% (PVsyst) in both measurement scenarios because the reindex preserves energy, while the hourly RMSE changes considerably. Claims about improved alignment must be described as conditional on the inferred timestamps.

## Required manuscript and repository safeguards
1. Label the physical A/3 pole relocation as **10 May 2023 around 13:10**, not 11 May. Exclude only the ending-14:00 mixed hour from primary A validation. Mention the original historically stitched IDA switch (11 May) in the provenance explanation.
2. Present both **as-recorded native-output** and **measurement-reindexed native-output** C/9 scenarios. Do not label the latter a proven clock correction or use the historically shifted IDA column as the baseline.
3. Interpret full-period percentage biases alongside hourly RMSE and separate A pole configurations: large opposing deviations can cancel when energies are summed.
4. **Completed 27 October 2026:** Independently inspected the uploaded `scripts/17_integrate_C9_shading_clock.py` and all three C9 provenance CSVs. The script reproduces the reported lags and metrics; the hourly audit matches all 1,200 C records. Include those files in the versioned repository commit.
5. The existing `scripts/02_run_analysis.py` still runs annual code when invoked as a whole. Continue using the dedicated `run_shading_analysis()` entry point until the separately approved raw annual reference is integrated.
6. The June 5 and May 15 daily figures do not visualize the inferred June 12–19 C time-shift; consider a separate sensitivity comparison graphic/table in supplementary material if the revised manuscript discusses the timing issue in detail.

## Submitted file SHA-256 fingerprints
| Uploaded file | SHA-256 |
|:--|:--|
| `shading_analysis_final_A3_C9.csv` | `61f82f082714feffe615ba0b6dcf747c2509cfca0145f90c858fe436f62180fa` |
| `Shading_energy_recomputed.csv` | `8c805a0daffe6285dac8c8175d04a85d20f7d0088c60dd557da235822349a1ac` |
| `Shading_hourly_diagnostics_recomputed.csv` | `761d0753e80b25d5914698124bc466bb11161e7e6edd20ad4ece757447c6e102` |
| `Figures4_5_6_plotted_hourly_power.csv` | `5a5f42832d79652419ab30e280d6397f9ab430e5d5b5b02bb37a63a5ad42050c` |
| `Figures4_5_6_daily_energy_check.csv` | `04eab40c40a0becc03324053f94d69736b5c5f4dbb4412cdd343c32bd7fc83cb` |
| `Shading_A3_source_reconciliation.csv` | `43e194cc9b44ed117e17d1d0d75886e50e343c1e1249af7a804eb34668b31813` |
| `Figure4_SystemA_clear_and_partly_cloudy.pdf` | `a94eae05cf6c2c184fda70733b94f5fc4d560a181c53a1aad81e8091b5dbf397` |
| `Figure5_SystemB_clear_and_partly_cloudy.pdf` | `36592c84c90af9b4259b4741bcfc4e2f5d557d7d127a4ed4f072222146fc3e12` |
| `Figure6_SystemC_clear_and_partly_cloudy.pdf` | `5ded34fa8995fa9a90b42258f87ceefbd404baa03a4703687db900ff62a31e39` |
| `02_run_analysis(1).py` | `09b6a531d02d046ce1a2de0e4e772fd8261ec6a74a40df0d058fdd352fc44ed6` |
| `11_make_figures4_5_6_shading.py` | `4b7e7419dda3be74096db021e0d32b987228f30424cb063996fe5f9720ad3f02` |
| `16_rebuild_A3_shading.py` | `ae0cb72cc4853e359807b650a7674dbddf2ae9b5c92a186f8558c7c8c1cdb0b7` |

**Audit scope limitation (updated 27 October):** Output file consistency, the uploaded local script 17, three C9 traceability CSVs, and original System C GitHub `inverter_o` provenance have been independently inspected. This does not authenticate the original PVsyst System B/C project geometries, the cause of System C's apparent clock offset, or the separate annual PV validation. Full script 17 end-to-end execution was confirmed by the user's local run and checked against its produced files; the audit did not independently rerun the original native simulation exports.


## Addendum — System C final reproducibility audit (27 October 2026)

Following the original audit, the current local copy of `scripts/17_integrate_C9_shading_clock.py` and all three previously requested C9 results were uploaded and inspected. The data were also independently cross-checked against `derived_data/shading_analysis_final_A3_C9.csv` using the script's own `operating_day`, lag-selection, and statistics conventions.

**Verification results:**
- The 1,200-row C hourly audit maps one-to-one onto the final canonical C data; original and inferred-reindexed measurements, source timestamps, original native IDA inverter power, previously shifted IDA values, and unchanged PVsyst power all match.
- Exactly **123** C measured hourly power values change upon reference reindexing, and exactly **43** historic IDA power values differ from the original `inverter_o` export.
- Of the 1,200 C hours, **1,008** are designated 0-hour shift, **72** a 2-hour shift, and **120** a 1-hour shift; these are status hours, not counts of nonzero-power changes.
- All **40** candidate daily measured B/C profile-fit rows (10 operating days × four offsets) reproduce their numerical scales, RMSEs, Pearson correlations, and sample counts. The minimum-RMSE lag for June 10–11 is 0 hours; for June 12–14, 2 hours; and for June 15–19, 1 hour.
- All **six** reported C sensitivity scenarios recalculate exactly within numerical tolerance from the final canonical data. The fixed positive-measured-GTI daytime mask includes **886 hours**.
- The total measured C energy is conserved at **867.190 kWh**. Original IDA native `inverter_o` energy is **901.411219 kWh**, and unchanged PVsyst energy is **936.6602 kWh**.
- GTI was **not** reindexed by script 17; the inferred timing issue was applied to C measured AC power only, while the GTI-positive sample mask remained unchanged. The two models were not clock-shifted.

### Original-versus-reindexed sensitivity, native simulator outputs

| Scenario | IDA ICE RMSE (W) | PVsyst RMSE (W) |
|---|---:|---:|
| As recorded | 244.245 | 253.695 |
| Measured power reindexed (inferred) | 158.286 | 171.969 |

The historical shifted IDA series produces a different RMSE (182.659 W against as-recorded measured power); it must **not** be used as the original-simulator baseline. The reindexed clock is a supported, conditional analysis scenario, not an independently authenticated correction of logger timestamps.

### Additional provenance-file SHA-256 fingerprints

| File | SHA-256 |
|---|---|
| `17_integrate_C9_shading_clock.py` | `1b6109d8fb783f6b3431588f02af118f7eac371f5d92e2c8d0ac994d319271d9` |
| `Shading_C9_original_vs_reindexed_metrics.csv` | `7fa501d3c2941894dfcf298ad6aebe09a97f5d54a59c355889c7f0f968026bfb` |
| `Shading_C9_clock_daily_lag_evidence.csv` | `08e00059a44d3bf469b4c4e2f9026154d812855a29ac58fd1622d5025f01dbda` |
| `Shading_C9_clock_hourly_audit.csv` | `b68ff7367336c8e7078d7fdfd9128a3a701d557ffb37cd798f54a62029bf5624` |

**Revised disposition:** The shaded-period results and Figures 4–6 are numerically and procedurally auditable and ready for a Git commit/repository freeze, **subject to explicit manuscript disclosure** of the inferred C clock scenario, the original/native IDA baseline, and the physical A pole-movement transition. The annual analysis is outside this freeze.
