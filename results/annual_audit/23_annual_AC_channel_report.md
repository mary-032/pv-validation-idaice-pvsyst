# Step 23 — Annual AC channel sensitivity

**Diagnostic only.** Not a finalized or approved annual AC comparison.

Measured input: original RISE ten-minute Power_* readings; six samples per hour.
The Step20/21 source cohort is retained: start-labeled samples, a -1 h
reference-label transformation, and solar elevation >0 **at the interval start**.
The prior diagnostics referred to this as hour-ending daylight; after the -1 h
transformation it is in fact the interval START. No sample is discarded
or relabeled during this sensitivity test.

Model clock cases: unshifted civil lookup and fixed-CET hypothesis
(model time t in CET, t-1 h in CEST). Neither is chosen by RMSE.

|System|Clock scenario|Channel|RMSE W|Bias %|
|---|---|---|---:|---:|
|A|civil_unshifted|IDA ICE produced_p|292.35|-1.38|
|A|civil_unshifted|IDA ICE inverter_o|313.07|-2.02|
|A|civil_unshifted|PVsyst E_Grid|288.02|-6.37|
|A|fixed_CET_hypothesis|IDA ICE produced_p|249.50|-1.33|
|A|fixed_CET_hypothesis|IDA ICE inverter_o|220.49|-1.96|
|A|fixed_CET_hypothesis|PVsyst E_Grid|252.46|-6.26|
|B|civil_unshifted|IDA ICE produced_p|400.83|+3.63|
|B|civil_unshifted|IDA ICE inverter_o|425.80|+2.88|
|B|civil_unshifted|PVsyst E_Grid|398.41|-0.45|
|B|fixed_CET_hypothesis|IDA ICE produced_p|335.11|+3.67|
|B|fixed_CET_hypothesis|IDA ICE inverter_o|306.12|+2.94|
|B|fixed_CET_hypothesis|PVsyst E_Grid|311.47|-0.30|
|C|civil_unshifted|IDA ICE produced_p|299.00|+6.84|
|C|civil_unshifted|IDA ICE inverter_o|314.90|+5.93|
|C|civil_unshifted|PVsyst E_Grid|294.87|+10.36|
|C|fixed_CET_hypothesis|IDA ICE produced_p|263.39|+6.86|
|C|fixed_CET_hypothesis|IDA ICE inverter_o|238.93|+5.95|
|C|fixed_CET_hypothesis|PVsyst E_Grid|245.00|+10.44|

## Daylight-selection boundary diagnostic

|System|Solar elevation evaluated at|Daylight h|Measured kWh|Hours entering relative to start|Hours excluded relative to start|
|---|---|---:|---:|---:|---:|
|A|start|4478|3648.541|0|0|
|A|midpoint|4461|3650.069|178|195|
|A|end|4478|3645.862|364|364|
|B|start|4478|4230.835|0|0|
|B|midpoint|4461|4232.569|178|195|
|B|end|4478|4229.346|364|364|
|C|start|4478|2809.808|0|0|
|C|midpoint|4461|2810.348|178|195|
|C|end|4478|2808.152|364|364|

## Conditional paired-model uncertainty (30-day circular moving blocks)

|System|Clock|IDA channel|IDA minus PVsyst RMSE W|95% CI W|
|---|---|---|---:|---|
|A|civil_unshifted|IDA_produced_p_W|+4.33|[-1.00, +13.43]|
|A|civil_unshifted|IDA_inverter_o_W|+25.06|[+12.10, +33.11]|
|A|fixed_CET_hypothesis|IDA_produced_p_W|-2.96|[-11.52, +9.39]|
|A|fixed_CET_hypothesis|IDA_inverter_o_W|-31.97|[-43.33, -15.29]|
|B|civil_unshifted|IDA_produced_p_W|+2.42|[-4.07, +9.70]|
|B|civil_unshifted|IDA_inverter_o_W|+27.39|[+14.80, +36.24]|
|B|fixed_CET_hypothesis|IDA_produced_p_W|+23.65|[+15.76, +32.42]|
|B|fixed_CET_hypothesis|IDA_inverter_o_W|-5.34|[-16.38, +6.32]|
|C|civil_unshifted|IDA_produced_p_W|+4.13|[-0.59, +9.48]|
|C|civil_unshifted|IDA_inverter_o_W|+20.03|[+11.12, +27.67]|
|C|fixed_CET_hypothesis|IDA_produced_p_W|+18.39|[+12.63, +23.73]|
|C|fixed_CET_hypothesis|IDA_inverter_o_W|-6.07|[-11.33, -0.41]|

## Release gate

- Determine from IDA ICE model documentation whether `produced_p` (equal to
  minus `grid_power`, with `used_power=0`) is the correct AC exported grid
  quantity, or whether `inverter_o` represents the comparison boundary.
- Verify input meteo fixed-CET clock semantics independently before
  choosing any CEST model lookup.
- Report the interval-start solar selection accurately; revise the
  daylight mask if the intended scientific definition differs.
- This file does not change historical annual results or the shading freeze.
