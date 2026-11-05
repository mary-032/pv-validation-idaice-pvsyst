"""Public Step 36 aggregates: run with unittest, no raw RISE/PVsyst inputs required."""
from __future__ import annotations

import csv
import importlib.util
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "36_curate_early_provenance.py"
spec = importlib.util.spec_from_file_location("step36_curator", SCRIPT)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def load(name):
    with (ROOT / "results" / "revision2" / "provenance" / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class ProvenanceTests(unittest.TestCase):
    def test_integrity_without_original_sources(self):
        module.verify_published()

    def test_historical_step18_not_selected_annual_output(self):
        data = load("18_historical_sampled_AC_targets.csv")
        self.assertEqual({r["system"] for r in data}, {"A", "B", "C"})
        self.assertTrue(all(r["status"] == module.STATUS for r in data))
        self.assertAlmostEqual(float(next(r for r in data if r["system"] == "A")["IDA_RMSE_W"]), 249.5025044)

    def test_first_reconciliation_and_unit_check_are_limited(self):
        data = load("22_source_channel_consistency.csv")
        expected = {"A": 3880, "B": 3933, "C": 3377}
        for r in data:
            self.assertEqual(int(r["sampled_IDA_produced_p_matching_hours"]), 8736)
            self.assertEqual(float(r["sampled_IDA_produced_p_MAE_W"]), 0)
            self.assertEqual(int(r["PVsyst_finite_unit_pair_count"]), expected[r["system"]])
            self.assertIn("finite_PVsyst_pairs_only", r["interpretation"])

    def test_step25_pairwise_clock_alternatives_are_preserved(self):
        metrics = load("25_SystemA_selected_model_metrics.csv")
        def rmse(scenario, label):
            matches = [x for x in metrics if x["scenario"] == scenario and x["output"] == label]
            self.assertEqual(len(matches), 1)
            return float(matches[0]["RMSE_W"])
        self.assertTrue(math.isclose(rmse("fixed_CET_hypothesis", "IDA ICE hourly mean, end-aligned"), 149.98075505, abs_tol=1e-6))
        self.assertTrue(math.isclose(rmse("fixed_CET_hypothesis", "PVsyst E_Grid"), 252.46308304, abs_tol=1e-6))
        self.assertTrue(math.isclose(rmse("civil_unshifted", "IDA ICE hourly mean, end-aligned"), 390.93052517, abs_tol=1e-6))
        self.assertTrue(math.isclose(rmse("civil_unshifted", "PVsyst E_Grid"), 288.01986465, abs_tol=1e-6))
        ci = load("25_SystemA_hourly_Table_paired_CI30d.csv")
        self.assertEqual({r["scenario"] for r in ci}, {"fixed_CET_hypothesis", "civil_unshifted"})
        self.assertTrue(all(int(r["n_boot"]) == 5000 for r in ci))

    def test_step19_version_is_not_reported_as_verified(self):
        m = load("19_pvsyst_inventory_consistency.csv")
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0]["verified_original_pvsyst_software_version"], "UNKNOWN")
        self.assertEqual(m[0]["historical_export_variant_identity"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
