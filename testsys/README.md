# testsys/ -- PIE tiered test suite

Modelled on the test systems in this group's other projects (EQdyna,
EQdyna.2Dcycle, eqquasi), scaled down for PIE: a small, serial,
no-build, pure-Python codebase with zero prior tests.

## Environment (read this first)

Use the **system** Python, not whatever `python3` resolves to on PATH:

```
/usr/bin/python3 testsys/run.py
```

This box's `/usr/bin/python3` has two conflicting matplotlib installs
on its default `sys.path` -- apt's `python3-matplotlib` 3.5.1 under
`/usr/lib/python3/dist-packages`, and a `pip --user` matplotlib 3.9.2
under `~/.local/lib/.../site-packages`, which sorts earlier. Several
src/ modules (`visualization_present.py`, `TEST_visualization_evolution.py`,
and so transitively `driverp.py`, `shootp.py`'s callers, and `main.py`)
do `from mpl_toolkits.mplot3d import Axes3D` unconditionally; with both
installs on the path, `matplotlib` resolves to the pip one but
`mpl_toolkits` resolves to the apt one, and that pairing is broken
(apt's `mpl_toolkits.mplot3d.axes3d` imports a name matplotlib 3.9
removed). See "Findings" below -- this is a real project bug, not
fixed here.

- **In-process tests** (unit/contract/integration): `testsys/conftest.py`
  drops the `.local` entries from `sys.path` before importing anything
  from `src/`, which makes both packages resolve from the same (apt)
  install. Nothing to set manually.
- **Subprocess tests** (e2e, which run `main.py` as a real
  subprocess): need `PYTHONNOUSERSITE=1` (in the subprocess's own
  environment; `testsys/conftest.py`'s `run_pie()` helper and
  `testsys/run.py` both set it). `MPLBACKEND=Agg` avoids needing a
  display either way.

## Running

```
/usr/bin/python3 testsys/run.py                       # fast tiers (default): unit + contract + integration
/usr/bin/python3 testsys/run.py unit
/usr/bin/python3 testsys/run.py e2e                    # opt-in, ~5.5 min for one composition
/usr/bin/python3 testsys/run.py all                    # everything
```

Equivalent direct pytest invocation (what `run.py` shells out to; CI
uses this exact form -- see `.github/workflows/test.yml`):

```
PYTHONNOUSERSITE=1 MPLBACKEND=Agg /usr/bin/python3 -m pytest testsys -m "unit or contract or integration" -v
```

## Tiers

| Tier | Marker | What | Count | Runtime |
|---|---|---|---|---|
| Unit | `unit` | Pure functions: coreEos EOS objects, libCore's mass/MOI integrals, the Newton solver in isolation, planet_input/globalvar parameter sanity | 32 (+1 xfail) | ~8 s |
| Contract | `contract` | Output CSV/h5 schema vs `globalvar.presentday_columns`, CI workflow YAML validity and push/PR-excludes-e2e, README/run.py/pytest.ini tier-name parity, repo hygiene (src/ untouched), no `interp2d` in `src/` (removed in scipy 1.14; ported in v1.1.1) | 13 | ~0.5 s |
| Integration | `integration` (parity subset also marked `parity`) | One present-day solve at Margot CMR2=0.346/CMC=0.424 (self-consistency); 3 solves vs **published paper output** (regression anchor, same code) with ALL 19 scalars + full radial profiles gated; **wide fast subset**: 1 radius x 2 MOI x 6 compositions (12 cases, all scalars+profiles, incl. a documented non-convergent case); **v1.0.4 (2023) history**: 17-row field-by-field diff with 2 known, attributed deltas; **MC-wide parity**: 24 curated real Monte-Carlo-drawn (CMR2,CMC) cases (4 per composition x MOI: extremes/centre/most-converged) vs published scalars | 9+3+12+14+24 | ~19s+~57s+~52s+~0.02s+~65s |
| E2E | `e2e` | (a) `main.py p 0.346 0.424 S Edmund` end-to-end in a tmp dir via the REAL CLI subprocess (full file/figure I/O), vs a self-golden; (b) wide sweep, ALL 3 radii x 2 MOI x 6 compositions (36 cases, all scalars+profiles), direct-solve (not CLI), parallelized, CI-sharded by composition; (c) `published_wide` (marker `published_wide`, skipped when `~/shared_dataset` absent -- always in CI): 240 further Monte-Carlo-drawn cases sampled directly from the shared cache, never copied | 4 + 36 + 240 | ~4.5 min + ~54 s + ~150-200 s |

`published_wide` (since v1.3.0): a fresh failure where the published run
converged is a HARD failure whatever its signature -- the ricb = 10 m
"Factor is exactly singular" flake (Findings #5, bug B5) is fixed by the
getk2 nrs=0 index fix (board item 19 closed). A fresh convergence where the
published run had zero rows is accepted only if the recovered model passes
`conftest.assert_recovered_model_valid` (residual, chi box, ricb < rcmb,
rho > 0, finite) and is printed as "recovered".

Fast-tier total (unit+contract+integration, what CI runs on every
push/PR): **106 passed, 1 xfailed**; measured 194-307 s depending on
this shared box's other load at the time (multiple ProcessPoolExecutor-
parallelized solves compete with other users' jobs on this 64-core
machine) -- CI's own (dedicated) runner should land nearer the low end.

### Coverage breadth (2026-09-28 follow-up)

All 6 compositions (S, Si, S+Si x Edmund, Steinbruegge) are now guarded
at BOTH the fast (12-case, 1 radius) and e2e (36-case, 3 radii) levels,
at both Margot (CMR2=0.346/CMC=0.426) and Genova (CMR2=0.333/CMC=0.443)
MOI configurations -- gating ALL 19 `presentday_columns` scalars
(previously `moi`/`cmc`/`chi_li_eut_icb`/`chi_li_eut_cmb` were skipped
in the Zenodo parity test; they are the model's own FIT TARGETS and are
now gated everywhere) plus the FULL radial profile arrays (r, rho, P,
T, Tad, g, chi_li -- not just the scalar summary). See
`testsys/conftest.py`'s `solve_full_model`/`assert_scalars_match`/
`assert_profiles_match` for the shared implementation all of these
tests now use.

One of the 36 wide-sweep cases (Margot CMR2=0.346/CMC=0.426, `Si`,
`Edmund`) does NOT converge from a generic cold-start initial guess, at
every radius tried (10 m through 650 km) -- this is tracked and GATED
AS a failure mode (the test asserts it keeps failing, not that it's
absent), not silently dropped. See "Findings" below.

### Published Monte Carlo anchor (2026-09-28 second follow-up)

The full published dataset (Dunnigan et al. 2026's Monte Carlo study,
6144 result directories: 2 MOI x 1024 (CMR2,CMC) draws x {S, Si, S+Si},
liquidus Edmund only) is available locally, shared read-only across
projects, at `~/shared_dataset/zenodo.16459292/extracted/PIE/`. This
REPLACES self-golden as the primary anchor for S and Si (previously
only S+Si had a published anchor, via the smaller `zenodo_v1.0.5/`
slice): `integration/test_mc_wide_parity.py` gates 24 curated cases
(committed, run everywhere) against real MC-drawn (CMR2, CMC) pairs;
`e2e/test_published_wide_sweep.py` (marker `published_wide`) samples 240
further cases DIRECTLY from the shared cache (never copied -- skipped
with a clear reason when that path is absent, i.e. in CI). Steinbruegge
liquidus has NO published anchor in either dataset -- those compositions
stay self-golden-only (`reference/self_v1.0.5/wide_sweep/`).

This dataset has scalar metadata (`pMetaData_*.csv`) only, no `.h5`
radial profiles -- so `mc_wide`/`published_wide` gate the 19 scalars,
not profile arrays (profiles are still gated, for S+Si, by the smaller
`zenodo_v1.0.5/` slice's `test_zenodo_parity.py`).

Only ONE test (`e2e/test_full_composition_sweep.py`) goes through the
real `main.py` CLI subprocess end-to-end (file/figure I/O, argv
parsing); the wide-coverage tests call `shootp`'s Newton/shoot directly
(same physics, no I/O) to stay fast enough to run 36-48 cases per tier.
This is a deliberate scope tradeoff: breadth of PHYSICS coverage is
wide, but only one composition's CLI/file-writing PATH is exercised
end-to-end. Flagged for the human: if CLI-path bugs specific to Si/S+Si
are a concern, that needs its own (slower) subprocess-based test.

### Why e2e runs one composition, not the full scheduler.py sweep

`scheduler.py CMR2 CMC` loops 16 `chi_Si_icb` values × S+Si, plus one
run each of S and Si: 18 compositions. Measured on this box: one S,
Edmund composition at CMR2=0.346/CMC=0.424 takes **5.5 min** wall time
(18 of ~40 possible inner-core-radius steps converge before the Newton
solver hits a singular Jacobian around ricb≈850 km and the run stops --
reproduced by the golden, so not a testsys bug; per
`docs/audits/AUDIT_2026-09-29_solver-failures.md` this means "no root
found by the local Newton variants tried", NOT an established physical
limit -- non-existence would need continuation in ricb / fold detection /
a chi_li_icb scan over [0, eut], none of which has been run). Scaling: **~1.5-2 h** for the full 18-composition
sweep. That is a periodic/manual check, not a push/PR gate; the single
composition run here already exercises the full pipeline (CLI argv →
globalvar → planet_input → driverp's radius loop → shootp's Newton/RK4
shoot → h5/csv/figure output), just not all 18 compositions of it.

## Reference fixtures

- `reference/zenodo_v1.0.5/` -- **published-paper** output (Dunnigan et
  al. 2026; Zenodo DOIs in `PROVENANCE.md`), used as a published
  regression anchor (same v1.0.5 code; proves reproducibility, not
  independent correctness) in `integration/test_zenodo_parity.py`. Read-only; regenerate
  via `reference/zenodo_v1.0.5/extract_zenodo_slice.py`, never hand-edit.
- `reference/self_v1.0.5/` -- **self-generated** golden from this repo's
  current HEAD (no published output exists at CMC=0.424 specifically,
  only at the paper's CMC=0.426/0.443), used by `e2e/`. Regenerate with:

  ```
  cd /tmp && mkdir pie_regen && cd pie_regen
  ln -s /path/to/PIE/src/*.py . && cp /path/to/PIE/src/TmFeSmelt.dat .
  mkdir results
  PYTHONNOUSERSITE=1 MPLBACKEND=Agg /usr/bin/python3 main.py p 0.346 0.424 S Edmund
  cp results/CMR2_*_S_Edmund/pMetaData_0.00.csv \
     /path/to/PIE/testsys/reference/self_v1.0.5/CMR2_0.346_CMC_0.424_S_Edmund/
  ```

  Only regenerate deliberately, and say why in the commit message (a
  changed golden is either "fix the bug" or "intended behaviour
  change" -- never silent).
- `reference/self_v1.0.5/wide_sweep/` -- self-golden for the 36-case
  wide sweep (all 6 compositions x 2 MOI x 3 radii, full scalars +
  profiles, ~512 KB). Regenerate with
  `generate_wide_sweep.py` in that directory (see its own PROVENANCE.md
  for what it covers and the one documented non-convergent case).
- `reference/zenodo_v1.0.5/mc_wide/` -- 24-file (27 KB) curated slice of
  the FULL published Monte Carlo dataset (6144 result dirs across both
  MOI configs), read from `~/shared_dataset/zenodo.16459292/extracted/
  PIE/{work.margot,work.genova}/` -- the PRIMARY anchor for S/Si/S+Si
  (Edmund only; no Steinbruegge in this dataset) at real MC-drawn
  (CMR2, CMC) pairs spanning extremes/centre/most-converged-rows,
  scalars only (no `.h5` profiles in this dataset). Used by
  `integration/test_mc_wide_parity.py`. Regenerate with
  `extract_zenodo_slice.py --mc-wide` (needs `~/shared_dataset`).
- `reference/v1.0.4_20230127/` -- ONE small (17-row, ~2 KB) CSV from a
  stored 2023 run of an earlier code version, at the SAME (CMR2, CMC,
  light_element, liquidus_eq) as the `self_v1.0.5` e2e golden, used by
  `integration/test_v1_0_4_regression_history.py` as a secondary
  regression-history check (12 untouched fields gated to rtol=1e-6; 2
  known-changed fields -- `core_mass`'s volume-prefactor fix,
  `isnow`'s classification-logic fix -- checked against their
  documented delta instead). See that directory's PROVENANCE.md for the
  full per-field delta table.

### v1.2.0 identity + recovery gate (v1.3.0)

`testsys/integration/test_v1_2_0_invariant.py` re-runs the 14-case fixed
sample in `testsys/reference/v1_2_0_sweeps/sample.json` (one published MC
draw per failure class; 6 cases with converged v1.2.0 rows, 8 zero-row
cases) with the current `src/` and the v1.3.0 continue policy, capped at
(v1.2.0 rows + 2) radii per case, and asserts: every row that converged in
v1.2.0 (fixture `v1_2_0_sweeps.json`, generated from `src/` at 18cf78a with
`generate_sweeps.py --policy stop` on the pinned env) has a bit-identical
`v`, `f`, `fout` (exact on numpy 1.21.5/scipy 1.8.0, rtol 1e-9 elsewhere);
every additional converged row is "recovered" and valid (residual < 1e-5,
0 <= chi <= eutectic / Si max, ricb < rcmb, rho > 0, finite, smooth in
ricb); the committed `recovered_rows_v1_3_0.json` is reproduced.

## Findings (real bugs found while building this suite -- not fixed here, per constraint)

1. **`src/planet_input.py:119`** -- `elif mod_type == 'e':` references an
   undefined name (should be `code_mode`, matching the `if code_mode ==
   'p':` branch at line 62). `planet('e', ...)` always raises
   `NameError`; the evolution-model branch of `planet()` is unreachable
   dead code. Locked in as `testsys/unit/test_planet_input.py::test_planet_evolution_mode_would_ideally_work`
   (`xfail(strict=True)`).
2. **`src/driverp.py:111`, `if chi_li.any()<0:`** -- `.any()` returns a
   numpy bool (`True`/`False`, i.e. `1`/`0` when compared numerically);
   `bool < 0` is always `False`. This condition -- meant to set
   `error_code = 2` ("Final light element %wt negative") -- can NEVER
   fire, regardless of whether `chi_li` actually goes negative (it
   should read `(chi_li < 0).any()`). Confirmed dead: a scan of ~2000
   published Monte Carlo result rows (`~/shared_dataset/zenodo.16459292/
   .../work.{margot,genova}/results/*_S_Edmund/pMetaData_0.00.csv`)
   found zero rows with `error_code != 0`, consistent with this branch
   never having fired in the published dataset either (full census since:
   `error_code` is 0 in all 201,633 margot + 272,442 genova rows). The
   `error_code = 1` path is dead too: `src/libCore.py:142-144` sets
   `err = True` on negative chi, but `src/shootp.py:131` hard-codes
   `err0 = False` and returns that instead. **Fixed in v1.2.0** (PR #5):
   `(chi_li<0).any()` and the `err` flag are restored, and `error_code`
   now takes the values 0-6 listed in the top-level README; locked by
   `testsys/unit/test_dead_checks.py` and `test_error_codes.py`.
3. **`isnow` classification knife-edge (2 vs 3)** -- `src/shootp.py`'s
   `isnow=3` ("deep snow + layers") vs `isnow=2` ("deep snow")
   distinction hinges on `abs(adiabat_T - liquidus_T) < 1e-8` at one
   specific radial grid point -- an epsilon two orders tighter than the
   Newton solver's own `xtol=ftol=1e-6`. Confirmed: comparing a
   cold-start solve against a WARM-STARTED published value (same code
   version) lands on opposite sides of that threshold in 2/24 curated
   MC cases and ~1/18 sampled published-wide cases. Not a bug in the
   sense of giving a wrong physical answer (both "2" and "3" describe
   the same deep-snow state, with or without an additional marginal
   layers flag) but IS a fragile classification boundary -- worth
   `lars-eriksson` knowing the `1e-8` epsilon is not attainable-in-practice
   precision for a value computed via `xtol=ftol=1e-6`. Handled in
   `test_mc_wide_parity.py`/`test_published_wide_sweep.py` by accepting
   `{2, 3}` as equivalent ONLY for `isnow`, ONLY when comparing a
   cold-start solve to a warm-started reference (documented at the call
   site, not silently loosened globally -- `test_zenodo_parity.py` and
   `test_wide_self_consistency.py`, which compare like-for-like solve
   paths, still gate `isnow` to exact equality and do so successfully).
4. **2/240 `published_wide` samples: published run recorded ZERO
   converged rows where a fresh cold-start solve at the SAME first
   radius (10 m -- the same starting point `driverp.py`'s own `k=0`
   step uses, no warm-start history to explain a difference) DOES
   converge** (both `S+Si`, Genova MOI, `chi_Si_icb=0.05`, different
   MC-drawn (CMR2, CMC)). The safe direction (current code finds a
   solution the published run didn't, not the reverse -- not gated as a
   hard failure, see `test_published_wide_sweep.py`'s "soft mismatch"
   handling), but the cause is unconfirmed. Candidates, per
   `docs/audits/AUDIT_2026-09-29_solver-failures.md` (claims 4b, 5):
   (a) at ricb=10 m `getk2` has nrs=0, and the fluid loop at k=0 indexes
   `k+nrs-1 = -1`, wrapping to the CMB end and reading the uninitialised
   `g[399]` (`np.empty`, `src/shootp.py:426`, loop `:456-460`), so the
   10-m solve depends on heap contents; (b) the published solve itself
   is not reproducible at boundary cases -- a plain re-run of published
   10-m det(J)==0 case `runs/base/034.json` (genova S) went 0 -> 30
   radii. Earlier guess ("FD-Jacobian floating-point-path sensitivity")
   is unsupported. Not fixed here.
5. **2/240 `published_wide` samples: identical starting conditions
   (ricb=10 m, the FIRST radius, same CMR2/CMC/`chi_Si_icb`/code) but a
   fresh solve raises `RuntimeError('Factor is exactly singular')` in
   `src/libCore.py:266` (`getpotvsr`'s `b = inv(A)*rhs`, a sparse LU
   factorization used by `getk2`'s ellipticity calculation) where the
   published run converged.** The CONCERNING direction (current code
   reproduces fewer solutions than published, on identical input) --
   this one is NOT softened and IS a hard failure in
   `test_published_wide_sweep.py` as committed (2/240 = 0.8% failure
   rate; see that test's output for the exact two (CMR2, CMC) draws).
   NOT a SuperLU/LAPACK version or conditioning effect: SuperLU and
   dense LAPACK both solve the finite A; "exactly singular" here means A
   contains NaN (797 non-finite entries). Sufficient mechanism,
   unconfirmed as the cause of this flip
   (`docs/audits/AUDIT_2026-09-29_solver-failures.md` claim 4c;
   `docs/notes/failure_analysis_2026-09-28.md` §3.2): at ricb=10 m,
   nrs = round(400*ricb/rcmb) = 0 (`src/shootp.py:421`), so the fluid
   loop at k=0 (`:456-460`) indexes `k+nrs-1 = -1`, wrapping to the CMB
   end and reading `r[399]` and the still-uninitialised `g[399]`
   (`np.empty`, `:426`); `rho[0]`/`g[0]` themselves ARE set (`:442-443`).
   A NaN in that heap slot reproduces the failure with no Newton
   iteration; other fill values converge -- hence run-to-run flips (1 vs
   2 failures at a fixed seed). The flipping run was never captured with
   its heap contents / a `nonfinite_g` trace. `np.zeros` alone is NOT a
   fix (deterministic wrong values from the `(r0^3-r399^3)/r0^2` term);
   the fix is correct indexing plus raising on non-finite g/rho
   (`PATHWAY_FORWARD.md` item 17). Distinct from the published 10-m
   singular-LU crashes, which are a Newton overshoot to chi<0 (NaN
   originates in the RK4). Not fixed here.
6. **No convergence from a generic cold-start guess for Margot
   CMR2=0.346/CMC=0.426, `Si`, `Edmund`** at any inner-core radius tried
   (10 m, 50 km, 100 km, 150 km, 200 km, 400 km, 650 km) --
   `mynewtonSys` hits its singular-Jacobian or max-iterations
   `sys.exit()` guard every time. Not necessarily a bug: production
   code (`driverp.py`) always warm-starts each radius from the
   previous, converged radius's solution, which this suite's
   fast/direct solves deliberately do not (to stay radius-independent
   and parallelizable) -- it is plausible a warm-started path finds a
   solution this cold start does not. Tracked as a GATED failure mode
   (`testsys/integration/test_wide_self_consistency.py` and
   `testsys/e2e/test_wide_full_sweep.py` assert it keeps failing to
   converge, so a change in that behaviour either way is visible), not
   silently absorbed. Worth a human/`lars-eriksson` look to determine
   which (physical non-solution vs. solvable-with-a-better-guess).
7. **Two conflicting matplotlib installs** on `/usr/bin/python3`'s
   default `sys.path` (see "Environment" above) make `main.py`,
   `driverp.py`, and anything importing `visualization_present.py` or
   `TEST_visualization_evolution.py` **unconditionally** fail to
   import, regardless of `code_mode` -- `main.py` does `from drivere
   import *` at module level even in `code_mode='p'` runs, so a present-day-only
   run pays for the evolution-model plotting module's import too. Worked
   around at the test-harness level (`sys.path` fixup / `PYTHONNOUSERSITE=1`),
   not fixed in `src/`.
8. **`src/libCore.py:284-288`, `get_mass_core`** -- the fixed (bb37b0a)
   formula is `ssum = rho[0]*r[0]**3/r[-1]**3` for the FIRST term, then
   `rho[i]*(4/3)*pi*(r[i]**3-r[i-1]**3)` for every subsequent shell. The
   first term is a leftover, differently-normalised expression (it looks
   like a copy from `get_mass_norm`, which intentionally divides by
   `r[-1]**3` to get a *fraction*) and is dimensionally inconsistent with
   the absolute shell masses summed after it -- it should be
   `(4/3)*pi*rho[0]*r[0]**3` (the innermost sphere's mass). **Currently
   harmless**: every real call site starts integration at `r[0] =
   0.0001/a` (a few tens of microns), so this term is ~1e-12 relative to
   the total and vanishes in any tolerance this suite uses. Flagged for
   `lars-eriksson`/`kai-fischer`; not made into a failing regression test
   because it flags zero cases in the real corpus (every actual call
   site has `r[0]≈0`) -- see the audit principle in this suite's design
   brief: a check that fires on a scenario absent from real data is not
   evidence of a bug in that data.
9. **`src/libCore.py:59-68`, `reorder_el`** -- for `li_el == 'S+Si'`, the
   function's own `chi_Si_constant` argument is ignored; it returns
   `{'Si': chi_Si_icb, ...}` reading the **module-level global**
   `chi_Si_icb` (from `from globalvar import *`) instead. **Currently
   harmless**: every real call site (`getchi_li_grun`, `shoot_mercmodel`)
   passes `chi_Si_icb` itself as that argument, so argument and global
   always agree in production. Exercised (not "fixed") in
   `testsys/unit/test_libcore.py::test_reorder_el_s_plus_si_uses_module_level_chi_si_icb`.
