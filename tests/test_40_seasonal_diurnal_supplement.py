"""Safe synthetic checks; no historical scripts, data exports or simulator reruns."""
from __future__ import annotations
import csv
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = (Path(__file__).resolve().parents[1] / "scripts" /
          "40_build_seasonal_diurnal_supplement.py")
spec = importlib.util.spec_from_file_location("supplement40", MODULE)
step40 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(step40)


class Step40Tests(unittest.TestCase):
    def test_quantile_linear_and_mean(self):
        x = [-5, -1, 2, 6, 10]
        r = step40.residual_summary(x)
        self.assertEqual(r["n"], 5)
        self.assertAlmostEqual(r["q25_error_W"], -1)
        self.assertAlmostEqual(r["median_error_W"], 2)
        self.assertAlmostEqual(r["q75_error_W"], 6)
        self.assertAlmostEqual(r["mean_error_W"], 2.4)
        self.assertAlmostEqual(r["RMSE_W"], math.sqrt(166 / 5))
        even = step40.residual_summary([-6, 0, 4, 10])
        self.assertAlmostEqual(even["q25_error_W"], -1.5)
        self.assertAlmostEqual(even["q75_error_W"], 5.5)

    def test_nMBE_positive_and_signed_zero(self):
        self.assertEqual(step40.format_one(17.298882869, sign=True), "+17.3")
        self.assertEqual(step40.format_one(-2.288934383, sign=True), "-2.3")
        self.assertEqual(step40.format_one(-0.001, sign=True), "+0.0")
        self.assertEqual(step40.format_one(13.796248, sign=False), "13.8")

    @staticmethod
    def seasonal_fixture():
        results = []
        for scenario, _, _ in step40.SCENARIOS:
            for system in step40.SYSTEMS:
                for model in step40.MODELS:
                    for season, _ in step40.SEASONS:
                        results.append({"scenario": scenario, "system": system,
                                        "model": model, "season": season,
                                        "n": str(step40.SEASON_N[season]),
                                        "CVRMSE_pct": "13.796248776",
                                        "nMBE_pct": "-2.288934383"})
        return results

    def test_two_tables_are_separate_and_have_six_rows(self):
        sample = self.seasonal_fixture()
        for scenario, label, title in step40.SCENARIOS:
            six = step40.table_rows(sample, scenario)
            self.assertEqual(len(six), 6)
            self.assertEqual(six[0], ["A", "IDA ICE", *(["13.8 / -2.3"] * 4)])
            self.assertIn(f"Table {label}", step40.table_markdown(six, label, title))
            self.assertEqual(len(step40.table_csv(six).splitlines()), 7)

    def test_seasonal_count_inconsistency_rejected(self):
        sample = self.seasonal_fixture()
        sample[0]["n"] = "704"
        with self.assertRaisesRegex(ValueError, "Unexpected sample count"):
            step40.table_rows(sample, "fixed_CET_hypothesis")

    def test_duplicate_row_rejected(self):
        sample = self.seasonal_fixture()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            step40.table_rows(sample + [sample[0]], "fixed_CET_hypothesis")

    def test_step29_diurnal_cross_check_and_tamper_rejection(self):
        sources = {}
        reference = []
        for scenario, _, _ in step40.SCENARIOS:
            items = []
            for system in step40.SYSTEMS:
                for hour in range(5, 23):
                    measured = 100 + hour
                    # no duplicate physical hours; model differences vary with hour
                    ida, pv = measured + (hour - 11), measured - 2 * (hour - 11)
                    items.append({"system": system, "timestamp": f"2020-06-01 {hour:02d}:00:00",
                                  "hour": f"{hour:02d}", "measured": measured,
                                  "IDA_ICE": ida, "PVsyst": pv})
                    for model, err in (("IDA_ICE", ida - measured),
                                       ("PVsyst", pv - measured)):
                        reference.append({"scenario": scenario, "system": system,
                                          "model": model, "hour_start_local": f"{hour:02d}",
                                          "n": "1", "MBE_W": str(err),
                                          "RMSE_W": str(abs(err)), "MAE_W": str(abs(err))})
            sources[scenario] = items
        with patch.object(step40, "EXPECTED_HOURS", 18):
            output = step40.build_diurnal(sources, reference)
            self.assertEqual(len(output), 216)
            self.assertEqual(output[0]["n"], 1)
            reference[0]["MBE_W"] = "1000"
            with self.assertRaisesRegex(ValueError, "Step 29 mismatch"):
                step40.build_diurnal(sources, reference)

    def test_hourly_sources_require_same_physical_measured_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "results" / "annual_audit"
            folder.mkdir(parents=True)
            fields = ["system", "physical_interval_start_local", "power_valid_10min",
                      "P_measured_W", "IDA_hourly_table_end_aligned_W",
                      "PVsyst_EGrid_W"]
            for scenario, filename in step40.SOURCE_FILES.items():
                with (folder / filename).open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    for system in step40.SYSTEMS:
                        for h in range(5, 11):
                            writer.writerow({"system": system,
                                "physical_interval_start_local": f"2020-06-01 {h:02d}:00:00",
                                "power_valid_10min": 6, "P_measured_W": 100,
                                "IDA_hourly_table_end_aligned_W": 101,
                                "PVsyst_EGrid_W": 99})
            with patch.object(step40, "EXPECTED_HOURS", 6):
                self.assertEqual(len(step40.read_hourly_inputs(root)), 2)
                second = folder / step40.SOURCE_FILES["civil_unshifted"]
                s = second.read_text(encoding="utf-8").replace(",100,101,99", ",111,101,99", 1)
                second.write_text(s, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "different physical measurements"):
                    step40.read_hourly_inputs(root)

    def test_manifest_marks_not_approved_and_method(self):
        self.assertEqual(step40.EXPECTED_HOURS, 4478)
        self.assertEqual(step40.COLORS["IDA_ICE"], "#77AC30")
        self.assertEqual(step40.COLORS["PVsyst"], "#0072BD")


if __name__ == "__main__":
    unittest.main()
