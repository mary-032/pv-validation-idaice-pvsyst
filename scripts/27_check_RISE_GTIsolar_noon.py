"""Independent RISE GTI / astronomical solar-noon sanity check.

Reads the Step 23 *measured* GTI series, not modelled PV power.
The test is descriptive; daily weighted GTI centroid is not an exact solar-noon
measurement, and cannot replace original logger timestamp documentation.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
# When running inside the user's project scripts directory:
REPO = ROOT.parent if ROOT.name == "scripts" else ROOT
SOURCE = REPO / "results" / "annual_audit" / "23_annual_AC_channel_comparison_hourly.csv"
# During this source audit, allow the mounted copy at /mnt/data.
if not SOURCE.exists():
    SOURCE = ROOT / "23_annual_AC_channel_comparison_hourly.csv"
OUT = (REPO / "results" / "annual_audit") if (REPO / "results").exists() else ROOT
OUT.mkdir(parents=True, exist_ok=True)

LAT = 57.719231  # informative, not used in the approximate noon formula
LON = 12.884806  # east-positive longitude in degrees
SEED = 20261028

raw = pd.read_csv(SOURCE, parse_dates=["physical_interval_start_local"])
d = raw.loc[(raw.system == "B") & (raw.scenario == "civil_unshifted")].copy()
assert len(d) == 4478, f"Unexpected selected daylight cohort: {len(d)}"
assert (d.power_valid_10min == 6).all(), "Unexpected measurement completeness"
d["date"] = d.physical_interval_start_local.dt.normalize()
d["hour_midpoint"] = d.physical_interval_start_local.dt.hour + 0.5
d["gti"] = pd.to_numeric(d.GTI_measured_Wm2, errors="coerce").clip(lower=0)
d["weighted_hour"] = d.hour_midpoint * d.gti

daily = d.groupby("date").agg(gti_Whm2=("gti", "sum"), weighted_hour=("weighted_hour", "sum"), is_CEST=("clock_CEST", "max"), n_hour=("gti", "size"))
daily = daily[daily.gti_Whm2 > 0].copy()
daily["gti_centroid_local_hour"] = daily.weighted_hour / daily.gti_Whm2

# NOAA approximation for equation-of-time at nominal clock noon, with
# leap-year-aware fractional year. Clock comparison resolves ~1 h, not minutes.
nday = daily.index.day_of_year.to_numpy()
ndays_in_year = np.where(daily.index.is_leap_year, 366, 365)
gamma = 2 * np.pi * (nday - 1) / ndays_in_year
eot_minutes = 229.18 * (
    0.000075 + 0.001868 * np.cos(gamma) - 0.032077 * np.sin(gamma)
    - 0.014615 * np.cos(2 * gamma) - 0.040849 * np.sin(2 * gamma)
)
# Clock hours in CET/CEST; solar noon is 12:00 clock time minus time offset.
daily["expected_solar_noon_civil_hour"] = 12 + (60 * (1 + daily.is_CEST.astype(int)) - 4 * LON - eot_minutes) / 60
daily["expected_solar_noon_fixed_CET_hour"] = 12 + (60 - 4 * LON - eot_minutes) / 60
daily["centroid_minus_civil_solar_noon_h"] = daily.gti_centroid_local_hour - daily.expected_solar_noon_civil_hour
daily["centroid_minus_fixed_CET_solar_noon_h"] = daily.gti_centroid_local_hour - daily.expected_solar_noon_fixed_CET_hour

daily.reset_index().to_csv(OUT / "27_RISE_GTIsolar_noon_daily.csv", index=False, float_format="%.9f")

rng = np.random.default_rng(SEED)
rows = []
for season, mask in [("CET", ~daily.is_CEST), ("CEST", daily.is_CEST)]:
    a = daily.loc[mask]
    residual = a.centroid_minus_civil_solar_noon_h.to_numpy()
    boot = rng.choice(residual, size=(5000, len(residual)), replace=True).mean(axis=1)
    rows.append({
        "season": season, "n_days_with_positive_GTI": len(a),
        "mean_observed_GTI_centroid_local_h": a.gti_centroid_local_hour.mean(),
        "mean_expected_noon_civil_h": a.expected_solar_noon_civil_hour.mean(),
        "mean_expected_noon_fixed_CET_h": a.expected_solar_noon_fixed_CET_hour.mean(),
        "mean_observed_minus_noon_civil_h": residual.mean(),
        "mean_observed_minus_noon_civil_CI95_low_h": np.percentile(boot, 2.5),
        "mean_observed_minus_noon_civil_CI95_high_h": np.percentile(boot, 97.5),
        "mean_observed_minus_noon_fixed_CET_h": a.centroid_minus_fixed_CET_solar_noon_h.mean(),
    })
summary = pd.DataFrame(rows)
summary.to_csv(OUT / "27_RISE_GTIsolar_noon_summary.csv", index=False, float_format="%.9f")
print(summary.round(4).to_string(index=False))
print("Outputs:", OUT)
