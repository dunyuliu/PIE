# Provenance: v1.0.3 (2022-10-21) regression-anchor fixtures

Class: **regression anchor** (`PROJECT_RULES.md` rule 5) -- parity with a
prior, untested PIE version, not evidence of correctness. v1.0.3 predates
the `bb37b0a` (v1.0.5) fix to `get_mass_core`'s missing `(4/3)*pi` volume
prefactor -- confirmed directly in this snapshot's own
`libCore.py:get_mass_core` (`rho[i]*(r[i]**3-r[i-1]**3)`, no `(4./3.)*np.pi`
term at all, same as the v1.0.4 snapshot documented in
`testsys/reference/v1.0.4_20230127/PROVENANCE.md`) -- so a "pass" against
these fixtures is parity with known-buggy legacy code, not independent
verification.

## Source (read-only oracle, never modified in place -- rule 7)

`~/3.Krista_Soderlund/MercuryInterior_MonteCarlo/dliu_20221021_v1.0.3/`
(a fixed, dated snapshot on this machine). Its own committed
`csvfiles/present_day_*.csv` outputs were HEADER-ONLY (0 data rows) for
every present-day composition (`margot_S_Edmund`, `margot_Si_Edmund`,
`genova_S_Edmund`, `genova_Si_Edmund`) -- confirmed by direct inspection
(`wc -l` = 1, header row only) -- so there was no pre-existing output to
read verbatim (rule 4: only fresh runs are evidence).

## How these fixtures were generated

Per rule 7 ("run regression anchors by invoking those trees' own
interpreters/scripts read-only; never edit them in place"): the ENTIRE
v1.0.3 source tree was copied verbatim to a scratch directory (never
back into the `~/3.Krista_Soderlund/...` tree), then run with
`/usr/bin/python3 main.py p <CMR2_preset> <light_element> Edmund` from
that scratch copy, with `PYTHONNOUSERSITE=1 MPLBACKEND=Agg` (same
two-matplotlib-installs workaround `testsys/conftest.py`/`run.py` use for
current HEAD -- v1.0.3 hits the identical `mpl_toolkits.mplot3d`
docstring-import trap on this box). `/usr/bin/python3` here carries
scipy 1.10.1, which still has `interp2d` (removed in scipy 1.14) --
v1.0.3's own `coreEos.py` uses `interp2d` directly (pre-dates this
repo's v1.1.1 `RectBivariateSpline` port), so this is the correct,
unmodified interpreter for running v1.0.3's own code, read-only.

v1.0.3's `globalvar.py` takes CMR2 as a NAMED PRESET string
(`'margot'` or `'genova'`), not a numeric value -- see
`planet_input.py`: `margot -> CMR2=0.346, CmC=0.148/CMR2`;
`genova -> CMR2=0.333, CmC=0.148/CMR2`. These do NOT match the numeric
CMC=0.424 used elsewhere in this repo's Margot-fit fixtures (that is a
DIFFERENT, later convention introduced in v1.0.4+); the fixtures below
are compared against current HEAD using v1.0.3's OWN preset-derived
(CMR2, CMC) pair, not 0.424, to keep the comparison apples-to-apples.

- `margot_S_Edmund/csvfiles/present_day_margot_0.0.csv`: 13 data rows,
  `python3 main.py p margot S Edmund`. CMR2=0.346, CmC=0.148/0.346
  (~0.427746).
- `genova_Si_Edmund/csvfiles/present_day_genova_0.0.csv`: 13 data rows,
  `python3 main.py p genova Si Edmund`. CMR2=0.333, CmC=0.148/0.333
  (~0.444444).

## Margot Si-only: does NOT converge in v1.0.3 itself

`python3 main.py p margot Si Edmund` (same scratch copy, same
environment) was ALSO run, read-only, as the natural Si-only pairing
for the margot preset -- it printed `Solution not found within
tolerance after_ 13 _iterations` and exited with ZERO data rows
written (matching the pre-existing header-only file in the source
tree exactly, confirming this is v1.0.3's own genuine, reproducible
behaviour, not an artifact of this rerun's environment). `genova Si
Edmund` was substituted as the Si-only regression anchor instead --
it converges to 13 rows. This is a real limitation of the v1.0.3
solver at the margot (CMR2=0.346) composition for Si-only, not
something fixed or worked around here (no edits to v1.0.3's code); see
`testsys/integration/test_v1_0_3_regression_history.py` for how this is
used (S-only anchored at margot's CMR2/CmC, Si-only anchored at
genova's).

## Measured deltas (v1.0.3 -> current HEAD)

Every field EXCEPT `core_mass` matches current HEAD to <=~3e-10 relative
(both at the S/margot and Si/genova compositions, radii 50010 m and
600010 m -- see the test for the live-solve comparison) -- i.e. the
underlying physics/algorithm has not changed since 2022-10-21 apart
from the documented `core_mass` prefactor. `core_mass`'s ratio
(current/v1.0.3) is exactly `(4/3)*pi = 4.18879020478639` at every row
checked, matching the same known, attributed bug as the v1.0.4 anchor.
