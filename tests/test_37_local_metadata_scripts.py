"""Zero-third-party-data tests for historical Step 18/19 source-script fixes."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_local(name):
    path = ROOT / 'scripts' / name
    spec = importlib.util.spec_from_file_location(name.replace('.py', ''), path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class SourceMetadataSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.annual = self.repo / 'simulation_models' / 'annual' / 'PVsyst'
        self.shaded = self.repo / 'simulation_models' / 'shaded' / 'PVsyst'
        self.annual.mkdir(parents=True)
        self.shaded.mkdir(parents=True)
        (self.annual / 'Test.VC0').write_text(
            'system 3\nNomF=weather.MET\nVersion=PVSyst unknown free text\n'
            'Comment=Fixed, Tilt 45.0°, Azim. 0.0°\n', encoding='utf8')
        (self.annual / 'Test.PRJ').write_text('NomF=weather.MET\nVersion=8.0.2 beta\n', encoding='utf8')
        (self.annual / 'Test.PAN').write_text('Version=PVsyst 8.0.2 beta\n',encoding='utf8')
        (self.annual / 'weather.MET').write_text(
            'Latitude=57.71\nLongitude=12.8\nAltitude=125\nTimeZone=1\n'
            'NomFSource=C:\\Users\\someone\\Private\\weather.MET\n'
            'Version=not-the-simulator-version\n',encoding='utf8')
        (self.repo / 'scripts').mkdir()
        (self.repo / 'scripts' / '02_run_analysis.py').write_text('annual_unshaded_analysis.csv')

    def test_step18_does_not_export_native_verbatim_by_default(self):
        m = load_local('18_annual_preflight_and_pvsyst_inventory.py')
        m.ROOT = self.repo
        out = self.base / 'private_18'
        m.main(out)
        self.assertFalse((out/'18_pvsyst_project_evidence.csv').exists())
        report = (out/'18_annual_preflight_report.md').read_text(encoding='utf8')
        self.assertIn('HISTORICAL sampled-power',report)
        self.assertIn('NOT exported',report)
        self.assertNotIn('C:\\Users\\someone', report)
        with (out/'18_approved_raw_reference_targets.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows),3)
        self.assertAlmostEqual(float(rows[0]['IDA_RMSE_W']),249.5025044)
        self.assertTrue((out/'18_pvsyst_project_manifest.csv').exists())
        with self.assertRaises(FileExistsError):
            m.main(out)

    def test_step18_verbatim_requires_explicit_opt_in(self):
        m=load_local('18_annual_preflight_and_pvsyst_inventory.py')
        m.ROOT=self.repo
        out=self.base/'private_evidence'
        m.main(out, include_verbatim_evidence=True)
        self.assertTrue((out/'18_pvsyst_project_evidence.csv').exists())
        self.assertIn('PRIVATE REVIEW ONLY',(out/'18_annual_preflight_report.md').read_text())

    def test_step19_omits_native_version_without_guessing(self):
        m=load_local('19_pvsyst_full_variant_provenance.py')
        m.ROOT=self.repo
        m.ANNUAL=self.annual
        m.SHADED=self.shaded
        out=self.base/'private_19'
        m.run(out)
        for fname in ('19_pvsyst_variant_matrix.csv','19_pvsyst_meteo_matrix.csv','19_pvsyst_module_matrix.csv'):
            with (out/fname).open(newline='', encoding='utf8') as f:
                data=list(csv.DictReader(f))
                self.assertNotIn('Version',data[0].keys())
        self.assertNotIn('C:\\Users\\someone',(out/'19_pvsyst_meteo_matrix.csv').read_text())
        self.assertIn('Version` tokens are OMITTED',(out/'19_pvsyst_linkage_summary.md').read_text())
        with self.assertRaises(FileExistsError):
            m.run(out)

    def test_both_scripts_refuse_to_write_in_repository(self):
        a=load_local('18_annual_preflight_and_pvsyst_inventory.py');a.ROOT=self.repo
        b=load_local('19_pvsyst_full_variant_provenance.py');b.ROOT=self.repo;b.ANNUAL=self.annual;b.SHADED=self.shaded
        with self.assertRaises(ValueError):
            a.main(self.repo/'results'/'annual_audit')
        with self.assertRaises(ValueError):
            b.run(self.repo/'results'/'annual_audit')
        self.assertFalse((self.repo/'results').exists())

    def test_source_files_import_without_pandas_or_simulator(self):
        self.assertTrue(callable(load_local('18_annual_preflight_and_pvsyst_inventory.py').main))
        self.assertTrue(callable(load_local('19_pvsyst_full_variant_provenance.py').run))

if __name__=='__main__':
    unittest.main()
