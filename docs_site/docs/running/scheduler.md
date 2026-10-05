# Scheduler sweep

```bash
python util/run/scheduler.py CMR2 CMC
```

Run from the repo root -- `scheduler.py` is an operational script, not
part of the installed `pie` package, so it is invoked by path like this,
not via `-m` (board item 28b).

`scheduler.py` loops over:

- composition: S, Si, S+Si
- liquidus equation: Steinbruegge, Edmund
- for S+Si specifically: Si wt% from 0% to 15% in 1% increments

Internally it invokes `python -m pie p CMR2 CMC light_element liquidus_eq
[chi_Si_icb]` once per composition -- the same entry point described in
[Single case](single-case.md).
