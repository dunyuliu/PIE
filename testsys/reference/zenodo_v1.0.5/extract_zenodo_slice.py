#!/usr/bin/env python3
"""Regenerate testsys/reference/zenodo_v1.0.5/ from the published Zenodo
data archive. See PROVENANCE.md for the DOIs and the exact in-archive
paths this pulls.

Usage:
    # 1. Download the archive once (large, ~90 MB -- not committed):
    curl -L -o "Plotting and Analysis Scripts.zip" \\
        "https://zenodo.org/records/16459292/files/Plotting%20and%20Analysis%20Scripts.zip?download=1"

    # 2. Extract this repo's curated slice from it:
    python3 testsys/reference/zenodo_v1.0.5/extract_zenodo_slice.py \\
        "Plotting and Analysis Scripts.zip"

Add more (case, filename) pairs to SLICE below to extend the reference
with more radii/compositions from the same archive; re-run, then update
PROVENANCE.md's file table and SHA-256 list by hand (rule: reference data
carries its provenance, not just its bytes).
"""
import argparse
import hashlib
import pathlib
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
ARCHIVE_PREFIX = "Plotting and Analysis Scripts/For Supplemental Figures/results"

SLICE = [
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "pMetaData_0.01.csv"),
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "pMetaData_0.06.csv"),
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "DataSi%wt0.01_R0500.0.h5"),
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "DataSi%wt0.06_R0550.0.h5"),
    ("CMR2_0.333_CMC_0.443_S+Si_Edmund", "DataSi%wt0.01_R0500.0.h5"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", help="path to the downloaded "
                     "'Plotting and Analysis Scripts.zip'")
    args = ap.parse_args()

    with zipfile.ZipFile(args.archive) as zf:
        for case, fname in SLICE:
            arcpath = f"{ARCHIVE_PREFIX}/{case}/{fname}"
            outdir = HERE / case
            outdir.mkdir(parents=True, exist_ok=True)
            outpath = outdir / fname
            data = zf.read(arcpath)
            outpath.write_bytes(data)
            print(f"{hashlib.sha256(data).hexdigest()}  {case}/{fname}")


if __name__ == "__main__":
    main()
