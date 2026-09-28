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
| Contract | `contract` | Output CSV/h5 schema vs `globalvar.presentday_columns`, CI workflow YAML validity and push/PR-excludes-e2e, README/run.py/pytest.ini tier-name parity, repo hygiene (src/ untouched), scipy `interp2d` dependency canary | 13 | ~0.5 s |
| Integration | `integration` (parity subset also marked `parity`) | One present-day solve at Margot CMR2=0.346/CMC=0.424 (self-consistency); 3 solves vs **published paper output** (regression anchor, same code) with ALL 19 scalars + full radial profiles gated; **wide fast subset**: 1 radius x 2 MOI x 6 compositions (12 cases, all scalars+profiles, incl. a documented non-convergent case); **v1.0.4 (2023) history**: 17-row field-by-field diff with 2 known, attributed deltas | 9+3+12+14 | ~19s+~57s+~52s+~0.02s |
| E2E | `e2e` | (a) `main.py p 0.346 0.424 S Edmund` end-to-end in a tmp dir via the REAL CLI subprocess (full file/figure I/O), vs a self-golden; (b) wide sweep, ALL 3 radii x 2 MOI x 6 compositions (36 cases, all scalars+profiles), direct-solve (not CLI), parallelized, CI-sharded by composition | 4 + 36 | ~4.5 min + ~54 s |

Fast-tier total (unit+contract+integration, what CI runs on every
push/PR): **≈129 s** (82 passed, 1 xfailed).

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
this is the model's own physical limit at this CMR2/CMC, reproduced by
the golden, not a bug). Scaling: **~1.5-2 h** for the full 18-composition
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
- `reference/v1.0.4_20230127/` -- ONE small (17-row, ~2 KB) CSV from a
  stored 2023 run of an earlier code version, at the SAME (CMR2, CMC,
  light_element, liquidus_eq) as the `self_v1.0.5` e2e golden, used by
  `integration/test_v1_0_4_regression_history.py` as a secondary
  regression-history check (12 untouched fields gated to rtol=1e-6; 2
  known-changed fields -- `core_mass`'s volume-prefactor fix,
  `isnow`'s classification-logic fix -- checked against their
  documented delta instead). See that directory's PROVENANCE.md for the
  full per-field delta table.

## Findings (real bugs found while building this suite -- not fixed here, per constraint)

1. **`src/planet_input.py:119`** -- `elif mod_type == 'e':` references an
   undefined name (should be `code_mode`, matching the `if code_mode ==
   'p':` branch at line 62). `planet('e', ...)` always raises
   `NameError`; the evolution-model branch of `planet()` is unreachable
   dead code. Locked in as `testsys/unit/test_planet_input.py::test_planet_evolution_mode_would_ideally_work`
   (`xfail(strict=True)`).
2. **No convergence from a generic cold-start guess for Margot
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
3. **Two conflicting matplotlib installs** on `/usr/bin/python3`'s
   default `sys.path` (see "Environment" above) make `main.py`,
   `driverp.py`, and anything importing `visualization_present.py` or
   `TEST_visualization_evolution.py` **unconditionally** fail to
   import, regardless of `code_mode` -- `main.py` does `from drivere
   import *` at module level even in `code_mode='p'` runs, so a present-day-only
   run pays for the evolution-model plotting module's import too. Worked
   around at the test-harness level (`sys.path` fixup / `PYTHONNOUSERSITE=1`),
   not fixed in `src/`.
4. **`src/libCore.py:284-288`, `get_mass_core`** -- the fixed (bb37b0a)
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
5. **`src/libCore.py:59-68`, `reorder_el`** -- for `li_el == 'S+Si'`, the
   function's own `chi_Si_constant` argument is ignored; it returns
   `{'Si': chi_Si_icb, ...}` reading the **module-level global**
   `chi_Si_icb` (from `from globalvar import *`) instead. **Currently
   harmless**: every real call site (`getchi_li_grun`, `shoot_mercmodel`)
   passes `chi_Si_icb` itself as that argument, so argument and global
   always agree in production. Exercised (not "fixed") in
   `testsys/unit/test_libcore.py::test_reorder_el_s_plus_si_uses_module_level_chi_si_icb`.
