"""Tests for Step 29 AC aggregation.

Run: python -m unittest discover -s tests -p 'test_29*.py'
A source-data integration test is included if the committed Step 28
CSV files and Step 29 output CSV files are present in the checkout.
"""
import importlib.util
import math
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "29_aggregate_revision2_annual_AC.py"
spec = importlib.util.spec_from_file_location("aggregate_revision2_ac", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class AggregationTests(unittest.TestCase):
    def test_one_interval_metrics(self):
        rows = [
            {"m": 100.0, "ida": 110.0, "pv": 90.0},
            {"m": 200.0, "ida": 180.0, "pv": 210.0},
        ]
        ida = module.metrics(rows, "ida")
        self.assertEqual(ida["n"], 2)
        self.assertAlmostEqual(ida["RMSE_W"], math.sqrt(250))
        self.assertAlmostEqual(ida["MAE_W"], 15)
        self.assertAlmostEqual(ida["MBE_W"], -5)
        self.assertAlmostEqual(ida["energy_bias_pct"], -100 / 30)
        self.assertAlmostEqual(ida["CVRMSE_pct"], math.sqrt(250) / 150 * 100)
        self.assertAlmostEqual(ida["measured_kWh"], 0.3)
        pv = module.metrics(rows, "pv")
        self.assertAlmostEqual(pv["energy_bias_pct"], 0)
        self.assertAlmostEqual(pv["RMSE_W"], 10)

    def test_season_mapping(self):
        self.assertEqual(module.season(1), "DJF")
        self.assertEqual(module.season(3), "MAM")
        self.assertEqual(module.season(6), "JJA")
        self.assertEqual(module.season(9), "SON")
        self.assertEqual(module.season(12), "DJF")

    def test_group_preserves_rows(self):
        rows = [{"date": "2020-06-01 05:00:00", "m": 10},
                {"date": "2020-06-01 06:00:00", "m": 15},
                {"date": "2020-07-01 05:00:00", "m": 7}]
        grouped = module.group(rows, lambda x: x["date"][:7])
        self.assertEqual(list(grouped), ["2020-06", "2020-07"])
        self.assertEqual(sum(len(v) for v in grouped.values()), 3)

    def test_checked_step28_integration(self):
        if not all((module.SOURCE / path).exists()
                   for path in module.INPUTS.values()):
            self.skipTest("Step 28 input CSVs not available")
        if not all((module.DEST / path).exists()
                   for path in module.FIELDS):
            self.skipTest("Committed Step 29 outputs not available")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--check-only"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0,
                         result.stdout + "\n" + result.stderr)
        self.assertIn("PASS: both 4,478-hour cohorts", result.stdout)


if __name__ == "__main__":
    unittest.main()
