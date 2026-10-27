"""Standard-library sanity tests; run: python -m unittest discover -s tests -p 'test_17_integrate_C9_shading_clock.py'"""
import importlib.util
import math
import tempfile
import unittest
from datetime import datetime,date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1]/"scripts"/"17_integrate_C9_shading_clock.py"
spec = importlib.util.spec_from_file_location("c9integration", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class C9Tests(unittest.TestCase):
    def test_hour_ending_00_belongs_previous_day(self):
        self.assertEqual(mod.operating_day(datetime(2023,6,15,0)),date(2023,6,14))
        self.assertEqual(mod.operating_day(datetime(2023,6,15,1)),date(2023,6,15))
    def test_lag_pattern(self):
        self.assertEqual([mod.lag_hours(date(2023,6,d)) for d in range(10,20)],
                         [0,0,2,2,2,1,1,1,1,1])
    def test_no_unknown_model_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"C.prn"
            p.write_text("# time order produced_p\n1.0 1 100\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"inverter_o"):
                mod.read_original_inverter(p)
    def test_hourly_source_duplicate_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"C.prn"
            p.write_text("# time order inverter_o\n1.0 1 100\n1.0 1 200\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"Duplicate"):
                mod.read_original_inverter(p)
    def test_lag_fit_uses_measured_only(self):
        from datetime import timedelta
        base=datetime(2023,6,12,1)
        rows={}
        for i in range(16):
            t=base+timedelta(hours=i)
            # C's real-time curve appears 2h ahead in recorded measurement index
            rows[("B",t)]={"P_measured_W":str(350 + 50*(i-7)**2)}
            rows[("C",t)]={"P_measured_W":str(0.65*(350 + 50*(i+2-7)**2))}
        res=mod.scale_fit_lag(rows,[base+timedelta(hours=i) for i in range(13)],2)
        self.assertAlmostEqual(res["scale"],0.65,places=6)
        self.assertLess(res["RMSE_W"],1e-8)
    def test_stats_simulated_minus_measured(self):
        r=[{"timestamp":"2023-06-01 12:00:00","GTI_measured_Wm2":"100","P_measured_W":"100","P_IDA_W":"120"},
           {"timestamp":"2023-06-01 13:00:00","GTI_measured_Wm2":"100","P_measured_W":"100","P_IDA_W":"100"}]
        d=mod.metrics(r,"P_IDA_W","P_measured_W")
        self.assertAlmostEqual(d["RMSE_W"],math.sqrt(200))
        self.assertAlmostEqual(d["bias_percent"],10)

if __name__=="__main__":
    unittest.main()
