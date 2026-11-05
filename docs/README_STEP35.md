# Install and verify Step 35 in the PyCharm project

This package was built from the uploaded 5 November 2026 local sky-bin audit. It contains **only new Step 35 paths**, so it does not overwrite existing untracked Steps 18–34, historical results or any simulator/source inputs.

**How to use it:** remain on branch `audit/local-analysis-integration-20261105`, extract the ZIP **into the repository root**, then run the commands below in PowerShell:

```powershell
# Inspect what the extracted package added (all paths should be 35_* or a Step35 README/test).
git status --short scripts/35* tests/test_35* results/revision2/35* docs/README_STEP35.md results/revision2/README_STEP35.md

# Recompute the CSVs, figure formats and manifest from YOUR repository's actual source files.
python scripts/35_rebuild_revision2_sky_bins.py

# Independently verify committed/input-derived numeric statistics without changing files.
python scripts/35_rebuild_revision2_sky_bins.py --check-only
python -m unittest discover -s tests -p "test_35*.py" -v
```

**Important:** the downloadable package contains numerically checked candidate CSVs/images constructed from the *supplied Step 31 hourly audit output*. Its **manifest is intentionally not included**, because a correct release manifest must contain **SHA-256 hashes from your actual tracked Step 28/canonical inputs**. Running the generator once creates that correct `35_Figure3_manifest.json` automatically. The source-matched `--check-only` validation must pass before publication.

If a source-hash or numeric check fails, **do not change your source files or hide the mismatch**. Capture the full error and compare the generator's source expectations with the local repository checkout. Neither the prior 31/34 outputs nor the recorded Step 28 source data should be overwritten to make it pass.

## Clean staging (only after all checks pass)

```powershell
git add scripts/35_rebuild_revision2_sky_bins.py tests/test_35_revision2_sky_bins.py .github/workflows/revision2-sky-bin-checks.yml

git add docs/README_STEP35.md results/revision2/README_STEP35.md

git add results/revision2/35_*

git diff --cached --stat
# Review the list before committing; never use git add . for this repo.
```

The package includes an independent GitHub Actions check that regenerates each numerical table from the tracked Step 28 and legacy geometry sources, reruns the unit tests, and uploads a figure/manifest preview artifact when a pull request is opened. The PR should **not** be merged if these checks fail.

The package deliberately does **not** include untracked native PVsyst project files or `18_*` evidence that may contain private paths. Keep the old Step 31 and Step 34 scripts for historical documentation. The new Step 35 is an explicitly versioned successor, not a rewrite of old research history.

Commit only on your audit branch. Once reviewed, push that branch and open a PR to `main`. The branch should not be merged until the source-derived checks pass in a clean clone and the article/reviewer reply agrees with the figure method and manuscript clock qualification.

**Manuscript caution:** the 365-day physical period contains 364 distinct dates with matched selected AC observations. 31 December 2020 is missing due to the existing common model's truncated 8,736-hour timeline. December monthly results are based on an incomplete matched cohort and must be labelled accordingly. The original input's 10-minute RISE observations should not be assumed absent on the missing date.
