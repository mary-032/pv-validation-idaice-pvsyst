"""Read-only paired annual AC-power comparison of native IDA output channels.

Uses the Step 20 measurement reconstruction with the explicit Step 21
CET/CEST model time lookup. Compares both annual IDA ICE power channels
(`produced_p`, `inverter_o`) and PVsyst `E_Grid` on IDENTICAL measured hours.

IMPORTANT: This is a *diagnostic*, not an approved primary analysis or a
proof that the reconstructed clock assumptions are the only possible ones.

Input scripts 20 and native annual IDA PRNs are read, never edited.
Output ONLY to results/annual_audit/23_*. Existing annual/shading frozen
outputs are never overwritten.

Run from PyCharm project root (Python 3.13 environment):
  .\\.venv313\\Scripts\\python.exe .\\scripts\\23_annual_AC_power_channel_sensitivity.py
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'annual_audit'
STEP20_PATH = ROOT / 'scripts' / '20_rebuild_raw_annual_AC_diagnostic.py'
RAW = ROOT / 'data' / 'measured' / 'annual' / 'RISE_raw10min_389.xlsx'
SIM0 = pd.Timestamp('2021-01-01 00:00:00')
SYSTEMS = {
    'A': ('System_A_3', 'Syst3_PD_20260907'),
    'B': ('System_B_8', 'Syst8_PD_20260907'),
    'C': ('System_C_9', 'Syst9_PD_20260907'),
}
# Never auto-select a model time offset based on the computed RMSE.
SCENARIOS = {
    'civil_unshifted': (0, 0),
    'fixed_CET_hypothesis': (0, -1),
}
EXPECTED_N = 4478
EXPECTED_MEASURED = {'A': 3648.540780436822, 'B': 4230.834711114277,
                     'C': 2809.8079413981186}
PREVIOUS_IDA_PRODUCED_RMSE = {'A': 249.50, 'B': 335.11, 'C': 263.39}
PREVIOUS_PVSYST_RMSE = {'A': 252.46, 'B': 311.47, 'C': 245.00}
N_BOOT = 5000
BLOCK_DAYS = 30
SEED = 20261027


def load_module(path: Path, module_name: str):
    if not path.is_file():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def read_prn_channels(path: Path, channel: str) -> pd.DataFrame:
    """Select by header name, never by column order or inferred units."""
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open('r', encoding='utf-8-sig', errors='replace') as f:
        header = f.readline().lstrip('#').split()
    if not {'time', 'order', channel}.issubset(header):
        raise ValueError(f'{path}: expected time/order/{channel}; got {header}')
    d = pd.read_csv(path, sep=r'\s+', skiprows=1, header=None,
                    names=header, engine='c')
    for c in ('time', channel):
        d[c] = pd.to_numeric(d[c], errors='raise')
    time = d['time'].to_numpy(float)
    if not np.isfinite(time).all() or not np.allclose(time, np.round(time), rtol=0, atol=1e-5):
        raise ValueError(f'Invalid native IDA simulation hour in {path}')
    if not np.isfinite(d[channel].to_numpy(float)).all():
        raise ValueError(f'Nonfinite {channel}: {path}')
    d['ida_time_h'] = np.rint(time).astype(int)
    if d['ida_time_h'].duplicated().any():
        raise ValueError(f'Duplicate original IDA hour in {path}')
    out = d[['ida_time_h', channel]].copy()
    return out


def measured_reference(step20, workbook, system, cfg):
    """Recreate exactly the Step 21 reference, with interval labels explicit."""
    raw = step20.load_raw(system, workbook)
    h = step20.to_hourly(raw, 'sample_start')
    # The Step 20 group key is the PHYSICAL INTERVAL END. Step 21 then
    # subtracts one hour, yielding the physical START, not hour-ending.
    h = h.rename(columns={'physical_timestamp':'physical_interval_end_local',
                          'timestamp':'synthetic_interval_end'})
    h['physical_interval_start_local'] = h['physical_interval_end_local'] - pd.Timedelta(hours=1)
    h['reference_synthetic_time'] = h['synthetic_interval_end'] - pd.Timedelta(hours=1)
    # Earlier cohort selection used solar elevation at this reference time,
    # i.e. the interval START. Do not relabel it "hour ending".
    sky_start = step20.solar_masks(h['physical_interval_start_local'], cfg)
    sky_end = step20.solar_masks(h['physical_interval_end_local'], cfg)
    h['reference_sun_above_horizon_at_interval_start'] = sky_start['astronomical_day_hour_end']
    h['sun_above_horizon_at_interval_midpoint'] = sky_end['astronomical_day_hour_midpoint']
    h['sun_above_horizon_at_interval_end'] = sky_end['astronomical_day_hour_end']
    # Keep exactly the domain in the previous Step21 calculation:
    # reference time also had to exist in the common IDA/PVsyst model axis.
    h = h[['physical_interval_start_local','physical_interval_end_local',
           'reference_synthetic_time','P_measured_W','GTI_measured_Wm2',
           'sample_count','power_valid_10min','reference_sun_above_horizon_at_interval_start',
           'sun_above_horizon_at_interval_midpoint','sun_above_horizon_at_interval_end']].copy()
    return h


def dst_mask(times: pd.DatetimeIndex, zone: str) -> np.ndarray:
    z = times.tz_localize(zone, ambiguous=False, nonexistent='shift_forward')
    offsets = np.array([t.utcoffset().total_seconds()/3600 for t in z])
    if not np.isin(offsets, [1,2]).all():
        raise ValueError(f'Unexpected {zone} UTC offsets: {np.unique(offsets)}')
    return offsets == 2


def metrics(measured: np.ndarray, simulated: np.ndarray) -> dict:
    if measured.shape != simulated.shape or not len(measured):
        raise ValueError('Empty or unmatched comparison')
    if not (np.isfinite(measured).all() and np.isfinite(simulated).all()):
        raise ValueError('Comparison would have nonfinite values; fail closed')
    e = simulated - measured
    total = float(measured.sum())
    return {
        'n': len(measured),
        'measured_kWh': total/1000.0,
        'simulated_kWh': float(simulated.sum()/1000.0),
        'RMSE_W': float(np.sqrt(np.mean(e**2))),
        'MAE_W': float(np.mean(np.abs(e))),
        'MBE_W': float(np.mean(e)),
        'CVRMSE_pct': float(100*np.sqrt(np.mean(e**2))/np.mean(measured)),
        'energy_bias_pct': float(100*e.sum()/total),
    }


def block_indices(n_days: int, n_boot=N_BOOT, block_days=BLOCK_DAYS, seed=SEED):
    """Circular moving-block bootstrap on consecutive LOCAL observation dates."""
    if n_days < 1 or block_days < 1:
        raise ValueError('Bad bootstrap shape')
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n_days/block_days)
    weights = np.zeros((n_boot,n_days), np.uint16)
    off = np.arange(block_days)
    for k in range(n_boot):
        starts = rng.integers(0,n_days,size=n_blocks)
        drawn = ((starts[:,None] + off[None,:])%n_days).ravel()[:n_days]
        weights[k] = np.bincount(drawn,minlength=n_days)
    return weights


def paired_channel_CIs(d: pd.DataFrame, channels: tuple[str,...], pv_col='PVsyst_EGrid_W'):
    start_days = pd.DatetimeIndex(pd.to_datetime(d['physical_interval_start_local']))
    days = pd.date_range('2020-06-01','2021-05-31',freq='D')
    indices = days.get_indexer(start_days.normalize())
    if (indices<0).any():
        raise ValueError('Reference interval starts outside physical study year')
    W = block_indices(len(days))
    counts = np.bincount(indices,minlength=len(days)).astype(float)
    sample_counts = W@counts
    if not np.all(sample_counts>0):
        raise ValueError('Bootstrap resampled zero daylight hours')
    measured = d['P_measured_W'].to_numpy(float)
    pv = d[pv_col].to_numpy(float)
    pv_daily = np.bincount(indices,weights=(pv-measured)**2,minlength=len(days))
    pv_rmse = np.sqrt((W@pv_daily)/sample_counts)
    output=[]
    for channel in channels:
        ida=d[channel].to_numpy(float)
        ida_daily=np.bincount(indices,weights=(ida-measured)**2,minlength=len(days))
        ida_rmse=np.sqrt((W@ida_daily)/sample_counts)
        delta=ida_rmse-pv_rmse
        observed=float(np.sqrt(np.mean((ida-measured)**2))-np.sqrt(np.mean((pv-measured)**2)))
        lo,hi=np.percentile(delta,[2.5,97.5])
        # two-sided sign-based bootstrap diagnostic; avoid zero p-values
        p=2*min((1+np.sum(delta>=0))/(1+len(delta)),(1+np.sum(delta<=0))/(1+len(delta)))
        output.append({'IDA_channel':channel,'paired_delta_RMSE_IDA_minus_PVsyst_W':observed,
                       'CI95_low_W':float(lo),'CI95_high_W':float(hi),
                       'bootstrap_two_sided_p_unadjusted':float(min(1,p)),
                       'block_days':BLOCK_DAYS,'n_boot':N_BOOT,'n_days':len(days)})
    return output


def main():
    for p in (RAW, STEP20_PATH, ROOT/'config.json'):
        if not p.is_file():
            raise FileNotFoundError(p)
    step20=load_module(STEP20_PATH,'step20_reused_for_annual_channel_audit_23')
    cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    tz=cfg['site']['timezone']
    OUT.mkdir(parents=True,exist_ok=True)
    metrics_rows=[]
    ci_rows=[]
    all_hourly=[]
    verified=[]
    mask_rows=[]
    with pd.ExcelFile(RAW) as book:
        for system in 'ABC':
            ref=measured_reference(step20,book,system,cfg)
            model=step20.read_models(system)
            # Reproduce Step21's *exact* common model-axis cohort.
            common=ref.merge(model[['timestamp']],left_on='reference_synthetic_time',
                             right_on='timestamp',how='inner',validate='one_to_one')
            # The previously approved numerical target used sunrise/sunset as
            # classified at the INTERVAL START. Report other defensible masks
            # explicitly instead of silently assuming they are equivalent.
            valid=common['power_valid_10min'].eq(6) & common['P_measured_W'].notna()
            start_mask=valid & common['reference_sun_above_horizon_at_interval_start']
            for label,col in [('start','reference_sun_above_horizon_at_interval_start'),
                              ('midpoint','sun_above_horizon_at_interval_midpoint'),
                              ('end','sun_above_horizon_at_interval_end')]:
                sample=common.loc[valid & common[col]]
                mask_rows.append({'system':system,'solar_elevation_at':label,
                                  'n_valid_sun_positive_hours':len(sample),
                                  'measured_kWh':sample['P_measured_W'].sum()/1000,
                                  'n_hours_not_in_start_mask':int((valid & common[col] & ~start_mask).sum()),
                                  'n_start_mask_hours_missing':int((start_mask & ~common[col]).sum())})
            eligible=common.loc[start_mask].copy()
            eligible=eligible.sort_values('reference_synthetic_time').reset_index(drop=True)
            eligible=eligible.drop(columns='timestamp')
            if eligible['P_measured_W'].isna().any():
                raise ValueError(f'{system}: partial measured AC detected')
            if len(eligible)!=EXPECTED_N:
                raise ValueError(f'{system}: expected 4478 primary reference hours, got {len(eligible)}')
            energy=eligible['P_measured_W'].sum()/1000
            if not math.isclose(energy,EXPECTED_MEASURED[system],abs_tol=0.001):
                raise ValueError(f'{system}: measured-energy mismatch {energy:.6f}')
            pathroot=ROOT/'simulation_models'/'annual'/'IDA ICE'/SYSTEMS[system][0]/SYSTEMS[system][1]/'energy'
            power=read_prn_channels(pathroot/'electrical system.EL-POWERS.prn','produced_p')
            inv=read_prn_channels(pathroot/'electrical system.EL-STRING-POWERS.prn','inverter_o')
            native=power.merge(inv,on='ida_time_h',how='inner',validate='one_to_one')
            native['timestamp']=SIM0+pd.to_timedelta(native['ida_time_h'],unit='h')
            native=native.set_index('timestamp')
            model_idx=model.set_index('timestamp')
            # Independently verify that the annual spreadsheet is produced_p.
            same= model_idx[['P_IDA_W']].join(native[['produced_p']],how='inner').dropna()
            if len(same)<8700 or np.max(np.abs(same['P_IDA_W']-same['produced_p']))>0.02:
                raise ValueError(f'{system}: annual workbook no longer matches native produced_p')
            clock=pd.DatetimeIndex(eligible['physical_interval_start_local'])
            is_dst=dst_mask(clock,tz)
            m=eligible['P_measured_W'].to_numpy(float)
            for case,(w,s) in SCENARIOS.items():
                offsets=np.where(is_dst,s,w)
                synthetic=pd.DatetimeIndex(eligible['reference_synthetic_time'])
                source_time=synthetic+pd.to_timedelta(offsets,unit='h')
                ida_out=native[['produced_p','inverter_o']].reindex(source_time)
                pv_out=model_idx[['P_PVsyst_W']].reindex(source_time)
                ch=pd.DataFrame({
                    'system':system,'scenario':case,
                    'physical_interval_start_local':eligible['physical_interval_start_local'],
                    'physical_interval_end_local':eligible['physical_interval_end_local'],
                    'reference_synthetic_time':eligible['reference_synthetic_time'],
                    'model_lookup_synthetic_time':source_time,
                    'clock_CEST':is_dst,
                    'power_valid_10min':eligible['power_valid_10min'],
                    'GTI_measured_Wm2':eligible['GTI_measured_Wm2'],
                    'P_measured_W':m,
                    'IDA_produced_p_W':ida_out['produced_p'].to_numpy(float),
                    'IDA_inverter_o_W':ida_out['inverter_o'].to_numpy(float),
                    'PVsyst_EGrid_W':pv_out['P_PVsyst_W'].to_numpy(float),
                })
                if ch[['P_measured_W','IDA_produced_p_W','IDA_inverter_o_W','PVsyst_EGrid_W']].isna().any().any():
                    raise ValueError(f'{system} {case}: missing native model values')
                ch['IDA_produced_minus_inverter_W']=ch['IDA_produced_p_W']-ch['IDA_inverter_o_W']
                all_hourly.append(ch)
                for label,col in [('IDA ICE produced_p','IDA_produced_p_W'),
                                  ('IDA ICE inverter_o','IDA_inverter_o_W'),
                                  ('PVsyst E_Grid','PVsyst_EGrid_W')]:
                    vals=metrics(m,ch[col].to_numpy(float))
                    metrics_rows.append({'system':system,'clock_scenario':case,'simulation_channel':label,**vals})
                    if case=='fixed_CET_hypothesis' and label in ('IDA ICE produced_p','PVsyst E_Grid'):
                        target=(PREVIOUS_IDA_PRODUCED_RMSE[system] if label.startswith('IDA')
                                else PREVIOUS_PVSYST_RMSE[system])
                        if abs(vals['RMSE_W']-target)>0.07:
                            raise ValueError(f'{system}: failed Step21 RMSE check: {label} '
                                             f'{vals["RMSE_W"]:.3f} vs {target:.3f}')
                for row in paired_channel_CIs(ch,('IDA_produced_p_W','IDA_inverter_o_W')):
                    ci_rows.append({'system':system,'clock_scenario':case,**row})
                verified.append({'system':system,'clock_scenario':case,
                                 'reference_n':len(ch),'measured_kWh':energy,
                                 'IDA_spread_mean_W':ch['IDA_produced_minus_inverter_W'].mean(),
                                 'IDA_spread_MAE_W':ch['IDA_produced_minus_inverter_W'].abs().mean(),
                                 'IDA_spread_sum_kWh':ch['IDA_produced_minus_inverter_W'].sum()/1000})
            print(f'{system}: PASS {len(eligible)} common solar-selected raw measured hours; '
                  f'{energy:.3f} kWh; 2 clock cases, 2 IDA channels + PVsyst')

    path=OUT/'23_annual_AC_channel_comparison_hourly.csv'
    pd.concat(all_hourly,ignore_index=True).to_csv(path,index=False)
    metrics_df=pd.DataFrame(metrics_rows)
    metrics_df.to_csv(OUT/'23_annual_AC_channel_metrics.csv',index=False)
    pd.DataFrame(ci_rows).to_csv(OUT/'23_annual_AC_channel_paired_CI30d.csv',index=False)
    pd.DataFrame(verified).to_csv(OUT/'23_annual_AC_channel_source_spread.csv',index=False)
    pd.DataFrame(mask_rows).to_csv(OUT/'23_annual_AC_daylight_boundary_sensitivity.csv',index=False)
    lines=['# Step 23 — Annual AC channel sensitivity', '',
           '**Diagnostic only.** Not a finalized or approved annual AC comparison.', '',
           'Measured input: original RISE ten-minute Power_* readings; six samples per hour.',
           'The Step20/21 source cohort is retained: start-labeled samples, a -1 h',
           'reference-label transformation, and solar elevation >0 **at the interval start**.',
           'The prior diagnostics referred to this as hour-ending daylight; after the -1 h',
           'transformation it is in fact the interval START. No sample is discarded',
           'or relabeled during this sensitivity test.', '',
           'Model clock cases: unshifted civil lookup and fixed-CET hypothesis',
           '(model time t in CET, t-1 h in CEST). Neither is chosen by RMSE.', '',
           '|System|Clock scenario|Channel|RMSE W|Bias %|',
           '|---|---|---|---:|---:|']
    for r in metrics_rows:
        lines.append(f'|{r["system"]}|{r["clock_scenario"]}|{r["simulation_channel"]}|'
                     f'{r["RMSE_W"]:.2f}|{r["energy_bias_pct"]:+.2f}|')
    lines += ['', '## Daylight-selection boundary diagnostic', '',
              '|System|Solar elevation evaluated at|Daylight h|Measured kWh|Hours entering relative to start|Hours excluded relative to start|',
              '|---|---|---:|---:|---:|---:|']
    for r in mask_rows:
        lines.append(f'|{r["system"]}|{r["solar_elevation_at"]}|{r["n_valid_sun_positive_hours"]}|'
                     f'{r["measured_kWh"]:.3f}|{r["n_hours_not_in_start_mask"]}|'
                     f'{r["n_start_mask_hours_missing"]}|')
    lines += ['', '## Conditional paired-model uncertainty (30-day circular moving blocks)', '',
              '|System|Clock|IDA channel|IDA minus PVsyst RMSE W|95% CI W|',
              '|---|---|---|---:|---|']
    for r in ci_rows:
        lines.append(f'|{r["system"]}|{r["clock_scenario"]}|{r["IDA_channel"]}|'
                     f'{r["paired_delta_RMSE_IDA_minus_PVsyst_W"]:+.2f}|'
                     f'[{r["CI95_low_W"]:+.2f}, {r["CI95_high_W"]:+.2f}]|')
    lines += ['', '## Release gate', '',
              '- Determine from IDA ICE model documentation whether `produced_p` (equal to',
              '  minus `grid_power`, with `used_power=0`) is the correct AC exported grid',
              '  quantity, or whether `inverter_o` represents the comparison boundary.',
              '- Verify input meteo fixed-CET clock semantics independently before',
              '  choosing any CEST model lookup.',
              '- Report the interval-start solar selection accurately; revise the',
              '  daylight mask if the intended scientific definition differs.',
              '- This file does not change historical annual results or the shading freeze.', '']
    (OUT/'23_annual_AC_channel_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Wrote results/annual_audit/23_annual_AC_channel_*.csv,')
    print('  23_annual_AC_daylight_boundary_sensitivity.csv, and report.md')


if __name__=='__main__':
    main()
