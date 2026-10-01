# v1.3.3 performance: opt-in vectorised GK21 quadrature in `coreEos.Gibbs`

Canonical case: CMR2=0.346, CMC=0.424, light='S', liquidus='Edmund' (the
Margot fit), same as `docs/notes/perf_v1.3.2.md`. Timings on this box
(dliu, shared), pinned venv (`numpy==1.21.5`, `scipy==1.8.0`).

## Profile finding

`eosAndersonGrueneisen.Gibbs` (`src/coreEos.py`) calls
`scipy.integrate.quad(lambda x: self.volume(x,T), a, b)` once per Newton
iterate. Profiling (cProfile, single-radius solve, canonical case) found
this at ~6.4 s of a 9.6 s solve: 26124 calls / 548604 total integrand
evaluations = exactly 21 evals/call, i.e. QUADPACK's QAGSE never
subdivides past its first 21-point Gauss-Kronrod (GK21) panel for any
`(p, T)` pair actually reached in a real solve. Verified across the full
S/Si/S+Si x Edmund/Steinbruegge x small-ricb/canonical-ricb matrix
(237057 real captured `quad` calls, all `infodict['last']==1`; near-rcmb
radii don't converge at this CMR2/CMC for any composition -- a
pre-existing solver-boundary issue, unrelated to `quad`). See
`testsys/reference/perf_v1.3.3/README.md`.

This single-panel property is NOT universal: a direct sweep of
`eos.Gibbs`/`quad` over the full admissible pressure domain (up to
`pMax=200` GPa, vs ~39 GPa reached by any real Mercury-core solve) shows
QAGSE DOES subdivide (`last` in {2, 3}) once the integration interval
gets wide enough
(`testsys/unit/test_perf_v1_3_3_gk21_quad.py::test_direct_sweep_shows_single_panel_is_not_universal`).

## The port, and why it is opt-in rather than default

`coreEos._gk21_panel` evaluates QUADPACK's `dqk21.f` 21-point
Gauss-Kronrod rule (+ its embedded 10-point Gauss error estimate),
vectorised: `func` is called once on all 21 abscissae instead of 21
scalar Python calls. `coreEos._gk21_or_quad` replicates `dqagse.f`'s own
single-panel accept test and falls back to the real
`scipy.integrate.quad` per call whenever that test fails -- a per-call
runtime check, not a one-time global switch, which is why the
not-universal sweep above matters: the fallback is load-bearing.

A first attempt shipped this as the DEFAULT path, justified by a
differential test showing max diff 0.0 against real `scipy.integrate.quad`
on 237057 real captured solver states -- on the pinned environment. That
broke CI's `fast-latest` job (pins-stripped, current numpy/scipy, Python
3.12) with an ~8.3e-17 difference. Root cause:
`eosAndersonGrueneisen.volume(x, T)` -- which internally calls
`self.poly.__call__(p)`, a `scipy.interpolate.CubicSpline` -- does not
return exactly the same values when called with an array `x`
(vectorised, what `_gk21_panel` relies on) as when called once per scalar
point (what real `scipy.integrate.quad` does internally), on scipy/numpy
versions newer than the pin. This is floating-point non-associativity in
`CubicSpline`'s own vectorized-vs-scalar code path (SIMD/BLAS dispatch),
not a bug in the GK21 port's node/weight tables or accept-test
replication, and it is genuinely environment-dependent (the same commit
passed `fast-latest` on one CI runner invocation and failed it on
another, almost certainly different GitHub Actions runner CPU
microarchitecture -- the same class of ULP-level cross-machine
nondeterminism already documented in
`testsys/integration/test_v1_2_0_invariant.py`'s `_same()`/`_on_pinned_env()`
docstring).

Ruling: GK21 ships **opt-in** (`PIE_FAST_QUAD=1`, default `0`/unset), not
the default. Default behaviour is the unconditional
`scipy.integrate.quad` call, unchanged on every environment.

## Differential test results

- Pinned environment (`numpy==1.21.5`, `scipy==1.8.0`): max abs diff
  **0.0** (exact equality, not a tolerance) over 4000 (eos, real-call)
  pairs (2 eos objects x 2000 sampled real calls) --
  `TestGK21MatchesRealQuadBitIdentically::test_max_diff_is_exactly_zero_on_real_sample`.
- Portable tier (same assertion run as if off the pinned environment,
  bound checked explicitly rather than assumed): max relative diff
  measured **0.0**, bound enforced at **<=1e-14**. On this pinned
  environment the measured value happens to also be exactly 0 because
  the pinned tier's exact-equality branch is what actually ran; the
  portable bound is the one that governs on `fast-latest` and any other
  non-pinned environment, where a nonzero (but <=1e-14) relative
  difference is expected from the `CubicSpline` dispatch difference above.

## Timing (pinned environment, this box)

Per `quad`/`gk21` call (2000 real captured `(a, b, T)` calls, `fccFe`
eos object):

| path | total (2000 calls) | per call |
|---|---|---|
| `scipy.integrate.quad` (default) | 0.340 s | 170.1 us |
| `coreEos._gk21_or_quad` (opt-in) | 0.080 s | 40.1 us |

Speedup: **4.24x** per call.

