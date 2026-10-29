# Step 28 — annual AC release candidate (not final)

The selected working primary comparison is fixed-CET model lookup relative to
a CET/CEST RISE measurement clock. **It is not independently verified from original logger records.**

## Numerically reproduced release-candidate results

|System|IDA hourly Table RMSE W|PVsyst RMSE W|IDA−PVsyst W|95% bootstrap CI W|
|---|---:|---:|---:|---|
|A|149.98|252.46|-102.48|[-124.95, -73.58]|
|B|242.51|311.47|-68.96|[-96.18, -41.01]|
|C|190.03|245.00|-54.97|[-72.68, -36.00]|

## Quality gates passed

- 4,478 shared and fully observed measured hourly records per system; measured energy unchanged.
- Two clock scenarios operate on exactly the same physical reference rows.
- IDA Table values use interval-end indices; power metrics reproduce Step 26.
- Step 26 30-day paired uncertainty reproduces the reported RMSE differences.
- No shading or historical annual datasets were modified.

## Scientific qualifications

- Fixed CET is the supported **working** interpretation only. The ranking reverses under the civil-unshifted sensitivity; present both.
- The raw RISE 10-minute workbook contains regular records across DST with no duplicates, which prevents identifying the original logger behavior directly.
- Step 27 GTI solar centroid has CET residual +3.6 min and CEST residual −0.9 min relative to expected civil solar noon, but depends on weather and reconstructed timestamps.
- PVsyst MET has a recorded one-hour import shift which is already applied to the meteorological labels; the missing original CSV and MEF prevent a full import audit.
- IDA hourly Table `produced_p` is retained as the provisional electrical-system meter comparison boundary; document the `inverter_o` sensitivity.
- Solar elevation evaluated at the START of each selected measured interval; a midpoint convention changes the cohort.

## Before calling results final

- Verify source fingerprints and inspect the generated primary/sensitivity tables.
- Keep Step 26 and 27 source outputs; stage only 28_* files in version control.
- Document the remaining clock and AC metering uncertainties in Methods/Limitations.
- Do not replace or rerun the frozen shading analysis.
