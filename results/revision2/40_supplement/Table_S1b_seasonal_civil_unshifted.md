# Table S1b. Seasonal hourly AC-power validation

Alternative unshifted civil-clock interpretation

Each cell: **CV(RMSE) / nMBE (%)**.

| System | Software | Winter (DJF) | Spring (MAM) | Summer (JJA) | Autumn (SON) |
|:--|:--|--:|--:|--:|--:|
| A | IDA ICE | 58.8 / +17.3 | 41.5 / -2.6 | 44.9 / -4.4 | 60.4 / -3.1 |
| A | PVsyst | 64.0 / +11.0 | 30.8 / -7.2 | 30.8 / -8.5 | 42.9 / -7.2 |
| B | IDA ICE | 53.4 / +3.8 | 49.5 / +4.4 | 49.5 / +2.3 | 73.3 / +2.0 |
| B | PVsyst | 72.1 / +5.0 | 38.6 / +0.9 | 35.9 / -2.1 | 51.2 / -1.7 |
| C | IDA ICE | 56.4 / -0.1 | 56.7 / +11.8 | 53.8 / +5.5 | 75.8 / +0.0 |
| C | PVsyst | 75.0 / +6.5 | 45.5 / +14.6 | 39.3 / +9.1 | 53.4 / +6.0 |

**Table note.** Positive nMBE indicates simulated power exceeding measured power. Sample sizes per system and model: winter (DJF) 703 hours; spring (MAM) 1,310; summer (JJA) 1,537; autumn (SON) 928. The selected cohort does not contain 31 December 2020. Both software tools use the same 4,478 physical selected hours per system. These are descriptive point estimates without season-specific confidence intervals.

**Source:** `results/revision2/29_seasonal_AC.csv`, derived from the corrected Step 28 paired hourly series.
