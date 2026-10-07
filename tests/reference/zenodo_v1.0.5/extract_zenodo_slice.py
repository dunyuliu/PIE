#!/usr/bin/env python3
"""Regenerate tests/reference/zenodo_v1.0.5/ from the published Zenodo
data archive. See PROVENANCE.md (and mc_wide/PROVENANCE.md) for the
DOIs and the exact in-archive paths this pulls.

Usage:
    # Prefers the shared, read-only, cross-project cache if present
    # (the user's convention: published datasets live once in
    # ~/shared_dataset, projects reference them, never copy wholesale):
    #     ~/shared_dataset/zenodo.16459292/extracted/
    #         "Plotting and Analysis Scripts"/...   (the small slice, ~90 MB)
    #         PIE/{work.margot,work.genova}/results/...   (the wide MC set)
    # Falls back to downloading from Zenodo directly when that path is
    # absent (e.g. CI, which has no access to another user's home
    # directory) -- only for the small "Plotting and Analysis Scripts"
    # archive; the wide MC set (`work.tar`, tens of GB) is NEVER
    # auto-downloaded, only read from the shared cache when present.

    python3 tests/reference/zenodo_v1.0.5/extract_zenodo_slice.py            # small slice
    python3 tests/reference/zenodo_v1.0.5/extract_zenodo_slice.py --mc-wide  # mc_wide/ (needs shared_dataset)

Add more (case, filename) pairs to SLICE below to extend the small-slice
reference with more radii/compositions; re-run, then update
PROVENANCE.md's file table and SHA-256 list by hand (rule: reference data
carries its provenance, not just its bytes). For mc_wide/, edit the
selection logic in this file's `_mc_wide_picks()` (mirrors
tests/reference/zenodo_v1.0.5/mc_wide/PROVENANCE.md's documented
"low/high/centre/most_converged_rows per composition x MOI" picks).
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
ARCHIVE_PREFIX = "Plotting and Analysis Scripts/For Supplemental Figures/results"
ZENODO_SMALL_SLICE_URL = (
    "https://zenodo.org/records/16459292/files/"
    "Plotting%20and%20Analysis%20Scripts.zip?download=1"
)
SHARED_DATASET_ROOT = pathlib.Path(
    "~/shared_dataset/zenodo.16459292/extracted").expanduser()

SLICE = [
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "pMetaData_0.01.csv"),
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "pMetaData_0.06.csv"),
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "DataSi%wt0.01_R0500.0.h5"),
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "DataSi%wt0.06_R0550.0.h5"),
    ("CMR2_0.333_CMC_0.443_S+Si_Edmund", "DataSi%wt0.01_R0500.0.h5"),
]

NOMINAL = {"margot": (0.346, 0.426), "genova": (0.333, 0.443)}


def _extract_small_slice():
    shared_zip = SHARED_DATASET_ROOT.parent / "Plotting and Analysis Scripts.zip"
    shared_extracted = SHARED_DATASET_ROOT / "Plotting and Analysis Scripts"
    if shared_extracted.is_dir():
        print(f"using already-extracted {shared_extracted}")
        for case, fname in SLICE:
            src = shared_extracted / "For Supplemental Figures" / "results" / case / fname
            outdir = HERE / case
            outdir.mkdir(parents=True, exist_ok=True)
            data = src.read_bytes()
            (outdir / fname).write_bytes(data)
            print(f"{hashlib.sha256(data).hexdigest()}  {case}/{fname}")
        return
    if shared_zip.is_file():
        archive = shared_zip
        print(f"using {archive}")
    else:
        archive = HERE / "Plotting and Analysis Scripts.zip"
        if not archive.is_file():
            print(f"downloading {ZENODO_SMALL_SLICE_URL} (CI path; no "
                  f"shared_dataset found at {SHARED_DATASET_ROOT})")
            urllib.request.urlretrieve(ZENODO_SMALL_SLICE_URL, archive)
    with zipfile.ZipFile(archive) as zf:
        for case, fname in SLICE:
            arcpath = f"{ARCHIVE_PREFIX}/{case}/{fname}"
            outdir = HERE / case
            outdir.mkdir(parents=True, exist_ok=True)
            outpath = outdir / fname
            data = zf.read(arcpath)
            outpath.write_bytes(data)
            print(f"{hashlib.sha256(data).hexdigest()}  {case}/{fname}")


def _mc_wide_picks():
    """Reproduces mc_wide/'s selection: for each (moi, light), pick the
    lowest-CMR2, highest-CMR2, nominal-closest, and
    most-converged-rows draws. Requires the shared_dataset (the wide MC
    set is never auto-downloaded)."""
    pie_root = SHARED_DATASET_ROOT / "PIE"
    if not pie_root.is_dir():
        raise SystemExit(
            f"{pie_root} not found -- --mc-wide requires the shared, "
            f"read-only dataset cache (the wide MC set is tens of GB and "
            f"is never auto-downloaded by this script)"
        )
    manifest = []
    for moi in ("margot", "genova"):
        base = pie_root / f"work.{moi}" / "results"
        for light in ("S", "Si", "S+Si"):
            suffix = f"_{light}_Edmund"
            info = []
            for d in base.iterdir():
                if not d.name.endswith(suffix):
                    continue
                m = re.match(r"CMR2_([\d.]+)_CMC_([\d.]+)_", d.name)
                cmr2, cmc = float(m.group(1)), float(m.group(2))
                fname = "pMetaData_0.05.csv" if light == "S+Si" else "pMetaData_0.00.csv"
                fpath = d / fname
                if not fpath.is_file():
                    continue
                n_rows = sum(1 for _ in open(fpath)) - 1
                info.append((cmr2, cmc, n_rows, d.name, fname))
            if not info:
                continue
            nom_cmr2, nom_cmc = NOMINAL[moi]
            picks = {
                "low_cmr2_extreme": min(info, key=lambda x: x[0]),
                "high_cmr2_extreme": max(info, key=lambda x: x[0]),
                "centre_nominal": min(info, key=lambda x: (x[0]-nom_cmr2)**2 + (x[1]-nom_cmc)**2),
                "most_converged_rows": max(info, key=lambda x: x[2]),
            }
            for label, (cmr2, cmc, n_rows, dname, fname) in picks.items():
                manifest.append({"moi": moi, "light": light, "label": label,
                                  "dir": dname, "fname": fname, "cmr2": cmr2,
                                  "cmc": cmc, "n_rows": n_rows})
    return manifest, pie_root


def _extract_mc_wide():
    manifest, pie_root = _mc_wide_picks()
    outdir_root = HERE / "mc_wide"
    sha_lines = []
    for entry in manifest:
        src = pie_root / f"work.{entry['moi']}" / "results" / entry["dir"] / entry["fname"]
        outdir = outdir_root / entry["moi"] / entry["dir"]
        outdir.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        (outdir / entry["fname"]).write_bytes(data)
        h = hashlib.sha256(data).hexdigest()
        entry["committed_path"] = f"{entry['moi']}/{entry['dir']}/{entry['fname']}"
        entry["sha256"] = h
        sha_lines.append(f"{h}  {entry['committed_path']}")
    (outdir_root / "manifest.json").write_text(json.dumps(manifest, indent=1))
    (outdir_root / "SHA256SUMS").write_text("\n".join(sha_lines) + "\n")
    print(f"wrote {len(manifest)} files to {outdir_root}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mc-wide", action="store_true",
                     help="regenerate mc_wide/ instead of the small slice "
                          "(requires ~/shared_dataset)")
    args = ap.parse_args()
    if args.mc_wide:
        _extract_mc_wide()
    else:
        _extract_small_slice()


if __name__ == "__main__":
    main()
