#!/usr/bin/env python3
"""Read-only reconciliation of *local historical* Figure 3 (Steps 30–34).

The current numerical reference is the committed Step 35 Revision 2 output.
This script does NOT regenerate, publish, overwrite, or execute historical
code, and does not read hourly measurements. No third-party assets are bundled.

Commands:
  python scripts/38_audit_figure3_history.py --verify-current
  python scripts/38_audit_figure3_history.py --local-audit

Optional --report-json PATH requires a path outside the repository checkout.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "results/revision2"
HIST = ROOT / "results/annual_audit"
KEY = ("scenario", "system", "selection", "model", "sky_bin")
SAMPLE_COUNTS = {"primary_annual_AC": 4478, "primary_figure3": 3593,
                 "unfiltered_Eext_positive": 3932, "provisional_step30": 3844}
CV_TOL = 1e-6  # percentage points; historical CSVs have finite decimal formatting
NMBE_TOL = 1e-6  # percentage points, after sign *and* n-1 correction

# Original historical files are intentionally NOT checked into the repository.
# Digests come from the archived local audit ZIP and were matched to the
# researcher's PowerShell inventory on 2026-11-06.
HISTORICAL_SHA256 = {
    "scripts/30_recompute_monthly_and_sky_bins.py": "49cdef111ebac44a9db280b8c876291c4d7caefb7498066136f9b9be4d0f3723",
    "scripts/31_reconcile_canonical_sky_geometry.py": "25e967ca63403500e4ed3c3d14cc417fa5211c2ba7165db46e6081bb47732505",
    "scripts/32_render_sky_bin_figure_candidates.py": "152b60445d8e244468ceb961f23d8d69caeb5ddb79fd95876c305d3b317f8ced",
    "scripts/34_render_Figure3_compact.py": "1fcd0f5df9898949f0e4dab4781b5b1c32de348055f918a48188b1d17c67bfc0",
    "results/annual_audit/30_AUDIT.md": "55af9ca65134c4cceb04b761d7c82c16eb61d60557d160569dcb1eed06a0a2a0",
    "results/annual_audit/31_canonical_sky_geometry_audit.md": "b8c657f726a023ea1e8256a8c1a037daa26da671c8d181cac334ba536504619c",
    "results/annual_audit/32_Figure3_candidate_method_note.md": "0da5ae8046661b3dcc98477264478bfc27c5a1693d88c93a489a6159b4576b26",
    "results/annual_audit/34_Figure3_fixed_CET_AOI_lt80_COMPACT_manifest.json": "9683154e7572e0552e4dd5721f3d31954f607fb2b8c1952afdaea20599701f32",
    "results/annual_audit/30_sky_bins_provisional.csv": "45c68437a3a99389f50d6064c868b91c16c03e0b95cab26986078d76942a3756",
    "results/annual_audit/31_canonical_sky_bin_statistics.csv": "ba55fba25ed48898672539dabe094e8ffc08524a8c16e04cee1d40f065d4bedc",
    "results/annual_audit/32_Figure3_candidate_source_statistics.csv": "ea9a136d82d24c59f63248860bc5957147bb68c967e65f5bfce633cc539c008c",
}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def sha256(path: Path) -> str:
    with path.open("rb") as f:
        h = hashlib.sha256()
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rows(path: Path, required: set[str], n_rows: int) -> list[dict[str, str]]:
    require(path.is_file(), f"Missing input: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        require(reader.fieldnames is not None and required.issubset(reader.fieldnames),
                f"Missing columns in {path.name}: {sorted(required - set(reader.fieldnames or []))}")
        rows = list(reader)
    require(len(rows) == n_rows,
            f"Unexpected {path.name} row count: {len(rows)} (expected {n_rows})")
    return rows


def keyed(rows: list[dict[str, str]], keys: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, str]]:
    result = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        require(key not in result, f"Duplicate key: {key}")
        result[key] = row
    return result


def verify_current(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    base = root / "results/revision2"
    required = set(KEY) | {"n", "CVRMSE_pct", "nMBE_pct"}
    full = read_rows(base / "35_sky_bin_statistics_all_scenarios.csv", required, 180)
    primary = read_rows(base / "35_Figure3_primary_source_statistics.csv", required, 30)
    full_map = keyed(full, KEY)
    primary_map = keyed(primary, KEY)
    require(len(full_map) == 180 and len(primary_map) == 30, "Duplicate Step 35 keys")
    for key, row in primary_map.items():
        require(key[0] == "fixed_CET_hypothesis" and key[2] == "Eext_positive_AOI_lt80",
                f"Unexpected current primary cohort: {key}")
        require(key in full_map, f"Missing primary row in all-scenario Step 35: {key}")
        other = full_map[key]
        for col in ("n", "CVRMSE_pct", "nMBE_pct"):
            require(row[col] == other[col], f"Current Step 35 primary mismatch: {key}/{col}")
    for scenario in ("fixed_CET_hypothesis", "civil_unshifted"):
        for system in ("A", "B", "C"):
            for model in ("IDA ICE", "PVsyst"):
                for selection, n_expected in (("Eext_positive_AOI_lt80", 3593), ("Eext_positive", 3932)):
                    selected = [r for r in full if r["scenario"] == scenario and r["system"] == system
                                and r["model"] == model and r["selection"] == selection]
                    require(len(selected) == 5 and sum(int(r["n"]) for r in selected) == n_expected,
                            f"Bad Step35 selection count: {scenario}/{system}/{model}/{selection}")
    return full, primary


def reconcile_historical(old: list[dict[str, str]],
                         current: list[dict[str, str]], *, expected_count: int) -> dict:
    """For Step 31/32: old nMBE = -current nMBE * n/(n-1).

    The legacy value is 100 * sum(measured - simulated) / [(n-1)*mean(measured)].
    The Step 35 value is 100 * sum(simulated - measured) / sum(measured).
    Merely negating the old series is numerically *incorrect*.
    """
    oldmap, newmap = keyed(old, KEY), keyed(current, KEY)
    require(len(oldmap) == expected_count, "Unexpected historical key count")
    require(set(oldmap).issubset(newmap), "Historical records absent from Step 35")
    max_cv, max_corrected_nmb, max_sign_only_nmb = 0., 0., 0.
    for key, earlier in oldmap.items():
        later = newmap[key]
        n_old, n_new = int(earlier["n"]), int(later["n"])
        require(n_old == n_new and n_old > 1, f"Historical sample mismatch: {key}")
        cv_err = abs(float(earlier["CVRMSE_pct"]) - float(later["CVRMSE_pct"]))
        original = float(earlier["nMBE_measured_minus_sim_pct"])
        release = float(later["nMBE_pct"])
        require(all(map(math.isfinite, (cv_err, original, release))), f"Nonfinite metric: {key}")
        # Fix BOTH sign convention and old n-1 normalization:
        converted = -original * (n_old - 1) / n_old
        nmb_err = abs(converted - release)
        only_sign_err = abs(-original - release)
        max_cv = max(max_cv, cv_err)
        max_corrected_nmb = max(max_corrected_nmb, nmb_err)
        max_sign_only_nmb = max(max_sign_only_nmb, only_sign_err)
        require(cv_err <= CV_TOL, f"Historical CV(RMSE) divergence: {key} {cv_err}")
        require(nmb_err <= NMBE_TOL, f"Historical nMBE divergence: {key} {nmb_err}")
    return {"matched_rows": len(oldmap), "counts_equal": True,
            "max_abs_CVRMSE_diff_pp": max_cv,
            "max_abs_nMBE_diff_pp_after_sign_and_denominator_fix": max_corrected_nmb,
            "max_abs_nMBE_diff_pp_if_sign_only": max_sign_only_nmb}


def reconcile_provisional(step30: list[dict[str, str]],
                          current: list[dict[str, str]]) -> dict:
    """Compare *counts only*. Step 30 used a different geometry/clock instant.

    DO NOT reinterpret the 30_* CV(RMSE) or nMBE as Step 35 metrics.
    """
    oldmap = keyed(step30, ("scenario", "system", "model", "bin"))
    newer = keyed([r for r in current if r["selection"] == "Eext_positive"],
                  ("scenario", "system", "model", "sky_bin"))
    require(len(oldmap) == len(newer) == 60 and set(oldmap) == set(newer),
            "Step 30 vs Step 35 unfiltered keys differ")
    n_diff = sum(int(row["n"]) != int(newer[key]["n"]) for key, row in oldmap.items())
    n_total_before = sum(int(row["n"]) for row in oldmap.values())
    n_total_current = sum(int(row["n"]) for row in newer.values())
    require(n_total_before == 3844 * 2 * 3 * 2, "Unexpected Step30 cohort size")
    require(n_total_current == 3932 * 2 * 3 * 2, "Unexpected Step35 Eext-positive cohort size")
    return {"paired_rows": len(oldmap), "bins_with_changed_n": n_diff,
            "eligible_hours_per_system_per_model_step30": 3844,
            "eligible_hours_per_system_per_model_step35_unfiltered": 3932,
            "numerical_metrics_directly_comparable": False}


def constant_dict(source: Path, name: str) -> dict:
    """Read literal color dictionaries with AST; never execute historical scripts."""
    nodes = ast.parse(source.read_text(encoding="utf-8"), filename=source.name).body
    for node in nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == name:
                obj = ast.literal_eval(node.value)
                require(isinstance(obj, dict), f"Unexpected {name} literal")
                return obj
    raise ValueError(f"No static {name} in {source.name}")


def audit_local(root: Path) -> dict:
    # Verify historically observed bytes, not just file names, before comparing.
    for relative, expected in HISTORICAL_SHA256.items():
        p = root / relative
        require(p.is_file(), f"Missing historical source: {relative}")
        require(sha256(p) == expected, f"Historical source fingerprint mismatch: {relative}")
    current, _ = verify_current(root)
    hist = root / "results/annual_audit"
    old31 = read_rows(hist / "31_canonical_sky_bin_statistics.csv",
                      set(KEY) | {"n", "CVRMSE_pct", "nMBE_measured_minus_sim_pct"}, 180)
    old32 = read_rows(hist / "32_Figure3_candidate_source_statistics.csv",
                      set(KEY) | {"n", "CVRMSE_pct", "nMBE_measured_minus_sim_pct"}, 90)
    old30 = read_rows(hist / "30_sky_bins_provisional.csv",
                      {"scenario", "system", "model", "bin", "n", "CVRMSE_pct",
                       "nMBE_measured_minus_sim_pct"}, 60)
    step34 = json.loads((hist / "34_Figure3_fixed_CET_AOI_lt80_COMPACT_manifest.json").read_text(encoding="utf-8"))
    require(step34["source_sha256"] == sha256(hist / "31_canonical_sky_bin_statistics.csv"),
            "Step 34 source is not the archived Step 31 data")
    p32 = constant_dict(root / "scripts/32_render_sky_bin_figure_candidates.py", "COLORS")
    p34 = constant_dict(root / "scripts/34_render_Figure3_compact.py", "COLORS")
    require(p32["IDA ICE"] == (0.466, 0.674, 0.188) and p32["PVsyst"] == (0, 0.447, 0.741),
            "Step 32 palette changed; review color convention")
    require(p34 == {"IDA ICE": "#0072BD", "PVsyst": "#77AC30"},
            "Step 34 palette changed; review color convention")
    return {"status": "HISTORICAL_SNAPSHOT_RECONCILED_NOT_A_RELEASE",
            "historical_file_sha256_verified": len(HISTORICAL_SHA256),
            "step30_vs_step35_unfiltered": reconcile_provisional(old30, current),
            "step31_vs_step35_all_scenarios": reconcile_historical(old31, current, expected_count=180),
            "step32_vs_step35_selected_scenarios": reconcile_historical(old32, current, expected_count=90),
            "step34": {"source_digest_matches_step31": True,
                       "palette": p34, "palette_reversed_relative_to_step32_and_step35": True,
                       "nMBE_only_negates_step31_biased_n_minus_1_values": True},
            "step33": "NOT_PRESENT_IN_SUPPLIED_LOCAL_ARCHIVE_OR_INVENTORY",
            "publication": "DOCUMENTATION_ONLY; DO_NOT_PUBLISH_NATIVE_OR_HOURLY_SOURCES"}


def write_report_safely(path: Path, root: Path, result: dict) -> None:
    target = path.expanduser().resolve()
    source_root = root.resolve()
    require(not target.is_relative_to(source_root),
            "Refusing to write a report inside the Git repository; use a private temp folder")
    target.parent.mkdir(parents=True, exist_ok=True)
    require(not target.exists(), "Refusing to overwrite an existing report")
    with target.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2, sort_keys=True)
        out.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-current", action="store_true", help="Check only committed Step 35 files")
    mode.add_argument("--local-audit", action="store_true", help="Check local historical hashes and reconcile 30–34 with Step 35")
    parser.add_argument("--report-json", type=Path, help="Optional new report file OUTSIDE the repository")
    args = parser.parse_args()
    if args.local_audit:
        summary = audit_local(ROOT)
    else:
        full, primary = verify_current(ROOT)
        summary = {"status": "CURRENT_STEP35_VERIFIED", "all_scenario_rows": len(full),
                   "primary_rows": len(primary), "historical_files_not_required": True}
    if args.report_json:
        write_report_safely(args.report_json, ROOT, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("PASS: read-only Step 38 audit; NO historical sources or model results modified")


if __name__ == "__main__":
    main()
