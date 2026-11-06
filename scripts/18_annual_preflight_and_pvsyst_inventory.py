"""Local source inventory for the *historical sampled-channel* annual AC audit.

Run from the repository root with a fresh private output directory:
    python scripts/18_annual_preflight_and_pvsyst_inventory.py --output-dir <outside_repo>

The output location MUST be outside the Git repository and contain no existing
output files; historical audit CSVs are never overwritten. Native PVsyst
verbatim excerpts are NOT written unless --include-verbatim-evidence is set,
and are private/release-restricted. The fixed target numbers are historical
sampled-IDA power metrics, not the Step 28 hourly-Table reference.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'results' / 'annual_audit'

# Extract only bounded context from supported PVsyst input formats.
PVSYST_SUFFIXES = {'.PRJ', '.MET', '.PAN', '.OND', '.GIM', '.SIT', '.CSV', '.TXT'}
PVSYST_VC = re.compile(r'^\.VC\d+$', re.IGNORECASE)
KEYWORD = re.compile(
    r'(?i)(meteo|weather|climate|site|latitude|longitude|altitude|\bproject\b|'
    r'\bvariant\b|orientation|\btilt\b|azimuth|horizon|shade|shading|'
    r'near\s*shad|pole|array|\bmodule\b|inverter|optimizer|'
    r'\bpan\b|\.met\b|\.ond\b|\.pan\b|time\s*zone|utc|'
    r'\bdate\b|\byear\b|albedo|\bversion\b|\.vc\d\b)'
)
# HISTORICAL sampled-channel model results from the 27 Oct 2026 audit.
# Not the current Step 28 hourly Table power estimates (no new calculation).
BASELINE = [
    ('A', 4478, 3648.540780, 249.5025044, 252.4630830, -2.9605786, -11.26089097, 8.923914587, -1.328224908, -6.256988593),
    ('B', 4478, 4230.834711, 335.1115271, 311.4655027, 23.6460244, 15.83974386, 32.4975778, 3.665712537, -0.3001277994),
    ('C', 4478, 2809.807941, 263.3929704, 244.9995602, 18.3934102, 12.65777747, 23.66147348, 6.860322583, 10.43512456),
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_csv(path: Path, fields: list[str], data: list[dict]) -> None:
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(data)


def preview_text(path: Path) -> str:
    # Limit amount read to prevent high memory usage for e.g. annual .MET files.
    with path.open('rb') as f:
        sample = f.read(96_000)
    nul_frac = sample.count(b'\x00') / max(1, len(sample))
    if nul_frac > 0.15:
        for enc in ('utf-16-le', 'utf-16-be'):
            try:
                return sample.decode(enc)
            except UnicodeError:
                continue
        return ''
    for enc in ('utf-8-sig', 'cp1252'):
        try:
            return sample.decode(enc)
        except UnicodeError:
            continue
    return ''


def git_tracked(path: Path) -> str:
    try:
        r = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '--error-unmatch', '--', rel(path)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=6, check=False)
        return 'yes' if r.returncode == 0 else 'no'
    except (OSError, subprocess.TimeoutExpired):
        return 'unknown'


def main(output_dir: Path, include_verbatim_evidence: bool = False) -> None:
    global OUTPUT
    OUTPUT = Path(output_dir).expanduser().resolve()
    # Never write into this Git checkout: private native metadata or source
    # excerpts must not accidentally be staged as public research artifacts.
    if OUTPUT.is_relative_to(ROOT.resolve()):
        raise ValueError('Private Step 18 outputs must be outside the Git working repository; use a fresh --output-dir')
    target_names = [
        '18_annual_input_inventory.csv', '18_approved_raw_reference_targets.csv',
        '18_pvsyst_project_manifest.csv', '18_annual_script_consumers.csv',
        '18_annual_preflight_report.md',
    ]
    if include_verbatim_evidence:
        target_names.append('18_pvsyst_project_evidence.csv')
    existing = [name for name in target_names if (OUTPUT / name).exists()]
    if existing:
        raise FileExistsError(f'Refusing to overwrite existing audit outputs: {existing}')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    expected = [
        ('raw_10min_measurements', ROOT/'data/measured/annual/RISE_raw10min_389.xlsx'),
        ('historical_processed_measurements', ROOT/'data/historical/Results_PVsyst_E2_hour.xlsx'),
        ('legacy_annual_canonical', ROOT/'derived_data/annual_unshaded_analysis.csv'),
        ('historical_raw_builder_01b', ROOT/'scripts/01b_rebuild_raw_reference.py'),
        ('raw_reference_canonical', ROOT/'derived_data/annual_raw_reference.csv'),
        ('raw_reference_metric_table', ROOT/'results/raw_reference/01b_model_power_metrics.csv'),
        ('raw_reference_provenance', ROOT/'docs/RAW_REFERENCE_RECONSTRUCTION.md'),
        ('legacy_uncertainty_script', ROOT/'scripts/05_statistical_uncertainty.py'),
        ('annual_master_results_script', ROOT/'scripts/04_build_master_results.py'),
    ]
    for s in '389':  # System A/3, B/8 and C/9 (original RISE IDs).
        sysid = s
        expected.append((f'IDA_PD_System_{sysid}', ROOT/f'data/ida_ice/annual/Perez_Driesse/Syst{sysid}_PD.xlsx'))
        expected.append((f'PVsyst_PD_System_{sysid}', ROOT/f'data/pvsyst/annual/Perez_Driesse/PVsyst_{sysid}_PD_h.xlsx'))

    input_records = []
    for key, path in expected:
        input_records.append({'role': key, 'path': rel(path), 'exists': path.is_file(),
                              'size_bytes': path.stat().st_size if path.is_file() else '',
                              'sha256': sha256(path) if path.is_file() and path.stat().st_size < 12_000_000 else ''})
    write_csv(OUTPUT/'18_annual_input_inventory.csv', list(input_records[0]), input_records)

    baseline_fields = ['system', 'daylight_hours', 'measured_energy_kWh', 'IDA_RMSE_W', 'PVsyst_RMSE_W',
                       'IDA_minus_PVsyst_RMSE_W', 'CI95_low_W', 'CI95_high_W', 'IDA_nMBE_percent', 'PVsyst_nMBE_percent']
    write_csv(OUTPUT/'18_approved_raw_reference_targets.csv', baseline_fields,
              [dict(zip(baseline_fields, row)) for row in BASELINE])

    locations = [ROOT/'simulation_models/annual/PVsyst', ROOT/'simulation_models/shaded/PVsyst']
    manifest, evidence = [], []
    for folder in locations:
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob('*')):
            if not path.is_file():
                continue
            suf = path.suffix.upper()
            if suf not in PVSYST_SUFFIXES and not PVSYST_VC.match(suf):
                continue
            text = preview_text(path)
            lines = text.splitlines()
            nonblank = [x for x in lines if x.strip()]
            matchlines = [(i, line.strip()) for i, line in enumerate(lines, 1)
                          if KEYWORD.search(line) and line.strip()]
            manifest.append({'scope': rel(folder), 'file': rel(path), 'extension': suf,
                             'size_bytes': path.stat().st_size, 'sha256': sha256(path),
                             'git_tracked': git_tracked(path), 'readable_text': bool(nonblank),
                             'keyword_matches_in_first_96kB': len(matchlines)})
            # Skip dense tabular data: only a limited selection of metadata/header lines.
            # Include evidence per file in its actual file order; no inferred meaning.
            for lineno, line in matchlines[:30]:
                evidence.append({'file': rel(path), 'line_number_in_preview': lineno,
                                 'verbatim_excerpt': line[:320]})
    write_csv(OUTPUT/'18_pvsyst_project_manifest.csv',
              ['scope', 'file', 'extension', 'size_bytes', 'sha256', 'git_tracked', 'readable_text', 'keyword_matches_in_first_96kB'], manifest)
    if include_verbatim_evidence:
        write_csv(OUTPUT/'18_pvsyst_project_evidence.csv',
                  ['file', 'line_number_in_preview', 'verbatim_excerpt'], evidence)

    annual_uses_legacy = []
    for fname in ('01_build_canonical_data.py', '02_run_analysis.py',
                  '04_build_master_results.py', '05_statistical_uncertainty.py',
                  '06_build_tables4_6_uncertainty.py', '08_combined_measurement_temporal_uncertainty.py',
                  '09_temporal_aggregation_sensitivity.py'):
        path = ROOT/'scripts'/fname
        if path.is_file():
            contents = path.read_text(encoding='utf-8-sig')
            annual_uses_legacy.append({'script': rel(path),
                'references_historical_canonical': 'annual_unshaded_analysis.csv' in contents,
                'references_raw_reference_canonical': 'annual_raw_reference.csv' in contents})
    write_csv(OUTPUT/'18_annual_script_consumers.csv',
              ['script', 'references_historical_canonical', 'references_raw_reference_canonical'], annual_uses_legacy)

    report = [
        '# HISTORICAL sampled-power source preflight (not the Revision 2 reference)', '',
        'Generated (UTC): '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ'), '',
        'This inventory preserves the 27 October 2026 sampled-channel diagnostic; it is not a new performance calculation.',
        'Step 28 uses IDA ICE hourly Table power and supersedes the sampled-IDA metrics shown below.',
        'Step 29 contains monthly summaries and Step 35 contains Figure 3 statistics.',
        'Do not interpret these verification targets as current approved manuscript results.', '',
        '## Input state', ''
    ]
    for row in input_records:
        report.append(f"- {'FOUND' if row['exists'] else 'MISSING'} — `{row['path']}` ({row['role']})")
    report += ['', '## Historical sampled-IDA power targets from the 27 October audit (superseded)', '',
               '|System|Daylight h|Measured kWh|IDA RMSE W|PVsyst RMSE W|IDA − PVsyst RMSE W|95% 30-day CI W|',
               '|---|---:|---:|---:|---:|---:|---|']
    for s,n,m,ida,pv,delta,lo,hi,*rest in BASELINE:
        report.append(f'|{s}|{n:,}|{m:.3f}|{ida:.2f}|{pv:.2f}|{delta:+.2f}|[{lo:.2f}, {hi:.2f}]|')
    report += ['', '## Inspectable PVsyst local files', '',
               f'- Found {len(manifest)} project/weather/device/metadata files in annual and shaded simulation folders.',
               f'- Of these, {sum(x["git_tracked"]=="no" for x in manifest)} are not currently tracked by Git.',
               '- File names and metadata snippets are **evidence only**, not validated settings or proof of which run generated the exported results.',
               ('- Verbatim PVsyst excerpts exported for PRIVATE REVIEW ONLY; never commit without rights/PII screening.'
                if include_verbatim_evidence else '- Verbatim native PVsyst evidence NOT exported (privacy default).'), '',
               '## Annual consumers requiring controlled migration', '']
    for x in annual_uses_legacy:
        report.append(f"- `{x['script']}`: legacy={x['references_historical_canonical']}; raw={x['references_raw_reference_canonical']}")
    report += ['', '## Historical limits and current release gates', '',
        '1. This was a historical raw-reference investigation; its 01b_* paths are not required to validate the later Step 28/29/35 outputs.',
        '2. The primary paired cohort and the two clock interpretations are described in docs/REVISION2_RESULT_MAP.md.',
        '3. Original logger time semantics, model/export linkage and underlying rights remain unverified; no metric here authenticates them.',
        '4. Do not publish raw excerpts or project files, or replace prior source reports, without review.', '',
        '## Output files', '',
        '- `18_annual_input_inventory.csv`',
        '- `18_approved_raw_reference_targets.csv`',
        '- `18_pvsyst_project_manifest.csv`',
        ('- `18_pvsyst_project_evidence.csv` (private opt-in)'
         if include_verbatim_evidence else '- `18_pvsyst_project_evidence.csv` NOT generated'),
        '- `18_annual_script_consumers.csv`',
        '- `18_annual_preflight_report.md`', ''
    ]
    (OUTPUT/'18_annual_preflight_report.md').write_text('\n'.join(report), encoding='utf-8')
    print('PASS: read-only annual/PVsyst inventory complete')
    print('PVsyst local inventory items:', len(manifest))
    print('Historical raw builder present:', (ROOT/'scripts/01b_rebuild_raw_reference.py').is_file())
    print('Output:', OUTPUT)
    for n in target_names:
        print(' -', n)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True, help='Fresh private result directory; historical results/annual_audit is protected')
    parser.add_argument('--include-verbatim-evidence', action='store_true', help='Explicit private opt-in for third-party native file excerpts')
    args = parser.parse_args()
    main(args.output_dir, args.include_verbatim_evidence)
