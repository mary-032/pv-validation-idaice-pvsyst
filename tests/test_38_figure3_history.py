"""Standard-library-only tests for Step 38 (no original private files required)."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/38_audit_figure3_history.py'
spec = importlib.util.spec_from_file_location('step38_audit_figure3_history', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def old_row(n=101, cv=20, nmb=-10.1):
    return {'scenario': 'fixed_CET_hypothesis', 'system': 'A',
            'selection': 'Eext_positive_AOI_lt80', 'model': 'IDA ICE',
            'sky_bin': 'Clear', 'n': str(n), 'CVRMSE_pct': str(cv),
            'nMBE_measured_minus_sim_pct': str(nmb)}


def current_row(n=101, cv=20, nmb=10):
    return {'scenario': 'fixed_CET_hypothesis', 'system': 'A',
            'selection': 'Eext_positive_AOI_lt80', 'model': 'IDA ICE',
            'sky_bin': 'Clear', 'n': str(n), 'CVRMSE_pct': str(cv),
            'nMBE_pct': str(nmb)}


class Figure3ArchiveVerification(unittest.TestCase):
    def test_sign_and_n_minus_one_reconciliation(self):
        result = module.reconcile_historical([old_row()], [current_row()], expected_count=1)
        self.assertEqual(result['matched_rows'], 1)
        self.assertLess(result['max_abs_nMBE_diff_pp_after_sign_and_denominator_fix'], 1e-12)
        self.assertAlmostEqual(result['max_abs_nMBE_diff_pp_if_sign_only'], 0.1)

    def test_sign_alone_is_not_sufficient(self):
        with self.assertRaisesRegex(ValueError, 'nMBE divergence'):
            module.reconcile_historical([old_row(nmb=-10)], [current_row(nmb=10)], expected_count=1)

    def test_changed_cohort_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'sample mismatch'):
            module.reconcile_historical([old_row(n=101)], [current_row(n=100)], expected_count=1)

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate key'):
            module.keyed([old_row(), old_row()], module.KEY)

    def test_report_must_be_outside_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'fake_repo').mkdir()
            repo = base / 'fake_repo'
            with self.assertRaisesRegex(ValueError, 'Refusing to write'):
                module.write_report_safely(repo / 'results/report.json', repo, {'value': 1})
            target = base / 'private/report.json'
            module.write_report_safely(target, repo, {'value': 1})
            self.assertTrue(target.exists())
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                module.write_report_safely(target, repo, {'value': 2})

    def test_legacy_scripts_are_never_executed(self):
        source = SCRIPT.read_text(encoding='utf-8')
        ast.parse(source)
        self.assertNotIn('subprocess.', source)
        self.assertNotIn('runpy.', source)
        self.assertNotIn('exec(', source)

    def test_current_step35_from_public_repository(self):
        root = SCRIPT.parents[1]
        full, primary = module.verify_current(root)
        self.assertEqual(len(full), 180)
        self.assertEqual(len(primary), 30)


if __name__ == '__main__':
    unittest.main()
