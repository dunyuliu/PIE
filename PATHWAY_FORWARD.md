# Pathway forward

Present tense: open issues, to-dos, and standing claims for PIE. Close an
item by editing its State, not by deleting the row, until it is truly done —
then it may be removed. Re-prioritise by editing the Priority column; that is
expected maintenance, not a rewrite (`PROJECT_RULES.md` rule 12).

Seeded 2026-09-28. `src/` has never had automated tests; every priority below
follows from that one fact.

| # | Priority | Item | State | Command (evidence) | Last checked |
|---|---|---|---|---|---|
| 1 | P1 | Build tiered `testsys/` (unit/contract/integration/e2e) + CI. This codebase has never been rigorously tested. Owned by a concurrent, separate effort — do not build it from this working context. | in progress | `ls testsys/run.py testsys/reference/ .github/workflows/test.yml` (exists once landed) | 2026-09-28 |
| 2 | P1 | Regression anchors: parity vs prior PIE output, S-only, Si-only, **and S+Si**. Primary anchor: the Zenodo dataset (10.5281/zenodo.16459292) for Dunnigan et al. 2026 JGR Planets (doi:10.1029/2025JE009368), produced by this v1.0.5 code — published code 10.5281/zenodo.16929504 is identical to current HEAD `src/`, so this anchor is same-code, not cross-version. Secondary anchors: v1.0.3 (`/home/utig5/dliu/3.Krista_Soderlund/MercuryInterior_MonteCarlo/dliu_20221021_v1.0.3/`), v1.0.4 (`/home/utig5/dliu/3.Krista_Soderlund/MercuryEvolution/Mercury_present_evolution_v1.0.4_20230127/`), v1.0.0 zip in `historical_versions/` — S-only/Si-only only, and known to contain since-fixed bugs (missing `pi` in `get_mass_core`, fixed `bb37b0a`). | blocked on item 1 | (none yet — testsys/reference/ will define it) | never |
| 3 | P1 | Truth anchors (independent correctness): homogeneous-sphere CMR2=0.4 limit; S+Si with Si→0 == S case, S→0 == Si case; reproduce Steinbruegge et al. 2020 (doi 10.1029/2020GL089895, predecessor repo github.com/gregorsteinbruegge/MercuryInterior) published values; Margot CMR2=0.346/CMC=0.424 fit; published Fe-S/Fe-Si liquidus data behind `src/coreEos.py`. Note: the Zenodo/Dunnigan anchor (item 2) is a regression anchor, same-code — it is not an independent truth oracle for S+Si; that gap stands. | blocked on item 1 | (none yet) | never |
| 4 | P2 | S+Si is no longer "no oracle" — the Zenodo/Dunnigan dataset (item 2) now covers it as a regression anchor. Still no independent *truth* oracle for S+Si (see item 3's note); state that distinction wherever S+Si results are reported. | open, standing caveat | n/a (documentation caveat, see `CLAUDE.md`) | 2026-09-28 |
| 5 | P1 | Triage and fix bugs `testsys` surfaces (xfail'd tests). | blocked on item 1 | (none yet) | never |
| 6 | P1 | Push `387d6e6`, then tag + GitHub-release v1.0.5, once `testsys` and CI are green. Do not tag ahead of green CI (`PROJECT_RULES.md` rule 13). | blocked on items 1, 5 | `git log origin/main..main` (non-empty until pushed); `git tag` (no v1.0.5 yet) | 2026-09-28 |
| 7 | P3 | README drift: `README.md:32` says `python TACC.create.parallel.launcher.py`, file is `src/TACC.LS6.create.parallel.launcher.py`; `README.md:24` `mkdir results` requirement (accurate but easy to miss); audit remaining README vs code for typos. Route: sophia-okafor (doc-vs-code drift), not fixed here. | open | `grep -n "TACC.create.parallel.launcher.py" README.md` (should read the corrected filename once fixed) | 2026-09-28 |
| 8 | P2 | Dependency manifest — none exists. Known runtime deps: numpy, scipy, pandas, matplotlib, h5py. `/usr/bin/python3` (not the default `python3` on PATH, which is a venv missing h5py) is the interpreter to target. | open | `ls requirements.txt pyproject.toml environment.yml 2>/dev/null` (empty today) | 2026-09-28 |
| 9 | P2 | Refactor `src/` once `testsys` is green — blocked by item 1. Every refactor change keeps all tiers green (bit/tolerance-identical vs `testsys/reference/`), one module at a time (`PROJECT_RULES.md` rule 3a). Known targets: star-imports (`from globalvar import *`, `from libCore import *`, six-plus files), duplicated imports, dead/scratch files (`src/test.py`, `TEST_visualization_evolution.py`, `main_abbey_plot.py`), flat `src/` layout. | blocked on item 1 | `grep -rln "import \*" src/*.py \| wc -l` (10 files as of 2026-09-28) | 2026-09-28 |
| 10 | P1 | Cite Dunnigan et al. 2026 (doi:10.1029/2025JE009368) + Zenodo code/data DOIs in `CITATION.cff`, README Citation section, and GitHub repo description (`PROJECT_RULES.md` rule 14). | done (lead) | `grep -c 2025JE009368 CITATION.cff README.md`; `gh repo view dunyuliu/PIE --json description` | 2026-09-28 |

## Known open, not queued

- v1.0.2/v1.0.3 were never tagged in git; only zipped/tarred externally
  (`historical_versions/`, and the two `3.Krista_Soderlund` trees). Do not
  retroactively tag them — treat as historical record only.
- `update_log` and `src/VERSION` disagreed on the v1.0.5 entry until commit
  `387d6e6` (unpushed) fixed it — see `PROJECT_RULES.md` rule 1a.