Per-radius (26124 real `quad` calls/radius, from the profiling count
above): quad ~= 26124 x 170.1 us = 4.44 s; gk21 ~= 26124 x 40.1 us =
1.05 s -- consistent with the ~6.4 s of 9.6 s originally profiled share
(this run's absolute quad time differs somewhat from the original
profiling run; both were taken on a shared, loaded box). A full
multi-radius sweep (`docs/notes/perf_v1.3.2.md`'s ~40-radius canonical
sweep) scales this per-radius saving roughly linearly with the number of
radii that reach the Newton solve's `Gibbs` call.

## 2026-10-01 update: test-fix (unconditional array-vs-scalar assertion) + fast-latest reproduction

**Bug found and fixed in this branch, before merge.** Reviewing the PR #15/#16
history, `testsys/unit/test_perf_v1_3_3_gk21_quad.py`'s
`TestVolumeVectorisesExactly::test_array_call_matches_elementwise_scalar_calls`
still had an UNCONDITIONAL `assert np.array_equal(vec, scalar)` -- exactly the
assertion that failed on CI run 36881055265's `fast-latest` job
("AssertionError: fccFe: volume(array) != elementwise volume(scalar)"), while
the sibling class below it (`TestGK21MatchesRealQuadBitIdentically`) already
had the correct `_on_pinned_env()` exact/portable split. Fixed at
`testsys/unit/test_perf_v1_3_3_gk21_quad.py:117-166`
(`TestVolumeVectorisesExactly.test_array_call_matches_elementwise_scalar_calls`):
now exact `np.array_equal` only on the pinned environment; off it, bounded by
the existing `GK21_PORTABLE_RTOL = 1e-14` (reused, not reinvented -- same root
cause, `CubicSpline` array-vs-scalar non-associativity in
`eosAndersonGrueneisen.volume`, that the constant was already calibrated
against).

### Why reuse `GK21_PORTABLE_RTOL` instead of measuring a fresh bound

Measured on THIS host (numpy 2.2.6, scipy 1.15.3, the box's default
`/usr/bin/python3` interpreter) the array-call-vs-elementwise-scalar-call
divergence for `eosAndersonGrueneisen.volume` over the real captured sample
(100 (eos, call) pairs x 21 points, `rng.default_rng(42)`, same sample as
`TestVolumeVectorisesExactly`) is **exactly 0.0** (max abs diff and max rel
diff both 0.0) -- `volume` values are O(1) (sample: `[1.18235321, 1.15976657,
1.13938154, ...]`), so this is not a units/scale artifact. This reproduces
what the module docstring already documents: the divergence is **CPU/SIMD-
dependent floating-point nondeterminism across ephemeral runners**, not
something guaranteed to reproduce on every host or every run -- CI run
36879868704 (PR-head, green) and 36881055265 (merge-SHA, red) resolved
IDENTICAL package versions (numpy==2.5.3, scipy==1.18.1, pandas==3.0.6) via
`gh run view <id> --log`, so this is not a pip-resolution difference. Since a
0.0 measurement on one host does not bound what a *different* CPU/SIMD runner
will produce, the right fix is not "tighten to 0 since that's what I
measured" (that would just reintroduce the brittle unconditional assert under
a different name) -- it is to bound it by the SAME `GK21_PORTABLE_RTOL =
1e-14` already in the file, which has ~1e5x headroom above the one concrete
failure magnitude on record (~8.3e-17 absolute / O(1) values => ~8.3e-17
relative, from CI run 36881055265).

### Reproducing the `fast-latest` CI step locally

```
sed -E 's/==[^ ]+//' testsys/requirements.txt | grep -v '^#' > /tmp/req-latest.txt
virtualenv -p /usr/bin/python3 venv-fast-latest
./venv-fast-latest/bin/pip install -q -r /tmp/req-latest.txt
```

Resolved on this host (`/usr/bin/python3`, Python 3.10.12 -- the CI job pins
Python 3.12, so exact resolved versions differ by Python-version availability
windows on PyPI, but the key finding -- IDENTICAL numpy/scipy across the two
real CI runs above -- is a CI-side fact, not something this local
reproduction needs to re-derive):

| package | resolved here | CI (36879868704 / 36881055265, both runs) |
|---|---|---|
| numpy | 2.2.6 | 2.5.3 |
| scipy | 1.15.3 | 1.18.1 |
| pandas | 2.3.3 (py3.10 ceiling) | 3.0.6 |

`python3 -m pytest testsys/unit/test_perf_v1_3_3_gk21_quad.py -v` in this venv:
**10 passed** (all tiers, including the now-fixed
`test_array_call_matches_elementwise_scalar_calls`, which on this host's
resolved numpy/scipy takes the pinned-env-equivalent `np.array_equal` path's
measured value of 0.0 but is gated by the portable `<=1e-14` bound, not
exact-equality, since `_on_pinned_env()` correctly reports False here).

`python3 testsys/run.py unit contract integration` in this venv: **221
passed, 15 skipped, 3 xfailed, 0 failed** (175.89s). (`e2e` intentionally
excluded from this reproduction per the task scope; see the pinned-environment
`testsys/run.py all` run below for the full gate including `e2e`.)

### Full gate, pinned environment (fresh venv, numpy==1.21.5/scipy==1.8.0/pandas==1.3.5, matching `testsys/requirements.txt` exactly)

`testsys/run.py all`: **264 passed, 14 skipped, 3 xfailed, 0 failed**
(927.51s / 15m27s, `-n 4` xdist).

## How to opt in

```
PIE_FAST_QUAD=1 PYTHONNOUSERSITE=1 MPLBACKEND=Agg python scheduler.py 0.346 0.424
```

See README.md's "Performance options" section for the accuracy caveat.
