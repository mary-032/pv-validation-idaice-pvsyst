# Step 37 — source-provenance script maintenance (historical Steps 18 and 19)

**5 November 2026. Local source-maintenance change; no change to Step 28/29/35 scientific results.**

## Rationale

Step 36 (now merged) preserved aggregate-only historical provenance with exact source hashes. Two earlier, **untracked** analysis scripts remained misleading and potentially unsafe to rerun:

1. `18_annual_preflight_and_pvsyst_inventory.py` labelled the old sampled-IDA power RMSE comparisons as approved. Those October 2026 targets are historical and are *not* the hourly Table source selected for Revision 2 Step 28.
2. `19_pvsyst_full_variant_provenance.py` interpreted each PVsyst native `Version` token as a pure number. The supplied historical 19-series CSVs showed `[unexpected]` in all 16 entries. Without native format/run evidence, the correct treatment is to **omit** the field, rather than silently assign an inferred PVsyst software build.

These replacement scripts preserve the historical output basename `18_approved_raw_reference_targets.csv` for source traceability but mark it as **historical sampled-power verification targets** in every report heading and code description. Historical target numbers and formulae are unchanged. The original, already-generated local 18/19 CSV files remain the immutable input snapshots documented by Step 36.

## Run safety (new)

Both scripts now **require** `--output-dir` and refuse any directory inside the repository. They also refuse to overwrite existing output filenames. Step 18's `18_pvsyst_project_evidence.csv`, which contains third-party verbatim excerpts, is not generated unless `--include-verbatim-evidence` is explicitly passed; that flag should only be used in a private location. No native PVsyst files are copied or modified. Step 19 produces the same filename set, without `Version` columns. The output metadata and source hashes remain source *claims*, not independently authenticated historical run lineage.

### Recommended local commands

Create independent private output folders (PowerShell):

```powershell
$runRoot = Join-Path $env:TEMP ("pv-source-metadata-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
& .\.venv313\Scripts\python.exe scripts/18_annual_preflight_and_pvsyst_inventory.py --output-dir (Join-Path $runRoot "step18")
& .\.venv313\Scripts\python.exe scripts/19_pvsyst_full_variant_provenance.py --output-dir (Join-Path $runRoot "step19")
```

Outputs in `%TEMP%` are **private working evidence**; do not stage them or paste verbatim excerpts into public GitHub. The scripts do not regenerate Step 36 curated sources and are intentionally not used as an input to the current working annual analysis.

### Automated tests

```powershell
& .\.venv313\Scripts\python.exe -m unittest discover -s tests -p "test_37*.py" -v
```

The tests use isolated, synthetic PVsyst file fixtures (not real source files), covering: historical label; exact preserved old target RMSE; verbatim-evidence opt-in; no native version claims; rejection of Git-repository destinations; and overwrite protection. They do not verify third-party redistribution rights or establish clock truth.

## Repository integration

Stage **only** the two corrected Python scripts, this documentation, the Step 37 tests, and the Step 37 GitHub Actions workflow. Do **not** stage legacy `18_*`/`19_*` CSV outputs, raw RISE data, or native PVsyst `.PRJ/.VC/.MET/.PAN/.GIM` files. Commit on a new branch created from merged `main`; preserve original local scripts outside the working tree before copying these replacements over them.

**Next:** the earlier Steps 30–34 figure/sky-bin development trail should be filed as historical method evidence, with Steps 29 and 35 as the current reproducible sources, and references to absent Step 33 removed or marked unavailable. This archival step is separate from this code-maintenance PR.
