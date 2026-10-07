# Benchmarks

PIE's correctness claims split into two classes that are **not**
interchangeable (see [Model overview](model-overview.md#regression-anchored-vs-independently-verified)):

* **Regression anchors** -- parity with an older PIE version's own output
  (or the Zenodo-archived dataset from the same code family). A pass means
  "no unintended behaviour change", not "correct".
* **Truth/independent anchors** -- agreement with a value derived outside
  this code family: an analytical closed-form check (e.g. a homogeneous
  sphere's CMR2 = 0.4), the predecessor Fe-S/Fe-Si codes, or published
  liquidus/EOS data.

PIE's single-light-element cases (S-only, Si-only) have an independent
oracle in the predecessor codes. The **S+Si** case does not: beyond
self-consistency limit checks (as Si%wt or S%wt -> 0), its only external
check is the Zenodo Monte Carlo dataset from the same v1.0.5 code family --
regression-anchored, never report it as "independently verified".

## Running the checks

Fast tiers (unit, contract, integration -- CI's push/PR gate, ~3-5 min):

```
.venv/bin/python3.12 tests/run.py
```

Everything, including the full-CLI e2e test and the wide physics-coverage
sweep (~14 min):

```
.venv/bin/python3.12 tests/run.py all
```

The widest check, 240 further Monte-Carlo-drawn cases sampled directly
from the shared published dataset cache, needs a local
`~/shared_dataset/zenodo.16459292/` mount and is not run in CI:

```
python3 -m pytest tests/e2e/test_published_wide_sweep.py -m published_wide -v
```

See [`tests/README.md`](https://github.com/dunyuliu/PIE/blob/main/tests/README.md)
for the full tier breakdown and runtimes.

## What each tier actually checks

| Check | Class | What it compares against |
|---|---|---|
| Unit (EOS objects, mass/MOI integrals, Newton solver in isolation) | Truth anchor | closed-form limits (e.g. a homogeneous body's CMR2 = 0.4) |
| Contract (csv/h5 schema, CI config, repo hygiene) | n/a | structural, not physical |
| Integration: self-consistency solve at Margot CMR2/CMC | Truth anchor (self-consistency) | the solver's own convergence criteria, no external data |
| Integration: published-paper parity (3 solves, all scalars + profiles) | Regression anchor | Zenodo-archived v1.0.5 output (same code family) |
| Integration: MC-wide parity (24 curated cases) | Regression anchor | Zenodo Monte Carlo dataset (same code family) |
| Integration: v1.0.4 (2023) history (17-row diff) | Regression anchor | an earlier, untested predecessor version |
| E2E: full-CLI subprocess run | Regression anchor | a self-generated golden (no independent oracle) |
| E2E: wide sweep (36 cases, all compositions x MOI x 3 radii) | Regression anchor | a self-generated golden |
| E2E: `published_wide` (240 cases, opt-in) | Regression anchor | Zenodo Monte Carlo dataset (same code family) |

No tier in this table is an independent check of the **S+Si** physics
specifically -- every S+Si row above compares against output from the same
PIE code family. S-only and Si-only results additionally rest on agreement
with the predecessor Fe-S/Fe-Si codes (run separately, not part of this
repo's automated suite).

## Known, documented non-convergence

One of the wide-sweep's 36 cases (Margot CMR2=0.346/CMC=0.426, `Si`,
`Edmund`) does not converge from a generic cold-start initial guess at any
radius tried, 10 m through 650 km. This is tracked and gated as an expected
failure, not silently dropped -- the test asserts it keeps failing. A
scheduler sweep at Margot's own CMR2=0.346/CMC=0.424 similarly stops partway
through its radius grid (18 of ~40 steps) when the Newton solver hits a
singular Jacobian around `ricb` ~ 850 km; this means no root was found by
the Newton variants tried, not an established physical non-existence result.
