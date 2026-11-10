# Table S1a. Seasonal hourly AC-power validation

Working fixed-CET model-clock interpretation

Each cell: **CV(RMSE) / nMBE (%)**.

| System | Software | Winter (DJF) | Spring (MAM) | Summer (JJA) | Autumn (SON) |
|:--|:--|--:|--:|--:|--:|
| A | IDA ICE | 58.8 / +17.3 | 13.8 / -2.3 | 13.6 / -4.3 | 18.9 / -1.4 |
| A | PVsyst | 64.0 / +11.0 | 27.0 / -7.2 | 26.2 / -8.4 | 35.9 / -6.8 |
| B | IDA ICE | 53.4 / +3.8 | 24.4 / +4.7 | 18.1 / +2.4 | 34.0 / +3.7 |
| B | PVsyst | 72.1 / +5.0 | 30.3 / +1.0 | 25.7 / -1.9 | 39.4 / -1.4 |
| C | IDA ICE | 56.4 / -0.1 | 30.5 / +12.0 | 21.5 / +5.5 | 36.9 / +1.4 |
| C | PVsyst | 75.0 / +6.5 | 37.5 / +14.6 | 30.7 / +9.1 | 45.0 / +6.2 |

**Table note.** Positive nMBE indicates simulated power exceeding measured power. Sample sizes per system and model: winter (DJF) 703 hours; spring (MAM) 1,310; summer (JJA) 1,537; autumn (SON) 928. The selected cohort does not contain 31 December 2020. Both software tools use the same 4,478 physical selected hours per system. These are descriptive point estimates without season-specific confidence intervals.

**Source:** `results/revision2/29_seasonal_AC.csv`, derived from the corrected Step 28 paired hourly series.
