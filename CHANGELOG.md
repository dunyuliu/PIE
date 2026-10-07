# Changelog

Version source of truth: git tags (`vX.Y.Z`) and GitHub releases; `CITATION.cff` `version:` is bumped in each release PR. This file holds the per-release change list (moved from `src/VERSION` in v1.1.0; history unchanged below). Pre-v1.0.5 development notes: `update_log` (frozen).

* v1.6.3; 20261007; patch, same-day user-facing bugfix plus completion of
  item 9's star-import narrowing (`pie/driverp.py`, `pie/planet_input.py`,
  `util/plot/summaryPlot.py`) and one regression test, all nine PRs
  (#95-#105, squash-merged `f7eb052`..`7d95c08`) landed on `main` since
  v1.6.2. No public CLI contract change, no numerical/physics output
  change, no dependency-pin change -- patch is the right call, not minor:
  the one behavior change (board item 28f, `pie/globalvar.py` no longer
  parsing `sys.argv` at import time) was itself released in v1.6.2's
  predecessor chain before this tag and is not new here; what is new this
  release is entirely refactor + a same-day fix of a regression that
  refactor introduced, plus its regression test.
  * **Fixed** (board item 35, PR #101 squash `f503af5`, 2026-10-07):
    `util/plot/read_plot_datah5.py` -- a real standalone entrypoint listed
    in CLAUDE.md's "Running" -- never called the (PR #95-introduced)
    `globalvar.parse_argv(sys.argv)` before its
    `from pie.planet_input import planet`, so every invocation since
    `f7eb052` (merged 2026-10-06) raised `ImportError: cannot import name
    'CMC' from 'pie.globalvar'`. Live on `main` for about a day before
    being caught; fixed same day by adding the `parse_argv()` call,
    matching the pattern `util/plot/summaryPlot.py`/`pie/main.py` already
    use.
  * **Changed** (board item 9, now fully closed): star-imports narrowed to
    explicit name lists in the three remaining science-path modules --
    `pie/driverp.py` (PR #97 squash `303672b`, 11-name list),
    `pie/planet_input.py` (PR #99 squash `3b7c45e`, `globalvar`/`libCore`
    split into two explicit lists), and `util/plot/summaryPlot.py` (PR #101,
    same commit as the fix above) -- whose two star-imports
    (`pie.drivere`, `pie.driverp`) were dropped outright rather than
    narrowed, since the file's own code uses no name from either module.
    No behavior change in any of the three; each landed with a full fast-
    tier gate and CI green on PR head and merge SHA.
  * **Added** (board item 35, PR #104 squash `5900087`, 75 lines,
    mutation-verified): `testsys/contract/test_read_plot_datah5_argv_parse.py`
    locks the fix above -- runs the script as a real subprocess, asserts no
    `ImportError`/`NameError` during the import chain, and asserts it gets
    far enough to fail downstream at the (deliberately absent) `.h5`
    fixture's `pd.read_hdf()` instead.
  * **Docs**: `CLAUDE.md`'s item-9 closed-module list corrected to include
    `driverp.py` (PR #103 squash `b60710c`), which PR #97 had landed without
    updating; `PATHWAY_FORWARD.md` items 9 and 35 updated to record the
    zofia-kaminska audits that corrected item 9's two premature closures
    and tracked the item-35 regression to its test-coverage close (PRs #96,
    #98, #100, #102, #105, all board-only, no code change).
  * Gate: fresh `uv venv --python 3.12` + `uv pip install -e .` +
    `uv pip install -r testsys/requirements.txt` in this release worktree,
    `.venv/bin/python3.12 testsys/run.py -n 4 unit contract integration` --
    304 passed, 15 skipped, 3 xfailed, 0 failed, 146.46s (independently
    reproduced, not taken on faith from any PR's own reported count).
* v1.6.2; 20261005; patch, docs-only: publishes the new MkDocs user-guide
  site (board item 34, docs/user/, PR #88) to GitHub Pages at
  https://dunyuliu.github.io/PIE/, via `.github/workflows/docs.yml`
  (builds on every push/PR, deploys only on a `v*` tag push). No `pie/`
  code change of any kind -- `git diff v1.6.1..HEAD -- pie/` is empty,
  confirmed before this release was cut. Also carries the item-33
  pre-commit path-hygiene hook (`.githooks/`, PR #84) and the item-31
  v1.0.5-vs-HEAD audit documentation (PRs #79-86, #89), both already on
  `main` since v1.6.1 and released here for the first time. Grant: patch
  release, owner-requested, full ceremony (not the lighter patch cadence).
  * **Added** (board item 34): `docs/user/` MkDocs Material site --
    getting-started, running-a-case, model-overview, parameters, outputs,
    benchmarks, troubleshooting, citing pages; `docs/user/gen_params.py`
    regenerates the parameter/error-code reference table from
    `pie/globalvar.py`'s `ErrorCode` enum, gated `--check`-clean in CI
    before `mkdocs build --strict`.
  * **Fixed** (found in this release's audit, before tagging): three
    `docs/user/` files (`mkdocs.yml`'s `site_url`/`repo_url`/`repo_name`,
    `getting-started.md`'s `git clone` command, `benchmarks.md`'s
    `testsys/README.md` link) pointed at the wrong GitHub owner
    (`dunyu-liu`, a 404) instead of the actual `dunyuliu` -- the published
    quickstart clone command would not have worked. Fixed before the tag.
  * **Fixed** (repo configuration, found in this release's audit): the
    `github-pages` deployment environment's branch-policy allowed deploys
    only from `main`, not from a tag, so `docs.yml`'s tag-triggered
    `deploy` job would have been rejected outright by GitHub the first
    time a `v*` tag was pushed. Added a `v*` tag policy to the
    `github-pages` environment via the GitHub API before tagging.
  * **Docs**: `PROJECT_RULES.md` rule 1's root whitelist now lists
    `.githooks/` explicitly (board item 33, previously shipped without an
    update to the whitelist it falls under); `PATHWAY_FORWARD.md` item 34
    updated to record the owner's first-deploy approval and both fixes
    above.
  * Remaining open issues, not addressed here (non-blocking, see
    `PATHWAY_FORWARD.md`): item 31's "knox"/internal-host mentions in
    `docs/user/running-a-case.md` (cosmetic, routed to a follow-up); 12
    item-31 audit-pilot JSON files under `docs/notes/` still carry
    truncated machine-local path fragments the hygiene contract test's
    pattern does not match (owner's path-leak policy is forward-only
    redaction, not release-blocking, item 33).
  * Gate: `testsys/run.py -n 4 unit contract integration` on a fresh
    `uv venv --python 3.12` built from the pinned manifest in this release
    worktree -- 292 passed, 15 skipped, 3 xfailed, 0 failed, 230.59s.
    `mkdocs build --strict -f docs/user/mkdocs.yml` and
    `docs/user/gen_params.py --check` both green on the same tree, post-fix.
* v1.6.1; 20261004; patch, two independent crash/observability fixes to
  `pie/robust_runner.py` and `pie/shootp.py`, both landed on `main` since
  v1.6.0 and released here for the first time (neither was in any prior
  CHANGELOG entry). No API/behaviour-breaking change; no change to any
  converged numerical output. Grant: patch release, owner-authorized
  explicit full-ceremony run (not the lighter patch cadence), under the
  standing "unattended-merge grant ... for v1.x patch/minor releases"
  (CHANGELOG v1.4.0 entry, owner-approved 2026-10-02, still in effect).
  * **Fixed** (board item 30, PR #72 squash `133967a`, closed PR #73 squash
    `c2246f0`): `pie/shootp.py::shoot_mercmodel` could build a non-finite
    ODE initial state `y0` when a bounded-line-search Newton trial iterate
    pushed `eosInnerCore` outside its domain; `scipy.integrate.solve_ivp`
    then raised a bare `ValueError` that `pie/driverp.py`'s per-radius
    `except lc.SolverError` handler did not catch, killing the whole sweep
    process and losing every remaining radius (observed in 326/1,400
    sampled jobs, 23%, during the item-18a population re-run). `y0` is now
    checked for finiteness immediately before `solve_ivp` and raises a new
    `SolverError(ErrorCode.NONFINITE_ICB_DENSITY, code 7)`
    (`pie/globalvar.py`) -- inside the line search this is a rejected
    trial, at the Newton level a per-radius failure row, and the sweep
    continues; no blanket `except ValueError` was added anywhere (verified
    by victor-reyes's and lars-eriksson's audits). README's error-code
    table gains row 7. Regression tests:
    `testsys/integration/test_item30_nonfinite_icb_density_crash.py`,
    `testsys/integration/test_item30_robust_runner_hides_partial_rows.py`.
  * **Fixed** (same PR #72): `pie/robust_runner.py::run_one_job` only read
    the per-job csv back (`summarize_error_codes`, sets `n_rows`) when
    `returncode == 0`; a job that crashed mid-sweep (e.g. the item-30 bug
    above, or any other nonzero-exit case) reported `n_rows=0` regardless
    of rows actually written before the crash, hiding real partial output
    from monitoring/resume logic. Now reads the csv whenever it exists,
    regardless of return code; status semantics unchanged (nonzero rc is
    still `PROCESS_CRASHED`). Observability/operational only -- no change
    to any convergence result.
  * **Fixed** (board item 29a, PR #62 squash `0454817`, landed after the
    v1.6.0 tag and not previously changelogged): `pie/robust_runner.py`'s
    stale-lock reclaim was not atomic -- two reclaimers could both pass the
    staleness check on the same dead-pid lock, then race `_release_lock`'s
    unconditional `os.remove` against a third process's fresh re-acquire,
    letting two runners believe they held the same job's lock (the exact
    double-truncation failure mode item 26's lock was built to prevent).
    `_acquire_lock` now returns a per-claimant token recorded in the lock
    JSON; `_reclaim_stale_lock` takes an `fcntl.flock` on a sibling mutex
    file and re-checks staleness inside the critical section, swapping the
    stale file via `os.replace` (lock path never momentarily absent);
    `_release_lock` is compare-then-delete when given a token. Narrow
    trigger (a prior crash plus two reclaimers racing within a few
    syscalls); not hit in CI or any gate run to date, but load-bearing for
    large concurrent TACC/knox batches. New test:
    `testsys/unit/test_robust_runner_item29a.py` (5 cases, red/green
    verified both ways).
  * **Housekeeping, also shipping in this tag for the first time since
    v1.6.0** (testsys-only, not user-facing): item 29b
    (`testsys/reference/perf_v1.3.3/generate_real_quad_calls.py`'s stale
    `sys.path.insert(0, ROOT/"src")` replaced with package-style
    `importlib.import_module("pie....")` imports, post item-28e rename)
    and item 28h (`testsys/conftest.py` fully deleted; `testsys/pielib.py`
    is now loaded as a pytest plugin via `testsys/pytest.ini`).
  * **Not in this release, but committed to `main` in the same window and
    worth flagging for the record**: item 18/18a's population-census and
    snow-fraction re-analysis (`docs/notes/item18_snowfraction_2026-10-03.md`,
    `docs/notes/item18a_population_rerun_2026-10-03.md` and their
    `_scripts/` directories) -- these are research data/docs, not `pie/`
    code, audited AUDITED-PASS by priya-nair, but the owner's erratum/
    comment decision for coauthors is still open; no number has been sent
    to any coauthor. Item 31 (convergence regression vs v1.0.5, 6,964/
    23,608 pre-stop radii) is open, unconfirmed root cause, awaiting an
    owner scope decision -- explicitly not touched by this patch.
  * No refactor pass was dispatched for this release: the net production
    diff is ~30 lines across the item-30 fix plus the already-landed item-
    29a fix, and both audits (zofia-kaminska rule-book, victor-reyes
    technical) came back clean-or-low/advisory-only, so a kai-fischer pass
    was judged unnecessary rather than skipped.
  * Two Low-severity residual risks noted by victor-reyes, both
    non-blocking per his own verdict (re-confirmed here): (1) a density
    that goes non-finite *during* `solve_ivp` integration rather than at
    the initial state is still mislabeled under error code 2/3 instead of
    7 -- undercounts code-7 stats, does not crash; (2) a retried job
    crashing before `pie/main.py:152`'s csv truncation can report a stale
    previous attempt's row count under `PROCESS_CRASHED`, a log-only
    exposure. Two Advisory items, also non-blocking: stale docstrings
    mentioning "codes 1-5" for retry logic; NaN/Infinity appearing in JSON
    solver-log context dicts (not strict-JSON).
  * zofia-kaminska's Mode B rule-book audit found no new violations in this
    patch's blast radius. One pre-existing Tier-3 unenforceable-as-written
    finding, not introduced by this patch: no branch protection configured
    on `main`, so rule 13's "green CI on merge SHA" gate is operator-
    discipline-only today, not mechanically enforced.
  * Gate: fresh `testsys/run.py unit contract integration` (fast tier) on
    the pinned py3.12 venv, this exact tree -- see Work record below for
    the count. CI: see "CI run this release was gated on" below.
* v1.6.0; 20261003; owner correction 2026-10-03: collapses what were
  drafted across PRs #52-#59 as three separate entries (v1.6.0/v1.6.1/
  v1.6.2) into this single release -- none of those three was ever tagged
  individually, so this is the one version actually cut. Grant: minor
  release, pre-authorized by the project owner under the standing
  "unattended-merge grant ... for v1.x patch/minor releases" (CHANGELOG
  v1.4.0 entry below, owner-approved 2026-10-02, still in effect); the
  packaging rename below is user-facing and breaking on its own terms, but
  per that grant and explicit owner pre-authorization for this release it
  ships as a minor bump, not a major one.
  * **Breaking**: board item 28(e), the owner's launch-mode decision
    superseding PR #53's "marker only, deferred" framing: `src/` is renamed
    to `pie/` and is now a real installed Python package
    (`uv pip install -e .`, new root `pyproject.toml`), not a directory
    inserted onto `sys.path`. User-facing on three axes:
    1. **Setup**: `uv pip install -r requirements.txt` into a bare venv is
       replaced by `uv pip install -e .` (editable install of the `pie`
       package); `requirements.txt` remains the pin source of truth (rule
       3b) and `pyproject.toml`'s `[project.dependencies]` must match it
       exactly (new contract test
       `test_pyproject_dependencies_pin_exact_versions_and_agree_with_requirements`).
    2. **Import path**: sibling modules (`globalvar`, `libCore`, `shootp`,
       `shoote`, `solver`, `planet_input`, `driverp`, `drivere`, `coreEos`,
       `main`, `TEST_visualization_evolution`, `visualization_evolution`)
       converted from bare top-level imports (`from globalvar import ...`,
       `import shootp as lc`) to package-relative imports
       (`from .globalvar import ...`, `from . import shootp as lc`).
       Callers outside the package (`util/plot/*.py`, `testsys/`) now
       `import pie` / `from pie import <module>` instead of inserting a
       directory onto `sys.path`.
    3. **Run recipes**: the former
       `cd src && python main.py p CMR2 CMC light_element liquidus_eq [chi_Si_icb]`
       is replaced by the console entry point
       `pie p CMR2 CMC light_element liquidus_eq [chi_Si_icb]` or,
       equivalently, `python -m pie p ...` (`pie/cli.py` + `pie/__main__.py`,
       both a one-line `runpy.run_module("pie.main", run_name="__main__")`
       so `pie/main.py`'s own script-style top-level code and
       package-relative imports are unaffected). `testsys/conftest.py`'s
       helper functions moved to a new `testsys/pielib.py` (`conftest.py`
       is now a ~15-line fixture-only stub); `import_src`/`solve_full_model`
       now `importlib.import_module("pie.<name>")`. `README.md`,
       `testsys/README.md`, `util/plot/*.py`, and
       `.github/workflows/test.yml` updated together in the same PR per
       rule 11. `PROJECT_RULES.md` rule 1's root whitelist updated
       (`pyproject.toml` added, `src/` -> `pie/`). No physics/algorithm
       change anywhere -- `pie/`'s contents are otherwise byte-identical to
       `src/` modulo the import-statement rewrites (verified: before/after
       `testsys/run.py all` counts match).
  * **Fixed** (PR #56, board items 28(b)/24/26): (a) item 28(b) closed --
    `scheduler.py`/`monteCarlo.run.py` moved `pie/` -> `util/run/` (pure
    operational scripts, no `pie`-internal imports, invoked as
    `python -m pie`/by path); `robust_runner.py` deliberately kept in
    `pie/` (imported as `from pie import robust_runner` by three test
    files, self-locates its results dir to the package dir, dual-mode
    importable-and-bare-script by design -- moving it would break that
    pattern for no functional gain). (b) item 24 fixed --
    `pie/globalvar.py`'s `contourplot_file` uncommented and defined
    (prefixed with `contour_plotting_path` so a bare filename doesn't land
    in whatever cwd the script runs from) and imported into
    `util/plot/summaryPlot.py`'s explicit import list;
    `contour_scale = int(np.log10(sample))` uncommented; `contourdond`
    typo fixed to `contourcond`; incidental 4th bug found and fixed while
    adding the regression test -- `plt.cm.get_cmap(cmap)` (removed in
    matplotlib >=3.9) replaced with `matplotlib.colormaps[cmap]`. (c) item
    26 fixed -- `pie/robust_runner.py`'s `run_one_job` gained a per-job
    atomic (`O_CREAT|O_EXCL`) lock file, claimed first and released in a
    `finally`, with same-host dead-pid stale-lock reclaim (needed for
    `testsys/integration/test_robust_runner_crash_restart.py`'s
    SIGKILL/resume case to still pass); `main.py:124`'s bare `sys.exit()`
    audited and confirmed unreachable from the runner's actual argument
    space (left as dead code, not fixed, not asked for); `pie_workers()`'s
    silent 4-worker fallback on `OSError`/`AttributeError` now prints the
    exception to stderr before returning 4. Regression tests,
    mutation-verified: `testsys/unit/test_summaryplot_contour_bugs.py`
    (2 cases), `testsys/unit/test_robust_runner_item26.py` (6 cases,
    including a reproduction of the crash/restart test's exact pre-fix
    failure when the stale-lock reclaim is reverted).
  * **Performance** (PR #55, board item 27, re-profiling pass after the
    v1.3.3/v1.5.1 GK21 port): `pie/coreEos.py:meltingDataFromFile.__call__`
    skips `np.sort()` when the (already `np.atleast_1d`-built) p/x array
    has length <= 1 -- a no-op removed, not a numeric change, bit-identical
    BY CONSTRUCTION on every environment, no new flag needed, ships
    default-on. Re-profiling (cProfile, canonical Margot-fit case,
    py3.12/numpy==2.5.3/scipy==1.18.1 pinned env) found this wrapper at
    ~25% of a single-radius solve, ~11 points of which was pure
    sort/atleast_1d/atleast_2d/array dispatch overhead around a call that
    is >99% scalar in real use. Measured: single radius 2.72s -> 2.56s
    (1.06x); 5-radius real sweep 18.97s -> 17.96s (1.06x). Differential
    test (`testsys/unit/test_perf_v1_3_4_melting_sort_skip.py`): max diff
    0.0 on real captured solver-state (x, p) pairs, plus a synthetic
    length>1 case proving real `np.sort` still runs when length > 1.
    `scipy.optimize.root` (hybrd, ~23% of the solve) and
    `CubicSpline.__call__` overhead inside `eos`/`volume` were profiled but
    NOT touched -- flagged as findings only, see `docs/notes/perf_v1.3.4.md`.
    PR #57 escalated the hybrd divergence-bound question to the owner; PR
    #59 records the owner's 2026-10-03 clarification that the standing
    v1.3.3 integrator rule already answers it and declines a further
    mira-volkov porting campaign for this release (cost/benefit call, see
    `PATHWAY_FORWARD.md` item 27) -- no code change in #57/#59, board rows
    only.
  Gate: fresh `testsys/run.py all` on a from-scratch pinned Python 3.12 venv
  (`uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python3.12 -e .`)
  built on this exact committed tree -- 327 passed, 15 skipped, 3 xfailed,
  0 failed, 424.10s. Supersedes every per-PR count quoted above.
* v1.5.0; 20261002; dependency MAJOR-version upgrade: pinned environment moved from Python 3.10 (numpy 1.21.5, scipy 1.8.0, pandas 1.3.5, matplotlib 3.5.1, h5py 3.6.0, tables 3.7.0, pytest 6.2.5, pytest-xdist 2.5.0, pyyaml 6.0.1) to Python 3.12 (numpy 2.5.3, scipy 1.18.1, pandas 3.0.6, matplotlib 3.11.2, h5py 3.16.0, tables 3.11.1, pytest 9.1.1, pytest-xdist 3.8.0, pyyaml 6.0.3), resolved with `uv` (PROJECT_RULES.md rule 3b/3c: the pinned manifest is now THE one supported environment, not an option). `pandas==3.0.6` is itself a major bump (unconditional copy-on-write, new default string dtype); a static grep of `read_hdf`/`to_hdf`/`Series`/`DataFrame` usage (`src/driverp.py:271-302`, `src/drivere.py:18-28`, `src/main.py:180`, `src/read_plot_datah5.py:21-27`) found no chained-assignment or `dtype==object` patterns, and the full `testsys/run.py all` tier on the new pins surfaced zero pandas-3.0 regressions needing a code fix.
    1. Bug found and fixed during this migration (not pandas-specific): `testsys/conftest.py:53` and three fixture-regeneration scripts (`testsys/reference/v1_2_0_sweeps/generate_sweeps.py`, `testsys/reference/perf_v1.3.2/generate_real_solver_states.py`, `testsys/reference/perf_v1.3.3/generate_real_quad_calls.py`) filtered `sys.path` on the bare substring `"/.local/"` to drop a stray `pip --user` matplotlib install (see each file's own docstring). Under the new uv-managed Python 3.12 interpreter, the interpreter's OWN stdlib also resolves under `~/.local/share/uv/python/.../lib/python3.12`, so the blanket filter stripped the interpreter's own stdlib out of `sys.path` and broke every test/subprocess invocation (`ModuleNotFoundError: No module named 'pdb'` / `'warnings'`). First narrowed to `"/.local/lib/"` (pip-user-site-packages pattern) with a locking regression test; **superseded same day by owner ruling**: with the pinned venv now the one supported environment (rule 3b/3c), user-site is disabled and apt dist-packages are absent from `sys.path` by construction, so the filter's premise can no longer occur under the required interpreter -- removed entirely (not narrowed) from all four files and from `testsys/run.py`'s `PYTHONNOUSERSITE` re-exec (subprocess e2e runs still set `PYTHONNOUSERSITE=1` out of caution, not re-audited as part of this change). New contract test `testsys/contract/test_gate_runs_in_pinned_venv.py` gates the premise the removal rests on (`site.ENABLE_USER_SITE is False`, no `dist-packages` on `sys.path`, interpreter is 3.12); the now-obsolete narrow-filter regression test `testsys/unit/test_conftest_syspath_filter.py` was deleted rather than kept alongside a filter that no longer exists. `testsys/README.md`'s stale "Environment" section (flagged as a follow-up below) was updated in this same change rather than deferred, since it directly documents the removed workaround. `testsys/contract/test_ci_and_cli.py`'s `test_ci_workflow_pins_python_3_10` was passing only because the workflow file's own migration comment happened to contain the substring `"3.10"` -- not because it checked an actual pin; replaced with `test_ci_workflow_pins_python_3_12`, which parses the workflow YAML and checks every `actions/setup-python` step's `python-version` field directly.
    2. CI (`.github/workflows/test.yml`): the pinned `fast` job (and the opt-in `e2e-cli-smoke`/`e2e-wide-sweep` jobs) moved from `actions/setup-python@v5` 3.10 to 3.12. `fast-latest` gains `continue-on-error: true` and an explicit workflow comment that it is a non-blocking early-warning canary only (PROJECT_RULES.md rule 3c) -- it was already non-required in branch protection, this makes the job config itself say so.
    3. README.md: pinned Python 3.12 + exact pins is now stated as required, not "latest also works"; one-command `uv` setup (`~/.local/bin/uv venv --python 3.12 .venv && ~/.local/bin/uv pip install --python .venv/bin/python3.12 -r requirements.txt`). **Superseded same day by the owner ruling above**: there is no non-venv/"any Python 3.12" fallback -- the pinned, uv-managed venv is the ONLY supported path (PROJECT_RULES.md rule 3c); a bare `pip install --user` or an ad hoc venv is unsupported and untested, and `testsys/contract/test_gate_runs_in_pinned_venv.py` fails the gate rather than silently accepting it.
    4. Fixtures: `testsys/reference/v1_2_0_sweeps/v1_2_0_sweeps.json` and the `perf_v1.3.2`/`perf_v1.3.3` captured-state `.npz` fixtures were NOT regenerated -- all three were already designed to be environment-portable (the v1.2.0 invariant test's `_same()` already falls back to a wider rtol 1e-4/atol 1e-6 cross-environment tolerance off the exact pinned numpy/scipy that generated the fixture; the perf fixtures are real captured solver states compared against a reference re-implementation, not pin-specific data) and all passed unchanged on the new pins once the conftest bug above was fixed -- see "Remaining open issues" for the one thing this does NOT cover.
    5. Timing (same host, `nice -n 10`, `OMP_NUM_THREADS=1`/`OPENBLAS_NUM_THREADS=1`/`MKL_NUM_THREADS=1`, median of 3 repeats, `PIE_FAST_QUAD` unset/off, Margot fit CMR2=0.346/CMC=0.424, S, Edmund): single radius (ricb=500010 m) old 7.88 s -> new 7.66 s (~3% faster, within repeat-to-repeat noise); full ~40-radius sweep old 902.3 s -> new 810.9 s (~10% faster). Not a dedicated perf pass -- see item 27 (queued, post-item-9) for `odeRK4_snow`.
    Gate: `testsys/run.py -n 8 all` on the new `.venv-py312` (Python 3.12.15), re-run after the filter-removal override above -- see this PR's own evidence for the final count.
* v1.4.0; 20261002; minor release: new robust-runner feature (item 22), `src/` star-import narrowing (item 9) with two folded-in bug fixes (item 12), test-coverage and documentation hardening (items 23, 18, 25), one dead-file removal, one docs-only design note, and one open-issue board row. Ten PRs since v1.3.3 (`#23`-`#32`):
    1. `#23` (item 23 a,b,d): `testsys/conftest.py` error_code tautology replaced with solve-derived status (mutation-verified); Steinbruegge x S+Si anchored at the Si=0 limit; new grid-convergence (RK4 order 4.04) and hydrostatic-residual tests. Item 23(c), Fe-Si at ricb>10 m, stays open.
    2. `#24` (items 9, 12): `src/libCore.py`/`src/planet_input.py` star-imports (`from globalvar import *`, `from planet_input import *`) replaced with explicit name lists, no behaviour change (binding semantics identical). Folds in item 12's two latent-bug fixes: `get_mass_core`'s first shell term `rho[0]*r[0]**3/r[-1]**3` -> `rho[0]*(4./3.)*np.pi*r[0]**3` (dimensional consistency; harmless at real call sites, r0~1e-4*a); `reorder_el`'s S+Si branch now reads its own `chi_Si_constant` argument instead of the global `chi_Si_icb`.
    3. `#25` (item 11): evolution-mode design doc (`docs/notes/evolution_design.md`), docs-only, no `src/` change; evolution mode (`planet_input.py` `'e'` branch) stays parked and locked by its existing xfail.
    4. `#26` (item 18): bounded quantify attempt for the item-18 snow-fraction/CMR2 science-impact question (`docs/notes/item18_quantify_2026-10-01.md`); flagged UNAUDITED on landing, one arithmetic error (41%->43.6%) corrected post-audit (`c267f0d`); independent re-derivation (priya-nair, 2026-10-02) reproduced 20/21 numeric claims, one (the 474,075-row published denominator's genova half) still unverifiable pending a crashed census script -- not release-blocking, no number sent to coauthors.
    5. `#27` (item 22): new feature `src/robust_runner.py` -- CSV job manifest with explicit seeds, sentinel-file resume (fixes the legacy `monteCarlo.run.py` header-row-counts-as-done bug), per-job `ErrorCode` status, `PIE_WORKERS` cap shared with `testsys/conftest.py`, per-job provenance (git SHA/dirty flag, dependency pins vs installed, host, run id), local + TACC backends. Crash/restart proven with real-subprocess tests.
    6. `#28` (item 9): dead-file triage -- `src/test.py` and `src/main_abbey_plot.py` deleted (confirmed unreferenced, broken against current `globalvar.py`/`planet_input.py`); `src/TEST_visualization_evolution.py` confirmed NOT dead (imported by `src/drivere.py`) and kept.
    7. `#29` (item 18): regression test locking the item-18 measure36 raw counts (39/892/16-37/17-of-39/74-23-3%) against the audited JSON, mutation-verified.
    8. `#30` (item 9): `src/summaryPlot.py`/`src/visualization_present.py` star-imports narrowed to explicit names; surfaced but did not fix pre-existing `summaryPlot.py` NameError/undefined-variable bugs, opened as item 24 (routed to lars-eriksson, non-blocking).
    9. `#31` (item 24): board row only, no code change -- opens item 24 for the `summaryPlot.py` findings above.
    10. `#32` (item 25): regression test `test_get_mass_core_distinguishes_old_normalized_bug_at_finite_r0` (Mercury-sized profile, r0=30% of r_total) closing the rule-10 gap zofia-kaminska's milestone audit found in `#24`'s item-12a fix (old/new formulas diverge 5.7% at this r0; the original fixture's r0=1e-3 could not distinguish them).
    Milestone audit (2026-10-02, pre-authorization): zofia-kaminska rule-book audit + victor-reyes technical audit + priya-nair item-18 re-derivation found no release-blocking issues; two MAJOR findings (item 25's missing regression test, item 9's overstated board claim) were fixed before authorization (`#32`, `823feca`). Two non-blocking follow-ups stay open past this release: item 24 (`summaryPlot.py` bugs) and item 26 (`src/robust_runner.py`: unlocked done-check/run race, a reachable-but-unconfirmed bare `sys.exit()` at `src/main.py:124`, two rule-2 fallback patterns at `src/robust_runner.py:137-138,276-298`) -- both routed to lars-eriksson. Grant: minor release v1.4.0, owner-approved 2026-10-02, unattended-merge grant in effect for v1.x patch/minor releases. Gate: `testsys/run.py -n 0 all` (pytest-xdist 2.5.0 pinned in `testsys/requirements.txt` not installed in this environment; ran serial via `-n 0`, same test content as the default xdist path) -- 301 passed, 14 skipped, 3 xfailed, 0 failed, 1491s, fresh on the exact release tree including this CHANGELOG/CITATION bump.
* v1.5.1; 20261003; owner ruling, default-NUMERICS change: `PIE_FAST_QUAD` now defaults ON (GK21 is the default integrator for `eosAndersonGrueneisen.Gibbs`'s `scipy.integrate.quad` call); `PIE_FAST_QUAD=0` is the explicit escape hatch back to real `scipy.integrate.quad` (unset, or any value other than `"0"`, means GK21-on -- pinned truth table verified by `test_env_var_truth_table`). This changes default output on every non-pinned environment, bounded (not eliminated) at `GK21_PORTABLE_RTOL=1e-14` relative, per the pre-existing bound -- NOT bit-identical off the pinned environment, only on it. On the pinned environment (`numpy==1.21.5`, `scipy==1.8.0`) GK21 remains exactly bit-identical to real `quad` (max diff 0.0 over the same 237057-call real captured matrix as v1.3.3). Measured off-pin (this host's resolved `numpy==2.2.6`/`scipy==1.15.3`): max reldiff **0.0** over the 4000 (eos, real-call) pairs `TestGK21MatchesRealQuadBitIdentically` checks -- well inside the 1e-14 bound, but not guaranteed to reproduce on every CPU/SIMD target (see docs/notes/perf_v1.3.3.md's CI-run finding for why 0.0-on-one-host does not bound every host). `testsys/unit/test_perf_v1_3_3_gk21_quad.py`'s `TestDefaultBehaviourIsGK21On` (renamed from `TestDefaultBehaviourIsUnchanged`) replaces the old off-by-default assertions with their mirror image: default flag is `True`, and the default `Gibbs()` call path is proven to reach `_gk21_or_quad` by monkeypatching the REAL `scipy.integrate.quad` to raise if invoked (not the old opt-in-era check that `_gk21_or_quad` wasn't reached). All other differential/parity/perf tests in that file are unchanged. Gate: fresh `testsys/run.py all` on the pinned environment (committed tree, clean working copy), 301 passed, 14 skipped, 3 xfailed, 0 failed, 1156s (`-n 8` xdist); separately confirmed the off-pin (current-numpy/scipy) differential tier green (10/10 `test_perf_v1_3_3_gk21_quad.py` tests) with the max reldiff quoted above. PIE still requires the pinned environment for byte-identical guarantees; CI's `fast-latest` job remains an early-warning canary on this change. Re-gated by the conductor after rebasing onto v1.5.0 (df3ede9, py3.12/uv migration) before merge (PR #39, squash `c0d9481`): fresh `testsys/run.py all` on the rebased tree, pinned py3.12 venv -- 315 passed, 15 skipped, 3 xfailed, 0 failed, 502s (count differs from the pre-rebase 301/1156s above only because the v1.5.0 base added its own tests, e.g. `test_gate_runs_in_pinned_venv.py`; no gk21-specific test changed).
* v1.3.3; 20261001; performance: opt-in vectorised GK21 quadrature for `src/coreEos.py`'s `eosAndersonGrueneisen.Gibbs` (`scipy.integrate.quad` call), default OFF via `PIE_FAST_QUAD` (unset/0 = unchanged `quad` call on every environment). `coreEos._gk21_panel` replicates QUADPACK's `dqk21.f` 21-point Gauss-Kronrod rule vectorised (`func` called once on all 21 abscissae); `coreEos._gk21_or_quad` replicates `dqagse.f`'s single-panel accept test and falls back to real `scipy.integrate.quad` per call whenever that test fails (a per-call runtime check -- profiling + a full S/Si/S+Si x Edmund/Steinbruegge sweep found QAGSE never subdivides past the first GK21 panel for any `(p, T)` reached in a real solve, but a direct sweep over the full admissible pressure domain shows it can, so the fallback is load-bearing). Measured (pinned env, `fccFe` eos, 2000 real captured calls): quad 170.1 us/call -> gk21 40.1 us/call, 4.24x. Differential gate: pinned environment (`numpy==1.21.5`, `scipy==1.8.0`) max diff 0.0 (exact) vs real `scipy.integrate.quad` over 237057 real captured solver states; off the pinned environment (CI `fast-latest`), `eosAndersonGrueneisen.volume`'s `CubicSpline` array-call vs scalar-per-point-call is not bit-associative (~8.3e-17 absolute divergence measured on CI run 36881055265), so the port ships opt-in rather than default -- a prior attempt (PR #15, reverted as PR #16) shipped it as the default and broke `fast-latest`. Confirmed via `gh run view <id> --log` that the PR-head run (36879868704, green) and the failing merge-SHA run (36881055265, red) resolved IDENTICAL package versions (numpy==2.5.3, scipy==1.18.1, pandas==3.0.6): this is CPU/SIMD-dependent floating-point nondeterminism across ephemeral GitHub-hosted runners, not a pip-resolution difference. Test suite: `testsys/unit/test_perf_v1_3_3_gk21_quad.py` exact-equality tier on the pinned environment, portable `GK21_PORTABLE_RTOL=1e-14` relative-diff bound (reused, not reinvented, for every array-vs-scalar comparison off the pinned environment, including the volume-vectorisation precondition test). Docs: `docs/notes/perf_v1.3.3.md`. Gate: `testsys/run.py all`, see docs/notes/perf_v1.3.3.md for the exact counts on both the pinned environment and a local `fast-latest`-equivalent (pins-stripped) venv.
* v1.3.2; 20261001; performance: two dense-inverse-for-a-single-rhs call sites replaced with a direct linear solve, no algorithm/matrix change. `src/libCore.py:getpotvsr`'s `b = inv(A)*rhs` (full dense inverse of a sparse SuperLU-factored matrix for one rhs) -> `spsolve(A, rhs)`; `src/shootp.py:mynewtonSys`'s `dx = np.dot(np.linalg.inv(J), f)` -> `np.linalg.solve(J, f)`. Measured: single radius 18.37s -> 9.62s (1.91x), 40-radius sweep 1675s -> 921s (1.82x). Differential gate (`testsys/unit/test_perf_v1_3_2_linear_solves.py`, real captured solver states, pre-v1.3.2 dense-inverse kept as the reference oracle): max relative diff 0.0 (sparse case) / 5.7e-14 (dense case), both well inside the 1e-12 bound. `getk2`'s loops profiled and NOT vectorized (<0.5% of post-fix time, no measured benefit); `solver.py:odeRK4_snow` is now the dominant cost (82%) but is a sequential root-find/quadrature-dependent stepper, not a vectorizable grid loop -- a Numba JIT proposal is written up (`docs/notes/perf_v1.3.2.md`) but not implemented (new dependency, owner decision pending). Gate: `testsys/run.py all` -- 253 passed, 14 skipped, 3 xfailed, 0 failed.
* v1.3.1; 20261001; test-gate parallelism (pytest-xdist) + resumable, seeded knox local launcher. No src/ physics change -- patch. `testsys/conftest.py` adds a single `PIE_WORKERS` knob capping both xdist worker count and every in-test ProcessPoolExecutor pool (shared-machine courtesy, PROJECT_RULES.md rule 15); `testsys/run.py` gains `-n`/`--dist=loadscope`. `monteCarlo.run.py`/`TACC.LS6.create.parallel.launcher.py`/`scheduler.py` use an explicit per-line seed, `sys.executable` (not bare `python`, broken on some hosts), and skip already-completed draws on resume. Gate: `testsys/run.py all` -- 251 passed, 14 skipped, 3 xfailed, 0 failed.
* v1.3.0; 20261001; bounded line-search Newton, getk2 nrs=0 fix, continue-after-failure sweeps, failures as csv rows. Minor: results CHANGE for models that previously failed (new rows); every row that converged in v1.2.0 is bit-identical (testsys/integration/test_v1_2_0_invariant.py). Output format change: three appended csv columns and one row per attempted radius.
    1. src/shootp.py mynewtonSys: step dx = J^-1 f unchanged; alpha = 1 first, halved while the trial is outside the admissible box (non-finite, rcmb <= ricb, chi above the eutectic / Si max; no lower bound: 21.8% of published converged rows have chi < 0) or |f| grows > 100x; alpha < 1e-3 fails with the rejection's code. No Armijo test (would alter 1.4% of converged v1.2.0 steps). Singular J = cond(J) > 1e12 or LinAlgError (was exact det==0). Solver log records alpha, cond(J), every rejected trial.
    2. src/shootp.py getk2 at nrs = 0 (ricb = 10 m): fully fluid core from the centre, g(0) = 0, no inner-core term, no k+nrs-1 index wrap (bug B5); arrays zero-initialised; non-finite/non-positive rho or g raises NONFINITE_SHOOT; ricb >= rcmb (nrs >= 400) raises RICB_GE_RCMB instead of IndexError. xi = 0 exactly at 10 m, 10-m outputs unchanged.
    3. src/driverp.py sweep policy: a failed radius is recorded and the sweep continues, warm-starting from the last converged solution with one cold retry from the generic v0 (solve_radius); only code 6 ends a composition (checked once before the sweep, one row).
    4. pMetaData_<chi_Si>.csv: one row per attempted radius (failed rows: NaN physics, error_code, start, newton_iters, resid_norm); .h5 only for converged radii; globalvar.presentday_columns gains start, newton_iters, resid_norm (appended). summaryPlot.py / main.py plot / main_abbey_plot.py filter error_code == 0.
    5. testsys: v1.2.0 identity + recovered-row validity gate (fixture testsys/reference/v1_2_0_sweeps/ from 18cf78a), line-search/box/getk2 unit tests, sweep-policy unit tests, failed-row e2e checks; published-wide B5 flake allowance removed (hard gate, board item 19); "golden non-convergent, fresh converges" is now a validity-gated recovery, not a failure.
    6. docs: README Solver section; docs/notes/solver_v1.3.0.md (design, invariant, recovery statistics with CIs, runtime).
* v1.2.0; 20260930; failures are recorded instead of silently dropped. Converged outputs unchanged (all published-parity tests identical); output additions only.
    1. No more sys.exit() or uncaught crashes in the present-day solve: mynewtonSys and shoot_mercmodel raise SolverError; driverp.py records it per radius and stops that sweep at the same point as before (bugs B1, B2).
    2. error_code column now meaningful (schema unchanged): 0 converged, 1 Newton maxit, 2 singular Jacobian, 3 non-finite shoot (NaN, SuperLU singular, getk2 index), 4 chi outside admissible range, 5 ricb >= rcmb, 6 Si above liquidus max (by design). Previously always 0. Restored the discarded err flag and the (chi_li<0).any() check (B3).
    3. New per-run structured solver log solverLog_<chi_Si>.jsonl next to the pMetaData csv: Newton iterations and failure context (item 15).
    4. Dependencies: root requirements.txt with exact pins, contract test keeping it equal to testsys/requirements.txt; rule 3b (exact pins).
    5. testsys: truth anchors (homogeneous sphere, S+Si limits, Margot fit, liquidus table) and v1.0.3 regression history; placeholder for Steinbruegge et al. 2020 values.
    6. docs: README launcher filename fixed; Steinbruegge code assessed as an independent anchor (docs/notes/steinbruegge_anchor_2026-09-30.md).
* v1.1.1; 20260929; scipy compatibility patch. Converged outputs unchanged.
    1. Port src/coreEos.py meltingDataFromFile from scipy interp2d (removed in scipy 1.14) to RectBivariateSpline(kx=3, ky=3, s=0): same FITPACK fit and evaluation, bit-for-bit on the pinned environment (testsys/unit/test_melting_interp_port.py).
    2. CI: new fast-latest job on Python 3.12 with current numpy/scipy (pins stripped); pinned job unchanged.
    3. Contract test: src/ must not use interp2d (replaces the interp2d canary).
* v1.1.0; 20260929; first tested baseline. src/ physics code byte-identical to v1.0.5 (the code archived for Dunnigan et al. 2026, JGR Planets, doi:10.1029/2025JE009368).
    1. Add testsys/: unit, contract, integration, e2e tiers; parity vs published Zenodo v1.0.5 output (10.5281/zenodo.16459292) for S, Si, S+Si; full radial-profile guards; runner testsys/run.py.
    2. Add CI (.github/workflows/test.yml): fast tiers on push/PR, e2e weekly and on demand.
    3. Add CITATION.cff and README citation; PROJECT_RULES.md, PATHWAY_FORWARD.md, CLAUDE.md.
    4. Move src/VERSION to CHANGELOG.md (git tags = version source of truth); pin CI requirements (scipy 1.8.0: interp2d removed in 1.14).
    5. Add docs/notes/failure_analysis_2026-09-28.md and docs/audits/: solver-failure analysis and audits (fixes scheduled for v1.1.1).
* v1.0.5; 20250708; publication release (all changes since v1.0.4 tag, 20230214)
    1. Add read_plot_datah5.py, which will read and plot *data.h5 results. For Hao's calculation of BV frequency. (20230403)
    2. Use eos.liquidNonIdaFeS; take alpha and C_p from eos function. (20230607)
    3. Add Monte Carlo wrapper for CMR2 (monteCarlo.run.py). (20250122)
    4. Add S mass calculation in driverp and shootp. (20250225)
    5. Fix missing pi in get_mass_core; fix missing column head for chi_S_bulk. (20250303)
    6. Fix iron snow layer classification to include 3 for deep snow+layers. (20250707)
    7. Merge 1.0.4.dev into src; rename TACC LS6 launcher/slurm scripts; remove runAll.sh. (20250707)
* v1.0.4; 20230127; 
	1. explore CMR2 and CmC parameter space.
	2. Add scheduler.py to run models over the CMR2, CMC, liquidus equation,  light element, and Si%wt parameter space.
	3. Generate as many models as possible and discard models negative light element weight ones at the end. 
	
* v1.0.3 committed on 20221026 and zipped under D:\3.Krista_Soderlund\GitHub\Committed_Mercury_present_evolution\Mercury_present_evolution_v1.0.3_committed_20221026