# Single case

Invoke the entry point directly with a CMR2, CMC, light-element choice, and
liquidus equation:

```bash
mkdir -p results   # required once; nothing creates it for you
pie p CMR2 CMC light_element liquidus_eq [chi_Si_icb]
```

For the Margot et al. constraints (CMR2 = 0.346, CMC = 0.424), S light
element, Edmund liquidus:

```bash
pie p 0.346 0.424 S Edmund
# or, equivalently:
python -m pie p 0.346 0.424 S Edmund
```

`chi_Si_icb` (Si wt% at the inner-core boundary) is only needed for the
`S+Si` two-light-element case.

Each run writes, per light-element setting, `pMetaData_<chi_Si>.csv` and
`solverLog_<chi_Si>.jsonl` (Newton iterations including step lengths and
rejected trials, failure context), plus one `Data*_R<ricb>.h5` profile
file per **converged** radius. See the README's "Outputs and error codes"
section for the full `error_code` table.
