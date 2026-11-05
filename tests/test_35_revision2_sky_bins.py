"""Unit and source-integration checks for Revision 2 sky-bin statistics.

Run from repository root:
 python -m unittest discover -s tests -p 'test_35*.py' -v
"""
from __future__ import annotations

import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/35_rebuild_revision2_sky_bins.py"
spec = importlib.util.spec_from_file_location("revision2_sky_bins", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class MetricTests(unittest.TestCase):
    def test_simulated_minus_measured_bias_with_n_denominator(self):
        m = np.array([100.0, 200.0])
        p = np.array([120.0, 180.0])
        z = module.group_metrics(m, p)
        self.assertEqual(z["n"], 2)
        self.assertAlmostEqual(z["RMSE_W"], 20)
        self.assertAlmostEqual(z["MAE_W"], 20)
        self.assertAlmostEqual(z["MBE_W"], 0)
        self.assertAlmostEqual(z["nMBE_pct"], 0)
        self.assertAlmostEqual(z["CVRMSE_pct"], 100 * 20 / 150)
        self.assertAlmostEqual(z["measured_kWh"], 0.3)
        self.assertAlmostEqual(z["simulated_kWh"], 0.3)

    def test_positive_bias_is_model_overproduction(self):
        m = np.array([100.0, 200.0, 300.0])
        p = np.array([110.0, 220.0, 330.0])
        z = module.group_metrics(m, p)
        self.assertAlmostEqual(z["nMBE_pct"], 10)
        self.assertAlmostEqual(z["MBE_W"], 20)
        self.assertAlmostEqual(z["energy_bias_pct"], 10)
        self.assertNotAlmostEqual(z["nMBE_pct"], 10 * (3 / 2))

    def test_all_metrics_require_paired_and_nonzero_denominator(self):
        with self.assertRaises(AssertionError):
            module.group_metrics(np.array([1., 2.]), np.array([1.]))
        with self.assertRaises(AssertionError):
            module.group_metrics(np.array([0., 0.]), np.array([1., 1.]))
        with self.assertRaises(AssertionError):
            module.group_metrics(np.array([10., 20.]), np.array([1., np.nan]))

    def test_source_to_csv_rebuild_on_repository(self):
        sources = [ROOT / "config.json", ROOT / "derived_data/annual_unshaded_analysis.csv"]
        sources.extend(ROOT / "results/annual_audit" / x for x in module.STEP28_FILES.values())
        if not all(p.is_file() for p in sources):
            self.skipTest("Full audited Step 28 + original canonical geometry sources unavailable")
        outputs = [ROOT / "results/revision2" / x for x in module.OUTPUT_FILES]
        if not all(p.is_file() for p in outputs):
            self.skipTest("Revision 2 sky-bin outputs not yet present")
        # Full code run, source input checks, 180 independent stat rows and equality to outputs.
        module.run(ROOT, ROOT / "results/revision2", check_only=True)


if __name__ == "__main__":
    unittest.main()
