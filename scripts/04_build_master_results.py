from pathlib import Path
from datetime import datetime

import pandas as pd


# ============================================================
# MASTER RESULTS ASSEMBLER
# ============================================================
#
# PURPOSE
# -------
# Collect the already-computed CURRENT Perez-Driesse results into one
# authoritative results package.
#
# IMPORTANT:
#   This script does NOT recompute any scientific result.
#   It only reads the outputs from 02_run_analysis.py and assembles them.
#
# Outputs:
#   results/PV_MASTER_RESULTS_CURRENT_PD.xlsx
#   results/PV_MASTER_RESULTS_CURRENT_PD_LONG.csv
#
# The Excel workbook is for human review/article work.
# The long CSV is the machine-readable master table.
# ============================================================


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DIR = ROOT / "derived_data"
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)

MASTER_XLSX = OUT / "PV_MASTER_RESULTS_CURRENT_PD.xlsx"
MASTER_LONG = OUT / "PV_MASTER_RESULTS_CURRENT_PD_LONG.csv"


FILES = {
    "Annual_GTI": OUT / "Table4_GTI_recomputed.csv",
    "Annual_Temperature": OUT / "Table5_Temperature_recomputed.csv",
    "Annual_Power": OUT / "Table6_Power_recomputed.csv",
    "Monthly_RMSE": OUT / "Monthly_RMSE_recomputed.csv",
    "Weather_Bins": OUT / "Figure3_weather_bins_recomputed.csv",
    "Shading_Energy": OUT / "Shading_energy_recomputed.csv",
    "Shading_Hourly": OUT / "Shading_hourly_diagnostics_recomputed.csv",
    "Power_Exclusions": OUT / "Power_exclusion_audit.csv",
}

OPTIONAL_FILES = {
    "Provenance": CANONICAL_DIR / "ANNUAL_PROVENANCE_AUDIT.csv",
    "Logger_Clock": CANONICAL_DIR / "RISE_logger_clock_summary.csv",
}


# Result sheets included in the machine-readable long master.
# Audit/provenance sheets are kept in the workbook but not melted into results.
RESULT_SHEETS = [
    "Annual_GTI",
    "Annual_Temperature",
    "Annual_Power",
    "Monthly_RMSE",
    "Weather_Bins",
    "Shading_Energy",
    "Shading_Hourly",
]


def require_files():
    missing = [str(p.relative_to(ROOT)) for p in FILES.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required analysis outputs:\n"
            + "\n".join(f"  - {x}" for x in missing)
            + "\n\nRun scripts/02_run_analysis.py first."
        )


def load_tables():
    tables = {}

    for name, path in FILES.items():
        tables[name] = pd.read_csv(path)

    for name, path in OPTIONAL_FILES.items():
        if path.exists():
            tables[name] = pd.read_csv(path)

    return tables


def canonical_qa():
    """
    Verify the current canonical annual dataset before assembling the master.
    """
    path = CANONICAL_DIR / "annual_unshaded_analysis.csv"

    if not path.exists():
        return {
            "Canonical annual dataset": "MISSING",
            "Annual rows": None,
            "Unique timestamps": None,
            "Systems": None,
        }

    d = pd.read_csv(path, usecols=["timestamp", "system"])

    return {
        "Canonical annual dataset": "PASS",
        "Annual rows": len(d),
        "Unique timestamps": d["timestamp"].nunique(),
        "Systems": ", ".join(sorted(d["system"].dropna().astype(str).unique())),
    }


def result_qa(tables):
    """
    Structural checks only. These do not judge whether results are 'good';
    they make sure the expected tables are complete.
    """
    rows = []

    def add(check, expected, actual):
        rows.append({
            "check": check,
            "expected": expected,
            "actual": actual,
            "status": "PASS" if str(expected) == str(actual) else "CHECK",
        })

    add("Annual GTI rows", 6, len(tables["Annual_GTI"]))
    add("Annual temperature rows", 6, len(tables["Annual_Temperature"]))
    add("Annual power rows", 6, len(tables["Annual_Power"]))
    add("Monthly RMSE rows", 6, len(tables["Monthly_RMSE"]))
    add("Weather-bin rows", 30, len(tables["Weather_Bins"]))

    # Expected shading sizes based on current analysis design.
    add("Shading energy rows", 18, len(tables["Shading_Energy"]))
    add("Shading hourly diagnostic rows", 6, len(tables["Shading_Hourly"]))

    return pd.DataFrame(rows)


