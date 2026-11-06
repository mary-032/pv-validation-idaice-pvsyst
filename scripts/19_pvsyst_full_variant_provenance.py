"""Read-only PVsyst variant/meteorological-file provenance audit.

Run from the repository root with a fresh private output directory:
    python scripts/19_pvsyst_full_variant_provenance.py --output-dir <outside_repo>

Reads *complete* local PVsyst .PRJ/.VC*/.MET/.PAN files, but exports only
whitelisted metadata fields. Source basenames and variant comment
excerpts may still require human privacy and distribution-rights review.
A native Version field is NOT authenticated software-version evidence and is
not exported. No simulation or canonical data is edited.

Outputs under the explicitly specified private --output-dir:
    19_pvsyst_variant_matrix.csv
    19_pvsyst_meteo_matrix.csv
    19_pvsyst_module_matrix.csv
    19_pvsyst_linkage_summary.md
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANNUAL = ROOT / "simulation_models" / "annual" / "PVsyst"
SHADED = ROOT / "simulation_models" / "shaded" / "PVsyst"
DEST = ROOT / "results" / "annual_audit"

# Retain only these explicitly approved metadata keys. Never export arbitrary
# PVsyst key=value text; some keys hold Windows account/OneDrive paths.
METEO_FILENAME = re.compile(r"(?i)^.+\.MET$")
VC_SUFFIX = re.compile(r"\.VC[0-9]+$", re.IGNORECASE)
ASSOCIATION = re.compile(r"(?i)(\.MET|\.PAN|\.OND)$")
NUMERIC = re.compile(r"^-?(?:\d+(?:\.\d*)?|\.\d+)$")
LEAK = re.compile(r"(?i)([a-z]:\\|/Users/|/home/|OneDrive|\\Users\\)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fd:
        for piece in iter(lambda: fd.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def read_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding).splitlines()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode PVsyst file: {path.name}")


def first_value(lines: list[str], key: str) -> str:
    prefix = key.casefold() + "="
    for line in lines:
        clean = line.strip()
        if clean.casefold().startswith(prefix):
            return clean.partition("=")[2].strip()
    return ""


def only_filename(value: str) -> str:
    # Windows paths may be embedded in .MET and .VC files on Linux or Windows.
    # Returning only the basename prevents leaks from NomFSource, including
    # personal folder names and affiliation-specific directory trees.
    return re.split(r"[/\\]", value.strip())[-1]


def safe_token(value: str, kind: str = "text") -> str:
    value = value.strip()
    if kind == "filename":
        value = only_filename(value)
        # Refuse any path or suspicious unresolved long text.
        if not re.fullmatch(r"[\w\-. ()åäöÅÄÖ]+", value, flags=re.UNICODE):
            return "[redacted]"
    elif kind == "numeric":
        if value and not NUMERIC.fullmatch(value):
            return "[unexpected]"
    elif kind == "comment":
        # Descriptive variant comments are useful but some may be private.
        # Do not export comments; keep only a simple system label derived
        # from standardized 'system 3/8/9' references below.
        return "[redacted]" if value else ""
    if LEAK.search(value):
        return "[redacted]"
    return value[:140]


def choose_weather(lines: list[str]) -> str:
    vals = []
    for line in lines:
        line = line.strip()
        if line.casefold().startswith(("nomf=", "meteofilename=")):
            v = line.partition("=")[2].strip()
            if METEO_FILENAME.search(v):
                vals.append(safe_token(v, "filename"))
    # Some files redundantly embed the meteo object; retain first reference
    return vals[0] if vals else ""


def source_system(lines: list[str]) -> str:
    # Only standardized explicit system phrases are used, never free-text
    # Comments or user-specific strings in output.
    opening = "\n".join(lines[:20]).casefold()
    m = re.search(r"\bsystem\s*([389])\b", opening)
    return m.group(1) if m else "unverified"


def orientation(lines: list[str]) -> str:
    for line in lines[:350]:
        s = line.strip()
        if "Fixed," in s and "Tilt" in s:
            # e.g. Comment=Fixed, Tilt 45.0°, Azim. 0.0°
            out = s.partition("=")[2].strip()
            if re.fullmatch(r"Fixed, Tilt\s*-?\d+(?:\.\d+)?[^,]{0,3},\s*Azim\.\s*-?\d+(?:\.\d+)?[^,]{0,3}",out):
                return out
            return "fixed orientation; detailed values unverified"
    return ""


def site_meta(lines: list[str]) -> dict[str, str]:
    fields = ("Latitude", "Longitude", "Altitude", "TimeZone", "Albedo")
    return {k: safe_token(first_value(lines, k), "numeric") for k in fields}


def extract_references(lines: list[str]) -> dict[str, str]:
    # Bounded list of embedded *filenames*, not original absolute paths.
    refs = set()
    for line in lines:
        if "=" not in line or len(line) > 300:
            continue
        k,v = line.split("=",1)
        if len(k) > 70:
            continue
        v = v.strip()
        if ASSOCIATION.search(v):
            v = safe_token(v, "filename")
            if v != "[redacted]":
                refs.add(v)
    pans = sorted(x for x in refs if x.upper().endswith(".PAN"))
    onds = sorted(x for x in refs if x.upper().endswith(".OND"))
    return {"PAN_refs": "; ".join(pans[:15]), "OND_refs": "; ".join(onds[:15])}


def put_csv(path: Path, rows: list[dict], fields: list[str]):
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def validate_output_privacy(paths: list[Path]):
    for path in paths:
        content=path.read_text(encoding="utf-8")
        if LEAK.search(content):
            path.unlink(missing_ok=True)
            raise RuntimeError(f"Private source path suspected in {path.name}; output removed")


def run(output_dir: Path):
    # Never regenerate the original local historical CSVs in-place: Step 36
    # fingerprinted them and re-export would silently change that source set.
    global DEST
    DEST = Path(output_dir).expanduser().resolve()
    if DEST.is_relative_to(ROOT.resolve()):
        raise ValueError('Private Step 19 outputs must be outside the Git working repository; use a fresh --output-dir')
    target_names = ['19_pvsyst_variant_matrix.csv', '19_pvsyst_meteo_matrix.csv',
                    '19_pvsyst_module_matrix.csv', '19_pvsyst_linkage_summary.md']
    existing = [name for name in target_names if (DEST / name).exists()]
    if existing:
        raise FileExistsError(f'Refusing to overwrite existing audit outputs: {existing}')
    if not ANNUAL.is_dir():
        raise FileNotFoundError(f"Missing local PVsyst folder: {ANNUAL}")
    variants=sorted(x for x in ANNUAL.iterdir() if x.is_file() and VC_SUFFIX.search(x.suffix))
    project_files=sorted(x for x in ANNUAL.iterdir() if x.is_file() and x.suffix.upper()==".PRJ")
    met_files=sorted(x for folder in (ANNUAL,SHADED) if folder.is_dir() for x in folder.iterdir() if x.is_file() and x.suffix.upper()==".MET")
    pans=sorted(x for x in ANNUAL.iterdir() if x.is_file() and x.suffix.upper()==".PAN")
    if not variants or not met_files:
        raise ValueError("PVsyst variants or meteorological files not found")
    DEST.mkdir(parents=True,exist_ok=True)
    all_mets={p.name.casefold():p for p in met_files}

    vrows=[]
    for p in [*project_files,*variants]:
        lines=read_lines(p)
        weather=choose_weather(lines)
        meta=site_meta(lines)
        refs=extract_references(lines)
        vrows.append({"file":p.name,"file_type":p.suffix.upper(),"sha256":sha256(p),
           "declared_system":source_system(lines),"weather_file":weather,
           "weather_file_exists":bool(weather and weather.casefold() in all_mets),
           "orientation_comment":orientation(lines),
           **meta,**refs})

    mrows=[]
    for p in met_files:
        lines=read_lines(p)
        meta=site_meta(lines)
        count=""
        for line in lines[:200]:
            match=re.search(r"VarMeteo,\s*list\s+of\s*=\s*(\d+)\s+TVarSimul",line,re.I)
            if match: count=match.group(1);break
        source_name=safe_token(first_value(lines,"NomFSource"),"filename")
        mrows.append({"file":p.name,"subfolder":p.parent.name,
           "sha256":sha256(p),"source_weather_basename":source_name,
           "weather_variable_count":count,**meta})

    prows=[]
    for p in pans:
        lines=read_lines(p)
        prows.append({"file":p.name,"sha256":sha256(p)})

    vfields=["file","file_type","sha256","declared_system","weather_file","weather_file_exists",
             "orientation_comment","Latitude","Longitude","Altitude","TimeZone","Albedo","PAN_refs","OND_refs"]
    mfields=["file","subfolder","sha256","source_weather_basename","weather_variable_count",
             "Latitude","Longitude","Altitude","TimeZone","Albedo"]
    pfields=["file","sha256"]
    vp=DEST/"19_pvsyst_variant_matrix.csv"
    mp=DEST/"19_pvsyst_meteo_matrix.csv"
    pp=DEST/"19_pvsyst_module_matrix.csv"
    put_csv(vp,vrows,vfields);put_csv(mp,mrows,mfields);put_csv(pp,prows,pfields)
    report=["# PVsyst project-file provenance (read-only)","",
        "The following associations are embedded in local project/variant files. They DO NOT independently prove that a given archived hourly Excel export was generated from a particular variant.","",
        "## Variants and project active setting", "",
        "| Variant/project | Explicit system ID | Weather file | File found | Orientation metadata |",
        "|---|---|---|---|---|"]
    for r in vrows:
        report.append(f"| `{r['file']}` | {r['declared_system']} | `{r['weather_file']}` | {'Yes' if r['weather_file_exists'] else 'No'} | {r['orientation_comment'] or 'Not extracted'} |")
    report += ["","## Key cautions","",
       "- SiteSimul metadata can still say Meteonorm when the selected variant's NomF references a separately imported weather file.",
       "- A .PRJ project's selected weather file is a saved project setting, not a historical per-export run log.",
       "- The original .MET files and their SHA-256 fingerprints are available in the meteorological matrix.",
       "- Native `Version` tokens are OMITTED, because their semantics and software-version identity were not verified; earlier exports showed `[unexpected]`.",
       "- Meteorological-file existence does not establish or fix any suspected one-hour alignment anomaly.",
       "- PVsyst site configuration should be reported as its own model input rather than silently replaced by the separate analytical solar-geometry coordinates.",
       "- Do not commit raw .PRJ/.VC/.MET files publicly without first checking operator names, absolute source paths, and release permissions.",
       "- This script does not read spreadsheet exports, derive annual power metrics, or modify weather data.","",
       "## Outputs","",
       "- `19_pvsyst_variant_matrix.csv`","- `19_pvsyst_meteo_matrix.csv`",
       "- `19_pvsyst_module_matrix.csv`","- `19_pvsyst_linkage_summary.md`",""]
    rp=DEST/"19_pvsyst_linkage_summary.md"
    rp.write_text("\n".join(report),encoding="utf-8")
    validate_output_privacy([vp,mp,pp,rp])
    print(f"PASS: {len(variants)} variants, {len(project_files)} project records, {len(met_files)} .MET inputs, {len(pans)} .PAN files")
    print("PASS: exports are whitelisted and do not contain private source paths")
    print("Output directory:",DEST)
    for f in (vp,mp,pp,rp):print(" -",f.name)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Fresh, private output folder (never the historical source folder)")
    run(parser.parse_args().output_dir)
