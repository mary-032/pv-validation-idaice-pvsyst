"""Step 26: read-only annual AC comparison using native IDA ICE hourly Table exports.

Inputs, in --input-dir (default results/annual_audit if present, else script directory):
    23_annual_AC_channel_comparison_hourly.csv  (Step 23 audited measured/reference cohort)
    26_IDA_hourly_mean_normalized.csv            (read-only normalized Excel Table exports)
Outputs written to --output-dir (default input-dir):
    26_annual_AC_all_systems_hourly.csv
    26_annual_AC_all_systems_metrics.csv
    26_annual_AC_all_systems_CET_CEST.csv
    26_annual_AC_all_systems_paired_CI30d.csv
    26_annual_AC_source_QC.csv

No annual, input, or shading file is overwritten. Uses only Python standard library and NumPy.
Clock hypotheses are declared by Step 23, not selected by minimizing errors.
The reconstructed RISE measured row is the interval [t,t+1) and Step 23's
model_lookup_synthetic_time identifies its interval START h. An IDA Table
value at elapsed model hour h+1 describes the preceding interval (h,h+1].
"""
import argparse
import csv
import datetime as dt
import math
from pathlib import Path
from collections import defaultdict
import numpy as np

INPUT_23 = '23_annual_AC_channel_comparison_hourly.csv'
INPUT_TABLE = '26_IDA_hourly_mean_normalized.csv'
N_BOOT, DAYS, BLOCK_DAYS, SEED = 5000, 365, 30, 20261027
SCENARIOS = ('civil_unshifted', 'fixed_CET_hypothesis')
SYSTEMS = ('A','B','C')
START = dt.datetime(2021,1,1)
REAL_START = dt.date(2020,6,1)


def read_csv(p):
    with p.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_csv(p, rows):
    if not rows:
        raise ValueError(f'No rows for {p}')
    with p.open('w',newline='',encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)


def point_stats(m, sim):
    e=sim-m
    n=len(m)
    rmse=float(np.sqrt(np.mean(e**2)))
    sst=float(np.sum((m-np.mean(m))**2))
    return dict(n=n, measured_kWh=float(sum(m)/1000), simulated_kWh=float(sum(sim)/1000),
                RMSE_W=rmse, MAE_W=float(np.mean(np.abs(e))), MBE_W=float(np.mean(e)),
                CVRMSE_pct=100*rmse/float(np.mean(m)),
                energy_bias_pct=100*float(sum(e))/float(sum(m)),
                R2=float(1-np.sum(e**2)/sst) if sst>0 else float('nan'))


def bootstrap_weights():
    rng=np.random.default_rng(SEED)
    W=np.zeros((N_BOOT,DAYS),dtype='uint16')
    offsets=np.arange(BLOCK_DAYS)
    for b in range(N_BOOT):
        starts=rng.integers(0,DAYS,size=math.ceil(DAYS/BLOCK_DAYS))
        indices=((starts[:,None]+offsets[None,:])%DAYS).ravel()[:DAYS]
        W[b]=np.bincount(indices,minlength=DAYS)
    return W


def holm_adjusted(pvals):
    n=len(pvals)
    order=sorted(range(n),key=lambda i:pvals[i])
    out=[None]*n; highest=0.
    for rank,i in enumerate(order):
        highest=max(highest,(n-rank)*pvals[i])
        out[i]=min(1.0,highest)
    return out