def make_long_master(tables):
    """
    Convert result-level tables to one generic long-format master.

    Identifier/text columns are retained as context.
    Every remaining numeric result column becomes:
        metric, value

    This avoids recomputing anything and preserves the exact values written
    by 02_run_analysis.py.
    """
    parts = []

    preferred_id_columns = [
        "System",
        "system",
        "Software",
        "software",
        "Sky_condition",
        "sky_condition",
        "Period",
        "period",
        "Metric",
        "metric",
        "Variable",
        "variable",
    ]

    for sheet_name in RESULT_SHEETS:
        df = tables[sheet_name].copy()

        # Keep text columns + known identifier columns as context.
        id_cols = []
        for c in df.columns:
            if c in preferred_id_columns or not pd.api.types.is_numeric_dtype(df[c]):
                id_cols.append(c)

        # n is an important count/context variable, not normally a metric value.
        for n_col in ("n", "N"):
            if n_col in df.columns and n_col not in id_cols:
                id_cols.append(n_col)

        value_cols = [c for c in df.columns if c not in id_cols]

        if not value_cols:
            # Preserve table even if it has no numeric metric column.
            tmp = df.copy()
            tmp.insert(0, "source_table", sheet_name)
            tmp["metric_name"] = None
            tmp["metric_value"] = None
            parts.append(tmp)
            continue

        melted = df.melt(
            id_vars=id_cols,
            value_vars=value_cols,
            var_name="metric_name",
            value_name="metric_value",
        )

        melted.insert(0, "source_table", sheet_name)
        parts.append(melted)

    long_df = pd.concat(parts, ignore_index=True, sort=False)

    # Put common context columns first.
    front = [
        "source_table",
        "System",
        "system",
        "Software",
        "software",
        "Sky_condition",
        "sky_condition",
        "Period",
        "period",
        "n",
        "metric_name",
        "metric_value",
    ]
    front = [c for c in front if c in long_df.columns]
    rest = [c for c in long_df.columns if c not in front]

    return long_df[front + rest]


def format_excel(writer, tables):
    """
    Apply basic readable formatting with XlsxWriter.
    """
    workbook = writer.book

    title_fmt = workbook.add_format({
        "bold": True,
        "font_size": 14,
        "bg_color": "#D9EAF7",
        "border": 1,
    })

    header_fmt = workbook.add_format({
        "bold": True,
        "bg_color": "#D9EAF7",
        "border": 1,
        "text_wrap": True,
        "valign": "top",
    })

    note_fmt = workbook.add_format({
        "text_wrap": True,
        "valign": "top",
    })

    num_fmt = workbook.add_format({
        "num_format": "0.0000",
    })

    int_fmt = workbook.add_format({
        "num_format": "0",
    })

    for sheet_name, df in tables.items():
        if sheet_name not in writer.sheets:
            continue

        ws = writer.sheets[sheet_name]
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, max(len(df), 1), max(len(df.columns) - 1, 0))

        # Headers
        for col_idx, col_name in enumerate(df.columns):
            ws.write(0, col_idx, col_name, header_fmt)

            # Sensible width based on header + a sample of contents.
            # Convert each sampled value explicitly to string. This is robust
            # to pandas extension/nullable dtypes that may still yield numeric
            # scalars during iteration after astype(str).
            sample = df[col_name].head(200)
            sample_lengths = [
                len(str(x))
                for x in sample
                if pd.notna(x)
            ]
            width = max(
                [len(str(col_name)), *sample_lengths]
            )

            width = min(max(width + 2, 10), 32)
            ws.set_column(col_idx, col_idx, width)

            if pd.api.types.is_integer_dtype(df[col_name]):
                ws.set_column(col_idx, col_idx, width, int_fmt)
            elif pd.api.types.is_float_dtype(df[col_name]):
                ws.set_column(col_idx, col_idx, width, num_fmt)

    # README uses custom formatting.
    if "README" in writer.sheets:
        ws = writer.sheets["README"]
        ws.set_column("A:A", 28)
        ws.set_column("B:B", 95)
        ws.freeze_panes(1, 0)
        ws.write("A1", "PV MASTER RESULTS — CURRENT PEREZ–DRIESSE ANALYSIS", title_fmt)
        ws.write("B1", "Value / description", title_fmt)
        ws.set_column("B:B", 95, note_fmt)


