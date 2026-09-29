from pathlib import Path

# =============================================================================
# 00 - CHECK REQUIRED SOURCE INPUTS
# =============================================================================
#
# This checker matches the public GitHub repository layout used by
# 01_build_canonical_data.py.
#
# Required files are those needed to rebuild the Perez–Driesse canonical
# annual and shading datasets.
#
# Optional/provenance files are reported separately and do not cause failure.
# =============================================================================

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

REQUIRED = [
    DATA / "historical" / "Results_PVsyst_E2_hour.xlsx",

    DATA / "ida_ice" / "annual" / "Perez_Driesse" / "Syst3_PD.xlsx",
    DATA / "ida_ice" / "annual" / "Perez_Driesse" / "Syst8_PD.xlsx",
    DATA / "ida_ice" / "annual" / "Perez_Driesse" / "Syst9_PD.xlsx",

    DATA / "pvsyst" / "annual" / "Perez_Driesse" / "PVsyst_3_PD_h.xlsx",
    DATA / "pvsyst" / "annual" / "Perez_Driesse" / "PVsyst_8_PD_h.xlsx",
    DATA / "pvsyst" / "annual" / "Perez_Driesse" / "PVsyst_9_PD_h.xlsx",

    DATA
    / "shading"
    / "audited_reconstruction"
    / "Shading_results_definitive_audit.xlsx",
]

OPTIONAL = [
    DATA / "measured" / "annual" / "RISE_raw10min_389.xlsx",

    DATA / "ida_ice" / "annual" / "Engerer2" / "Syst3_E2.xlsx",
    DATA / "ida_ice" / "annual" / "Engerer2" / "Syst8_E2.xlsx",
    DATA / "ida_ice" / "annual" / "Engerer2" / "Syst9_E2.xlsx",

    DATA / "pvsyst" / "annual" / "Engerer2" / "PVsyst_3_E2_h.xlsx",
    DATA / "pvsyst" / "annual" / "Engerer2" / "PVsyst_8_E2_h.xlsx",
    DATA / "pvsyst" / "annual" / "Engerer2" / "PVsyst_9_E2_h.xlsx",
]


def rel(path):
    return path.relative_to(ROOT)


def main():
    print("\nSOURCE INPUT CHECK")
    print("=" * 72)

    missing = []

    print("\nREQUIRED FOR SCRIPT 01")
    print("-" * 72)

    for path in REQUIRED:
        if path.exists():
            print(f"OK    {rel(path)}")
        else:
            print(f"MISS  {rel(path)}")
            missing.append(path)

    print("\nOPTIONAL / PROVENANCE / LATER SENSITIVITY INPUTS")
    print("-" * 72)

    for path in OPTIONAL:
        status = "OK  " if path.exists() else "----"
        print(f"{status}  {rel(path)}")

    print("\n" + "=" * 72)

    if missing:
        print(f"{len(missing)} required file(s) missing.")
        print(
            "\nCopy the required source files into the paths shown above, "
            "then rerun this checker."
        )
        raise SystemExit(1)

    print("All files required by 01_build_canonical_data.py are present.")
    print(
        "The historical frozen master-results workbook is intentionally NOT "
        "required: it is a validation/archive artifact, not a source input."
    )


if __name__ == "__main__":
    main()
