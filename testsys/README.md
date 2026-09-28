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
| Contract | `contract` | Output CSV/h5 schema vs `globalvar.presentday_columns`, CI workflow YAML validity and push/PR-excludes-e2e, README/run.py/pytest.ini tier-name parity, repo hygiene (src/ untouched) | 12 | ~0.5 s |
| Integration | `integration` (parity subset also marked `parity`) | One real present-day Newton solve at Margot CMR2=0.346/CMC=0.424 (self-consistency: convergence, CMR2/CMC recovery, physical sanity); 3 solves compared against **published paper output** (Dunnigan et al. 2026) for the SAME code | 9 + 3 | ~19 s + ~56 s |
| E2E | `e2e` | `main.py p 0.346 0.424 S Edmund` end-to-end in a tmp dir (one full composition, the smallest realistic subset of `scheduler.py`'s sweep), diffed against a committed self-golden | 4 | ~5.5 min |

Fast-tier total (unit+contract+integration, what CI runs on every
push/PR): **≈85 s**.

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

## Findings (real bugs found while building this suite -- not fixed here, per constraint)

1. **`src/planet_input.py:119`** -- `elif mod_type == 'e':` references an
   undefined name (should be `code_mode`, matching the `if code_mode ==
   'p':` branch at line 62). `planet('e', ...)` always raises
   `NameError`; the evolution-model branch of `planet()` is unreachable
   dead code. Locked in as `testsys/unit/test_planet_input.py::test_planet_evolution_mode_would_ideally_work`
   (`xfail(strict=True)`).
2. **Two conflicting matplotlib installs** on `/usr/bin/python3`'s
   default `sys.path` (see "Environment" above) make `main.py`,
   `driverp.py`, and anything importing `visualization_present.py` or
   `TEST_visualization_evolution.py` **unconditionally** fail to
   import, regardless of `code_mode` -- `main.py` does `from drivere
   import *` at module level even in `code_mode='p'` runs, so a present-day-only
   run pays for the evolution-model plotting module's import too. Worked
   around at the test-harness level (`sys.path` fixup / `PYTHONNOUSERSITE=1`),
   not fixed in `src/`.
3. **`src/libCore.py:284-288`, `get_mass_core`** -- the fixed (bb37b0a)
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
4. **`src/libCore.py:59-68`, `reorder_el`** -- for `li_el == 'S+Si'`, the
   function's own `chi_Si_constant` argument is ignored; it returns
   `{'Si': chi_Si_icb, ...}` reading the **module-level global**
   `chi_Si_icb` (from `from globalvar import *`) instead. **Currently
   harmless**: every real call site (`getchi_li_grun`, `shoot_mercmodel`)
   passes `chi_Si_icb` itself as that argument, so argument and global
   always agree in production. Exercised (not "fixed") in
   `testsys/unit/test_libcore.py::test_reorder_el_s_plus_si_uses_module_level_chi_si_icb`.
