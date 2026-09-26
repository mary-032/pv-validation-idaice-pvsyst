from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
needed=[
"01_source_inputs/annual/measured/Results_PVsyst_E2_hour.xlsx",
"01_source_inputs/annual/IDA_ICE/Syst3_PD.xlsx",
"01_source_inputs/annual/IDA_ICE/Syst8_PD.xlsx",
"01_source_inputs/annual/IDA_ICE/Syst9_PD.xlsx",
"01_source_inputs/annual/PVsyst/PVsyst_3_PD_h.xlsx",
"01_source_inputs/annual/PVsyst/PVsyst_8_PD_h.xlsx",
"01_source_inputs/annual/PVsyst/PVsyst_9_PD_h.xlsx",
"01_source_inputs/shading/audited_reconstruction/Shading_results_definitive_audit.xlsx",
"04_reference_frozen/PV_MASTER_RESULTS_FULLY_FROZEN_20260908.xlsx",
]
print("\nSOURCE INPUT CHECK")
print("="*36)
missing=[]
for rel in needed:
    ok=(ROOT/rel).exists()
    print(("OK   " if ok else "MISS "),rel)
    if not ok: missing.append(rel)
print("\nAll required workbooks present." if not missing else f"\n{len(missing)} required file(s) missing.")
