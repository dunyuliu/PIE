# Provenance: Zenodo-published parity reference (v1.0.5 oracle)

Source paper: Dunnigan et al. (2026), "Interior Models of Mercury and
Conditions for Iron Snow Formation in a Fe-S-Si Core," JGR Planets,
131(4), e2025JE009368, doi:10.1029/2025JE009368.

Code record: Zenodo 10.5281/zenodo.16929504 ("PIE-main.zip"). Verified
byte-identical to this repo's `src/` at the commit this reference was
added in (only `src/VERSION` differs -- version metadata, not code).

Data record: Zenodo 10.5281/zenodo.16459292, file
`Plotting and Analysis Scripts.zip`
(download: https://zenodo.org/records/16459292/files/Plotting%20and%20Analysis%20Scripts.zip?download=1),
in-archive path `For Supplemental Figures/results/<case>/`.

This directory is a CURATED SLICE (≈300 KB) of that archive, not the
full ~90 MB download -- see `extract_zenodo_slice.py` to regenerate it,
or add more cases/radii from the same archive.

## Files and in-archive origin

| File in this dir | In-archive path (under "Plotting and Analysis Scripts/For Supplemental Figures/results/") |
|---|---|
| CMR2_0.346_CMC_0.426_S+Si_Edmund/pMetaData_0.01.csv | CMR2_0.346_CMC_0.426_S+Si_Edmund/pMetaData_0.01.csv |
| CMR2_0.346_CMC_0.426_S+Si_Edmund/pMetaData_0.06.csv | CMR2_0.346_CMC_0.426_S+Si_Edmund/pMetaData_0.06.csv |
| CMR2_0.346_CMC_0.426_S+Si_Edmund/DataSi%wt0.01_R0500.0.h5 | CMR2_0.346_CMC_0.426_S+Si_Edmund/DataSi%wt0.01_R0500.0.h5 |
| CMR2_0.346_CMC_0.426_S+Si_Edmund/DataSi%wt0.06_R0550.0.h5 | CMR2_0.346_CMC_0.426_S+Si_Edmund/DataSi%wt0.06_R0550.0.h5 |
| CMR2_0.333_CMC_0.443_S+Si_Edmund/DataSi%wt0.01_R0500.0.h5 | CMR2_0.333_CMC_0.443_S+Si_Edmund/DataSi%wt0.01_R0500.0.h5 |

CMR2=0.346/CMC=0.426 is the paper's Margot et al. (2012) MOI case;
CMR2=0.333/CMC=0.443 is the Genova et al. (2019) case. Both are S+Si
(the composition with no external oracle before this record was found) with light-liquidus eq. Edmund
(2022).

Note this is CMC=0.426/0.443, not the CMC=0.424 named in the original
task brief's worked example -- 0.424 has no published S+Si oracle at
this CMR2. `testsys/integration/test_present_day_solve.py` covers
CMR2=0.346/CMC=0.424 as a self-consistency check (converges, recovers
its own target CMR2/CMC, physically sane); this directory's
CMR2=0.346/CMC=0.426 cases are the ones with a PUBLISHED regression
anchor -- see `test_zenodo_parity.py`. The published run used the same
v1.0.5 code, so this proves reproducibility, not independent correctness.

## SHA-256 (of the files as committed here)

```
82dcd05d4917ebeb819d383f8409943c38c010c83fe0761e9f830ae584ae06bf  CMR2_0.333_CMC_0.443_S+Si_Edmund/DataSi%wt0.01_R0500.0.h5
35805fce04881e00067896e958b23984a82cd579f2f1970f8be238b4a2fce138  CMR2_0.346_CMC_0.426_S+Si_Edmund/DataSi%wt0.01_R0500.0.h5
f5229e97669488450964b11112a60a43d58e0982cbed642c25125205f5c59cc0  CMR2_0.346_CMC_0.426_S+Si_Edmund/DataSi%wt0.06_R0550.0.h5
09075e179f791b07da9487ccd44a53b1cbec279891edcbdcd8e1ec7a2db0902b  CMR2_0.346_CMC_0.426_S+Si_Edmund/pMetaData_0.01.csv
9fb38fb5861f30d0b1d2349eca81aa9774525d42fa7c313f7f88a7e8571044a5  CMR2_0.346_CMC_0.426_S+Si_Edmund/pMetaData_0.06.csv
```

## Regeneration / extending the slice

```
python3 testsys/reference/zenodo_v1.0.5/extract_zenodo_slice.py --help
```

Reference data is read-only once committed (do not hand-edit these
files to make a test pass -- regenerate from the archive instead, and
say so in the commit message per the project's reference-data rule).