def make_readme(qa, structural_qa):
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = [
        ["Generated", generated],
        ["Status", "CURRENT Perez–Driesse master results candidate"],
        [
            "Purpose",
            "Single source of article result values assembled from "
            "02_run_analysis.py outputs. This workbook does NOT recompute metrics.",
        ],
        [
            "Annual canonical dataset",
            f"{qa.get('Annual rows')} rows; "
            f"{qa.get('Unique timestamps')} unique timestamps; "
            f"systems {qa.get('Systems')}",
        ],
        [
            "Measured GTI",
            "A = GTI3M with verified +1 h correction; B/C = GTI9M.",
        ],
        [
            "Annual record rules",
            "GTI/Tp: measured GTI > 0 and paired non-missing values; "
            "Power: same daytime rule plus exactly four agreed gross-error timestamps; "
            "no additional outlier removal.",
        ],
        [
            "Monthly RMSE/kWp",
            "Uses the same daytime-cleaned power records; nighttime PVsyst inverter "
            "consumption is intentionally excluded.",
        ],
        [
            "Weather bins",
            "kt_tilt = measured GTI / Eext_tilt; full azimuth-aware AOI; "
            "AOI < 80°; bins <0.2, 0.2–0.4, 0.4–0.6, 0.6–0.75, >=0.75; "
            "no upper kt_tilt cap.",
        ],
        [
            "Geometry",
            "57.719231 N, 12.884806 E, 170 m; tilt 45°; pvlib azimuth 180°; "
            "Eext_normal uses documented Esc=1361.1 W/m² formulation.",
        ],
        [
            "Logger clock",
            "Raw RISE timestamps empirically identified as Europe/Stockholm civil time "
            "(CET/CEST).",
        ],
        [
            "Shading",
            "Definitive audited reconstruction; no additional outlier removal.",
        ],
        [
            "Old frozen workbook",
            "Superseded as authority because it may contain mixed Engerer2 / "
            "Perez–Driesse generations. Retain only as historical audit material.",
        ],
    ]

    readme = pd.DataFrame(rows, columns=["Item", "Value / description"])

    # Append QA checks after a spacer-like row.
    qa_rows = structural_qa.copy()
    qa_rows.insert(0, "Item", "QA: " + qa_rows["check"])
    qa_rows["Value / description"] = (
        qa_rows["status"]
        + " — expected "
        + qa_rows["expected"].astype(str)
        + ", actual "
        + qa_rows["actual"].astype(str)
    )

    readme = pd.concat(
        [
            readme,
            pd.DataFrame([["", ""]], columns=readme.columns),
            qa_rows[["Item", "Value / description"]],
        ],
        ignore_index=True,
    )

    return readme


def main():
    require_files()
    tables = load_tables()

    qa = canonical_qa()
    structural_qa = result_qa(tables)

    print("\nMASTER RESULTS ASSEMBLY")
    print("=" * 60)
    print(
        f"Canonical annual rows: {qa.get('Annual rows'):,}"
        if isinstance(qa.get("Annual rows"), int)
        else "Canonical annual rows: unavailable"
    )
    print(f"Unique timestamps: {qa.get('Unique timestamps')}")
    print(f"Systems: {qa.get('Systems')}")
    print("\nStructural QA:")
    print(structural_qa.to_string(index=False))

    # Machine-readable long master.
    long_df = make_long_master(tables)
    long_df.to_csv(MASTER_LONG, index=False)

    # Human-readable workbook.
    workbook_tables = {
        "README": make_readme(qa, structural_qa),
        "Annual_GTI": tables["Annual_GTI"],
        "Annual_Temperature": tables["Annual_Temperature"],
        "Annual_Power": tables["Annual_Power"],
        "Monthly_RMSE": tables["Monthly_RMSE"],
        "Weather_Bins": tables["Weather_Bins"],
        "Shading_Energy": tables["Shading_Energy"],
        "Shading_Hourly": tables["Shading_Hourly"],
        "Power_Exclusions": tables["Power_Exclusions"],
    }

    if "Provenance" in tables:
        workbook_tables["Provenance"] = tables["Provenance"]

    if "Logger_Clock" in tables:
        workbook_tables["Logger_Clock"] = tables["Logger_Clock"]

    workbook_tables["Master_Long"] = long_df

    try:
        with pd.ExcelWriter(
            MASTER_XLSX,
            engine="xlsxwriter",
        ) as writer:
            for sheet_name, df in workbook_tables.items():
                df.to_excel(
                    writer,
                    sheet_name=sheet_name[:31],
                    index=False,
                )

            format_excel(writer, workbook_tables)

    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "The 'xlsxwriter' package is needed to create the formatted "
            "master workbook. In the PyCharm terminal run:\n\n"
            "    pip install XlsxWriter\n\n"
            "Then rerun this script."
        ) from exc

    print("\nWROTE")
    print(f"  {MASTER_XLSX.relative_to(ROOT)}")
    print(f"  {MASTER_LONG.relative_to(ROOT)}")

    print(
        "\nImportant: this master is assembled from the current PD analysis "
        "outputs. It does not compare against or inherit values from the "
        "superseded September frozen workbook."
    )


if __name__ == "__main__":
    main()
