Vendored reference code: Steinbruegge et al. (2020), Geophysical Research
Letters, doi:10.1029/2020GL089895.

Source: https://github.com/gregorsteinbruegge/MercuryInterior
Pinned commit: 8dc64663c574bc9dc1b3ecbb74252fbb3b1a2383
Fetched: 2026-09-30
License: MIT (LICENSE, verbatim from upstream)

Files vendored verbatim, unmodified, from the pinned commit:
  coreEos.py    -- EOS classes (Vinet + Anderson-Grueneisen), Gibbs
                   free energy fits, Margules solution model
  libcore.py    -- shooting-method interior solver (shoot_mercmodel,
                   mynewtonSys, getk2, ...)
  run_models.py -- original driver script (kept for reference/provenance
                   only; NOT imported by the tests runner below,
                   because it imports visualization.py)

Deliberately NOT vendored:
  visualization.py -- only consumed by run_models.py for plotting;
                   pulls in matplotlib, which is not needed to compute
                   any of the scalar/profile quantities this test suite
                   anchors against. Not imported by coreEos.py or
                   libcore.py.

Module name clash: this package's module is named `coreEos`, which
clashes with PIE's own src/coreEos.py. `run_steinbruegge_case.py` in
this directory MUST be invoked as its own `/usr/bin/python3` subprocess
(never imported into the same process as PIE's src/) -- see
tests/integration/test_steinbruegge_anchor.py, which does exactly
that via subprocess.run().

Read-only per PROJECT_RULES.md rule 7: this directory is treated as an
external reference tree once vendored -- do not edit coreEos.py,
libcore.py, or run_models.py to "fix" anything found while comparing
against PIE; any real bug found in either codebase is reported, not
patched here.

See docs/dev/notes/steinbruegge_anchor_2026-09-30.md for the full physics
diff between this code and src/coreEos.py / src/libCore.py / src/shootp.py.