def run(input_dir, output_dir):
    expected=read_csv(input_dir/INPUT_23)
    trows=read_csv(input_dir/INPUT_TABLE)
    sources={}
    metadata={}
    for r in trows:
        key=(r['system'],int(r['ida_time_h']))
        if key in sources:
            raise AssertionError(f'Duplicate Table index {key}')
        sources[key]=float(r['produced_p_hourly_mean_W'])
        metadata.setdefault(r['system'],set()).add((r['source_xlsx'],r['source_sha256']))
        if abs(float(r['used_power_hourly_mean_W']))>1.e-8:
            raise AssertionError(f'Unexpected used power {key}')
        if abs(float(r['grid_power_hourly_mean_W'])+sources[key])>1.e-6:
            raise AssertionError(f'Production/grid mismatch {key}')
    for s in SYSTEMS:
        hours=sorted(h for sys,h in sources if sys==s)
        assert hours==list(range(1,8737)), f'{s}: irregular Table index'
        assert len(metadata[s])==1, f'{s}: mixed Excel sources'

    blocks=defaultdict(list)
    for row in expected:
        k=(row['system'],row['scenario'])
        assert k[0] in SYSTEMS and k[1] in SCENARIOS
        ml=dt.datetime.fromisoformat(row['model_lookup_synthetic_time'])
        elapsed=(ml-START).total_seconds()/3600
        assert abs(elapsed-round(elapsed))<1e-6, f'Non-hour index: {row}'
        h=int(round(elapsed))
        item=dict(row)
        item['ida_time_h_table_end']=h+1
        item['IDA_hourly_table_end_aligned_W']=sources.get((k[0],h+1),float('nan'))
        item['IDA_hourly_table_same_index_W']=sources.get((k[0],h),float('nan'))
        assert math.isfinite(item['IDA_hourly_table_end_aligned_W'])
        blocks[k].append(item)

    assert len(blocks)==6
    mrows=[]; seasons=[]; pair=[]; qcs=[]; all_hourly=[]
    W=bootstrap_weights()
    for s in SYSTEMS:
        for scenario in SCENARIOS:
            cohort=blocks[(s,scenario)]
            assert len(cohort)==4478, f'{s}/{scenario}: unexpected cohort length'
            assert len({r['physical_interval_start_local'] for r in cohort})==4478
            assert all(int(r['power_valid_10min'])==6 for r in cohort)
            valid_days=np.array([(dt.date.fromisoformat(r['physical_interval_start_local'][:10])-REAL_START).days for r in cohort],int)
            assert valid_days.min()>=0 and valid_days.max()<DAYS
            arrays={col:np.array([float(r[col]) for r in cohort]) for col in
                    ['P_measured_W','IDA_produced_p_W','IDA_inverter_o_W','PVsyst_EGrid_W',
                     'IDA_hourly_table_end_aligned_W','IDA_hourly_table_same_index_W']}
            assert all(np.isfinite(v).all() for v in arrays.values())
            m=arrays['P_measured_W']; pv=arrays['PVsyst_EGrid_W']; ida=arrays['IDA_hourly_table_end_aligned_W']
            labels=[('IDA ICE hourly Table, interval-end','IDA_hourly_table_end_aligned_W'),
                    ('IDA ICE sampled produced_p','IDA_produced_p_W'),
                    ('IDA ICE sampled inverter_o','IDA_inverter_o_W'),
                    ('PVsyst E_Grid','PVsyst_EGrid_W'),
                    ('IDA ICE Table wrong same-index (diagnostic)','IDA_hourly_table_same_index_W')]
            for label,col in labels:
                mrows.append(dict(system=s,scenario=scenario,output=label,**point_stats(m,arrays[col])))
            for season in ('CET','CEST'):
                mask=np.array([(r['clock_CEST']=='True') == (season=='CEST') for r in cohort])
                assert mask.sum() in (1316,3162)
                for label,col in labels[:4]:
                    seasons.append(dict(system=s,scenario=scenario,season=season,
                                        output=label,**point_stats(m[mask],arrays[col][mask])))
            nd=np.bincount(valid_days,minlength=DAYS)
            den=W@nd
            assert np.all(den>0)
            sqpv=np.bincount(valid_days,weights=(pv-m)**2,minlength=DAYS)
            boots_pv=np.sqrt((W@sqpv)/den)
            for label,col in labels[:3]:
                x=arrays[col]
                sqx=np.bincount(valid_days,weights=(x-m)**2,minlength=DAYS)
                draws=np.sqrt((W@sqx)/den)-boots_pv
                delta=float(np.sqrt(np.mean((x-m)**2))-np.sqrt(np.mean((pv-m)**2)))
                lo,hi=np.percentile(draws,[2.5,97.5])
                p=min(1.,2*min((1+(draws>=0).sum())/(N_BOOT+1), (1+(draws<=0).sum())/(N_BOOT+1)))
                pair.append(dict(system=s,scenario=scenario,IDA_channel=label,
                                 delta_RMSE_IDA_minus_PVsyst_W=delta,
                                 CI95_low_W=float(lo),CI95_high_W=float(hi),
                                 p_two_sided_unadjusted=float(p),
                                 n_days=DAYS,n_boot=N_BOOT,block_days=BLOCK_DAYS,seed=SEED))
            # Independently check the Table against adjacent *sampled* outputs
            # only where both sampled hours survive the Step23 daytime filter.
            by_h={int(r['ida_time_h_table_end'])-1:float(r['IDA_produced_p_W']) for r in cohort}
            deviations=[]
            for h,v in by_h.items():
                if h+1 in by_h:
                    deviations.append(sources[(s,h+1)]-(v+by_h[h+1])/2)
            absdev=np.abs(deviations)
            assert len(deviations)>4000 and np.max(absdev)<=0.051
            qcs.append(dict(system=s,scenario=scenario,n_reference_hours=len(cohort),
                            measured_kWh=float(m.sum()/1000),n_valid_10min_per_hour=6,
                            table_values_missing=0, source_xlsx=next(iter(metadata[s]))[0],
                            source_sha256=next(iter(metadata[s]))[1],
                            adjacent_sample_crosscheck_n=len(deviations),
                            adjacent_sample_crosscheck_MAE_W=float(absdev.mean()),
                            adjacent_sample_crosscheck_max_abs_W=float(absdev.max())))
            for r in cohort:
                all_hourly.append({k:r[k] for k in ['system','scenario','physical_interval_start_local',
                                'physical_interval_end_local','reference_synthetic_time',
                                'model_lookup_synthetic_time','clock_CEST','power_valid_10min',
                                'ida_time_h_table_end','GTI_measured_Wm2','P_measured_W',
                                'IDA_produced_p_W','IDA_inverter_o_W','IDA_hourly_table_end_aligned_W',
                                'IDA_hourly_table_same_index_W','PVsyst_EGrid_W']})
    for sc in SCENARIOS:
        indices=[i for i,r in enumerate(pair) if r['scenario']==sc and r['IDA_channel']=='IDA ICE hourly Table, interval-end']
        adj=holm_adjusted([pair[i]['p_two_sided_unadjusted'] for i in indices])
        for i,v in zip(indices,adj):pair[i]['Holm_p_power_3_systems']=v
    for r in pair:r.setdefault('Holm_p_power_3_systems','')
    write_csv(output_dir/'26_annual_AC_all_systems_hourly.csv',all_hourly)
    write_csv(output_dir/'26_annual_AC_all_systems_metrics.csv',mrows)
    write_csv(output_dir/'26_annual_AC_all_systems_CET_CEST.csv',seasons)
    write_csv(output_dir/'26_annual_AC_all_systems_paired_CI30d.csv',pair)
    write_csv(output_dir/'26_annual_AC_source_QC.csv',qcs)
    print('\nPrimary comparison (clock hypotheses are sensitivities, not authenticated):')
    for s in SYSTEMS:
        for sc in SCENARIOS:
            ida=next(x for x in mrows if x['system']==s and x['scenario']==sc and x['output']=='IDA ICE hourly Table, interval-end')
            pv=next(x for x in mrows if x['system']==s and x['scenario']==sc and x['output']=='PVsyst E_Grid')
            ci=next(x for x in pair if x['system']==s and x['scenario']==sc and x['IDA_channel']=='IDA ICE hourly Table, interval-end')
            print(s,sc,f"IDA RMSE={ida['RMSE_W']:.3f} W, PVsyst RMSE={pv['RMSE_W']:.3f} W, delta={ci['delta_RMSE_IDA_minus_PVsyst_W']:+.3f} W, 95% CI=[{ci['CI95_low_W']:+.3f},{ci['CI95_high_W']:+.3f}], p={ci['p_two_sided_unadjusted']:.6f}")
    print('\nOutputs:',output_dir)


def main():
    parser=argparse.ArgumentParser()
    local=Path(__file__).resolve().parent
    repo_data=local.parent/'results'/'annual_audit'
    default_in=repo_data if (repo_data/INPUT_23).exists() else local
    parser.add_argument('--input-dir',type=Path,default=default_in)
    parser.add_argument('--output-dir',type=Path,default=None)
    args=parser.parse_args()
    out=args.output_dir or args.input_dir
    out.mkdir(parents=True,exist_ok=True)
    run(args.input_dir,out)

if __name__=='__main__':main()
