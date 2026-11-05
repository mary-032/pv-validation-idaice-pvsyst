"""Step 36: curate historical annual PV provenance without exposing row-level sources.

Requires LOCAL, previously generated (and normally untracked) Step 18--25 audit
CSVs in results/annual_audit/. The historical files are READ ONLY. New aggregate
outputs go into results/revision2/provenance/. This is *not* a recomputation of
the authoritative Step 28/29/35 results.

    python scripts/36_curate_early_provenance.py
    python scripts/36_curate_early_provenance.py --check-only
    python scripts/36_curate_early_provenance.py --verify-published

--verify-published works in a clean checkout without the confidential source
workbooks or locally untracked historical CSVs. It verifies the internally
published aggregate snapshots, not the original simulators or RISE raw logger.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "annual_audit"
DST = ROOT / "results" / "revision2" / "provenance"
CREATED = "2026-11-05"
STATUS = "HISTORICAL_DIAGNOSTIC_NOT_CURRENT_REVISION2"

INPUTS = [
    "18_approved_raw_reference_targets.csv",
    "18_pvsyst_project_manifest.csv",
    "19_pvsyst_variant_matrix.csv",
    "19_pvsyst_meteo_matrix.csv",
    "19_pvsyst_module_matrix.csv",
    "20_raw_AC_alignment_candidates.csv",
    "20_raw_measurement_inventory.csv",
    "22_ida_source_channel_reconciliation.csv",
    "22_pvsyst_EGrid_unit_reconciliation.csv",
    "24_SystemA_hourly_table_vs_sampled_audit.csv",
    "25_SystemA_interval_corrected_metrics.csv",
    "25_SystemA_interval_corrected_paired_CI30d.csv",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rows_for(name: str) -> list[dict[str, str]]:
    p = SRC / name
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        result = list(csv.DictReader(f))
    if not result:
        raise ValueError(f"Empty source CSV: {name}")
    return result


def csv_bytes(records: list[dict], columns: list[str]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue().encode("utf-8")


def csv_snapshot(name: str, records: list[dict], columns: list[str], output: dict[str, bytes]) -> None:
    output[name] = csv_bytes(records, columns)


def build() -> dict[str, bytes]:
    """Return deterministic public aggregate outputs; never export full hourly data."""
    data = {name: rows_for(name) for name in INPUTS}
    output: dict[str, bytes] = {}
    historic = []
    fields = ["historical_generation", "source_file", "interpretation", "status", *data[INPUTS[0]][0].keys()]
    for x in data[INPUTS[0]]:
        historic.append({"historical_generation": "Step18_sampled_IDA_prn",
                        "source_file": INPUTS[0],
                        "interpretation": "historical_sampled_AC_not_Step28_hourly_Table",
                        "status": STATUS, **x})
    if len(historic) != 3 or {x["system"] for x in historic} != set("ABC"):
        raise ValueError("Expected exactly three original Step18 targets")
    csv_snapshot("18_historical_sampled_AC_targets.csv", historic, fields, output)

    # Check same original source-file digests across the two independently
    # produced inventories. Do not publish source file names or raw excerpts.
    manifest = data["18_pvsyst_project_manifest.csv"]
    by_basename: dict[str, set[str]] = {}
    for x in manifest:
        key = Path(x["file"].replace("\\", "/")).name.casefold()
        by_basename.setdefault(key, set()).add(x["sha256"].casefold())
    m19 = [*data["19_pvsyst_variant_matrix.csv"],
           *data["19_pvsyst_meteo_matrix.csv"],
           *data["19_pvsyst_module_matrix.csv"]]
    matched = sum(x["sha256"].casefold() in by_basename.get(x["file"].casefold(), set()) for x in m19)
    bad_versions = sum(x.get("Version", "") == "[unexpected]" for x in m19)
    if matched != len(m19) or len(m19) != 16 or len(manifest) != 17:
        raise ValueError(f"PVsyst inventories disagree ({matched}/{len(m19)} matching)")
    csv_snapshot("19_pvsyst_inventory_consistency.csv", [{"step18_native_files": len(manifest),
                 "step19_metadata_records": len(m19), "matching_sha256": matched,
                 "invalid_historical_Version_fields": bad_versions,
                 "verified_original_pvsyst_software_version": "UNKNOWN",
                 "historical_export_variant_identity": "UNVERIFIED",
                 "status": STATUS}],
                 ["step18_native_files", "step19_metadata_records", "matching_sha256",
                  "invalid_historical_Version_fields", "verified_original_pvsyst_software_version",
                  "historical_export_variant_identity", "status"], output)

    align = data["20_raw_AC_alignment_candidates.csv"]
    raw = data["20_raw_measurement_inventory.csv"]
    dims = ["system", "ten_min_timestamp_interpretation", "measurement_shift_hours", "daytime_rule", "coverage_rule"]
    unique_counts = {k: len({x[k] for x in align}) for k in dims}
    if unique_counts != dict(zip(dims, [3, 2, 3, 3, 2])) or len(align) != 108:
        raise ValueError(f"Unexpected Step20 search grid {len(align)} {unique_counts}")
    if len(raw) != 3 or {x["system"] for x in raw} != set("ABC"):
        raise ValueError("Unexpected raw measurement inventory")
    raw_counts = {x["system"]: int(x["raw_rows"]) for x in raw}
    if any(v != 52560 for v in raw_counts.values()):
        raise ValueError(f"Unexpected raw 10-minute count: {raw_counts}")
    csv_snapshot("20_alignment_diagnostic_coverage.csv", [
        {"system": s, "raw_ten_min_rows": raw_counts[s], "number_of_alignment_candidates": sum(x["system"] == s for x in align),
         "selection_status": "diagnostic_grid_not_independent_logger_authentication", "status": STATUS}
        for s in "ABC"], ["system", "raw_ten_min_rows", "number_of_alignment_candidates", "selection_status", "status"], output)

    ida = data["22_ida_source_channel_reconciliation.csv"]
    pv = data["22_pvsyst_EGrid_unit_reconciliation.csv"]
    channel = []
    for s in "ABC":
        sources = [x for x in ida if x["system"] == s and x["source_channel"] == "produced_p" and x["population"] == "all_hours"]
        unit = [x for x in pv if x["system"] == s]
        if len(sources) != 1 or len(unit) != 1:
            raise ValueError(f"Missing unique Step22 audit rows: {s}")
        a, b = sources[0], unit[0]
        if int(a["n"]) != 8736 or float(a["MAE_W"]) != 0 or float(b["max_abs_deviation_W"]) != 0:
            raise ValueError(f"Unexpected original channel agreement: {s}")
        channel.append({"system": s, "sampled_IDA_produced_p_matching_hours": a["n"],
                        "sampled_IDA_produced_p_MAE_W": a["MAE_W"],
                        "PVsyst_finite_unit_pair_count": b["n_valid"],
                        "PVsyst_max_unit_pair_abs_deviation_W": b["max_abs_deviation_W"],
                        "interpretation": "sampled_IDA_channel_not_hourly_Table;finite_PVsyst_pairs_only",
                        "status": STATUS})
    csv_snapshot("22_source_channel_consistency.csv", channel,
                 ["system", "sampled_IDA_produced_p_matching_hours", "sampled_IDA_produced_p_MAE_W",
                  "PVsyst_finite_unit_pair_count", "PVsyst_max_unit_pair_abs_deviation_W", "interpretation", "status"], output)

    # Derive an aggregate QC check without releasing the 8736 original hourly
    # native IDA Table rows. This is mathematical source consistency, not an
    # independent audit of fine-resolution integration semantics.
    table = data["24_SystemA_hourly_table_vs_sampled_audit.csv"]
    indexes = [int(x["ida_time_h"]) for x in table]
    if indexes != list(range(1, 8737)):
        raise ValueError("Step24 Table missing/duplicate/unsorted hour index")
    diffs = [float(x["hourly_table_minus_endpoint_mean_W"]) for x in table]
    if not all(math.isfinite(x) for x in diffs) or max(map(abs, diffs)) > 0.051:
        raise ValueError("Step24 Table did not match mean of adjacent endpoints")
    summary = [{"system": "A", "native_hourly_table_rows": len(table),
                "max_abs_Table_minus_endpoint_average_W": format(max(map(abs, diffs)), ".8f"),
                "mean_abs_Table_minus_endpoint_average_W": format(math.fsum(map(abs, diffs)) / len(diffs), ".8f"),
                "interpretation": "consecutive_elapsed_hour_Table;not_independently_subhourly_integrated",
                "status": STATUS}]
    csv_snapshot("24_SystemA_hourly_Table_QC.csv", summary,
                 list(summary[0]), output)

    step25 = data["25_SystemA_interval_corrected_metrics.csv"]
    allowed = {"IDA ICE hourly mean, end-aligned", "IDA ICE sampled", "PVsyst E_Grid"}
    metric_rows = []
    for x in step25:
        if x["output"] not in allowed:
            continue  # Invalid same-index Table comparison is retained in private original.
        x = dict(x)
        x["interpretation"] = ("historical_sampled_comparator" if x["output"] == "IDA ICE sampled" else
                               "Step25_intermediate;Stage28_three_system_result_is_authoritative")
        x["status"] = STATUS
        metric_rows.append(x)
    if len(metric_rows) != 6 or {x["scenario"] for x in metric_rows} != {"civil_unshifted", "fixed_CET_hypothesis"}:
        raise ValueError("Step25 selected comparison population changed")
    csv_snapshot("25_SystemA_selected_model_metrics.csv", metric_rows,
                 [*data["25_SystemA_interval_corrected_metrics.csv"][0].keys(), "interpretation", "status"], output)

    ci_rows = []
    for x in data["25_SystemA_interval_corrected_paired_CI30d.csv"]:
        if x["IDA_channel"] != "IDA_hourly_end_aligned":
            continue
        x = dict(x)
        x["interpretation"] = "Step25_A_only_historical_replication_of_later_Step28_A"
        x["status"] = STATUS
        ci_rows.append(x)
    if len(ci_rows) != 2:
        raise ValueError("Expected two Step25 end-aligned clock CIs")
    csv_snapshot("25_SystemA_hourly_Table_paired_CI30d.csv", ci_rows,
                 [*data["25_SystemA_interval_corrected_paired_CI30d.csv"][0].keys(), "interpretation", "status"], output)

    manifest_record = {"stage": 36, "created": CREATED, "status": STATUS,
       "purpose": "non-destructive curation of 2026-10 historical source diagnostics",
       "not_authoritative_for_revision2": True,
       "current_reference": ["results/annual_audit/28_*", "results/revision2/29_*", "results/revision2/35_*"],
       "original_source_artifact_sha256": {name: digest((SRC/name).read_bytes()) for name in INPUTS},
       "curated_output_sha256": {name: digest(content) for name, content in output.items()},
       "source_release_permissions_confirmed": False,
       "original_logger_clock_authenticated": False,
       "third_party_native_project_files_distributed": False,
       "note": "These curated aggregates are not full source reproduction; avoid claims of upstream configuration verification."}
    output["36_curation_manifest.json"] = (json.dumps(manifest_record, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    return output


def verify_published() -> None:
    manifest = json.loads((DST/"36_curation_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != STATUS:
        raise ValueError("Unexpected curation status")
    if manifest["source_release_permissions_confirmed"] is not False:
        raise ValueError("Permission status is not explicitly unconfirmed")
    if manifest["original_logger_clock_authenticated"] is not False:
        raise ValueError("Clock authentication status unexpectedly changed")
    expected = manifest["curated_output_sha256"]
    for name, sha in expected.items():
        data = (DST / name).read_bytes()
        if digest(data) != sha:
            raise ValueError(f"Published curated output altered: {name}")
    def read(name):
        with (DST/name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    if len(read("18_historical_sampled_AC_targets.csv")) != 3: raise ValueError("Step18 rows")
    q19 = read("19_pvsyst_inventory_consistency.csv")[0]
    if (int(q19["matching_sha256"]), int(q19["invalid_historical_Version_fields"])) != (16, 16):
        raise ValueError("Step19 provenance counts unexpectedly changed")
    if len(read("20_alignment_diagnostic_coverage.csv")) != 3: raise ValueError("Step20 rows")
    if len(read("22_source_channel_consistency.csv")) != 3: raise ValueError("Step22 rows")
    if len(read("24_SystemA_hourly_Table_QC.csv")) != 1: raise ValueError("Step24 rows")
    if len(read("25_SystemA_selected_model_metrics.csv")) != 6: raise ValueError("Step25 rows")
    if len(read("25_SystemA_hourly_Table_paired_CI30d.csv")) != 2: raise ValueError("Step25 CI rows")
    for name in expected:
        content = (DST / name).read_text(encoding="utf-8")
        if "[unexpected]" in content or "C:\\Users\\" in content:
            raise ValueError(f"Unsafe or misleading text in published output {name}")
    print("PASS: 7 curated historical aggregates; manifest digests; explicit uncertainty/rights flags")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    opts = parser.add_mutually_exclusive_group()
    opts.add_argument("--check-only", action="store_true", help="Compare all aggregates to original local historical CSVs")
    opts.add_argument("--verify-published", action="store_true", help="Check committed curated aggregates without original CSVs")
    args = parser.parse_args()
    if args.verify_published:
        verify_published()
        return
    expected = build()
    DST.mkdir(parents=True, exist_ok=True)
    if args.check_only:
        for name, data in expected.items():
            file = DST/name
            if not file.exists() or file.read_bytes() != data:
                raise ValueError(f"Curated aggregate missing/changed: {file}")
        print("PASS: 8 file outputs match all 12 original local historical input CSVs")
    else:
        for name, data in expected.items():
            (DST/name).write_bytes(data)
            print("WROTE", (DST/name).relative_to(ROOT))
        verify_published()


if __name__ == "__main__":
    main()
