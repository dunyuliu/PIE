# Version history

Version source of truth: git tags (`vX.Y.Z`) and GitHub releases.
`CHANGELOG.md` in the repository root holds the full per-release change
list; this page is a short timeline. Pre-v1.0.5 development notes live in
`update_log` (frozen).

| Version | Date | Summary |
|---|---|---|
| v1.0.5 | -- | The code archived with Dunnigan et al. 2026 (Zenodo 10.5281/zenodo.16929504). |
| v1.1.0 | -- | First tested baseline (testsys, CI, rules, citation); `src/` byte-identical to v1.0.5. |
| v1.1.1 | 2026-09-29 | `scipy.interp2d` port to `RectBivariateSpline`. |
| v1.2.0 | 2026-09-30 | Error codes, clean exits, solver log, dependency manifest. |
| v1.3.0 | 2026-09-30 | Bounded line-search Newton, `getk2` `nrs=0` fix, continue-after-failure sweeps, failure rows in csv. |
| v1.3.1 | 2026-10-01 | `pytest-xdist` parallelism, no physics change (patch). |
| v1.3.2 | 2026-10-01 | Linear-solve performance (`spsolve` over `inv`), no algorithm change (patch). |
| v1.3.3 | 2026-10-01 | Opt-in vectorised GK21 quadrature (`PIE_FAST_QUAD`, default off, patch). |
| v1.4.0 | 2026-10-02 | Robust-runner feature, `src/` import narrowing, test-coverage/doc hardening. |
| v1.5.0 | 2026-10-02 | Python 3.10 -> 3.12 + current dependency pins (major dep bump); `uv`-managed venv the one supported environment. |
| v1.5.1 | 2026-10-03 | `PIE_FAST_QUAD` (GK21 quadrature) defaults ON. |
| v1.6.0 | 2026-10-03 | `src/` renamed to the installable `pie/` package; `util/` split (`util/plot/`, `util/run/`); `summaryPlot.py` bug fixes and `robust_runner.py` lock-race/silent-fallback fixes. |
| v1.6.1 | 2026-10-04 | Patch: `pie/shootp.py` non-finite ICB density now raises `SolverError` (code 7) instead of an uncaught `ValueError` that killed the whole sweep; `robust_runner.py::run_one_job` counts csv rows whenever the file exists, not only on `returncode == 0`; stale-lock reclaim race fix. No API/behaviour-breaking change, no numerical-output change. |

See `CHANGELOG.md` for the full entry text, including board-item
references, PR numbers, and regression-test pointers for each change.
