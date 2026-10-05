# PIE Project Rules

Index — read this list first; jump to a rule only when it's load-bearing.

1. Minimal changes; no new files until necessary — and a curated root.
1a. Git tags are the version source of truth; `CHANGELOG.md` holds the change list.
2. No silent fallbacks, swallowed errors, or placeholder data.
3. Gate every stage; pass before moving on.
3a. A refactor of `src/` runs testsys green before and after, one module at a time.
3b. Every dependency manifest pins exact versions; a pin change ships with a green `testsys/run.py all`.
3c. The pinned dependency manifest is the one supported environment; unpinned is a canary, never a gate.
4. Only fresh runs are evidence.
5. One calibrated definition of "pass" — never invent a metric.
6. Every result carries its provenance.
7. Reference data is read-only.
8. Never delete evidence unless the result is a confirmed pass.
9. Cheap targeted check before expensive run.
10. Every bug gets a regression test before the fix ships.
11. Docs move with the code, in the same change.
12. A living status board, prioritised and re-checked on a schedule.
13. Land through one gated PR at a time; release in one sequence; state the grant.
13a. The stranger-clone check runs in an isolated, from-scratch environment.
14. Every paper that uses PIE output records its Zenodo DOIs and a matching git tag.
15. Shared machines: cap PIE's parallelism to leave headroom for others.
16. An audit confirms the question and population, not just the arithmetic.

---

## 1. Minimal changes; no new files until necessary — and a curated root

Smallest edit that solves the problem; fold content into the file it belongs
to; never refactor unrelated code in the same change.

The root is a whitelist: `README.md`, `CLAUDE.md`, `PATHWAY_FORWARD.md`,
`PROJECT_RULES.md`, `LICENSE`, `CITATION.cff` (see rule 14), `CHANGELOG.md` (rule 1a), `update_log` (frozen, see 1a),
`pyproject.toml` (board item 28e: packaging + the pinned deps that must
agree with `requirements.txt`, rule 3b), plus
`pie/` (the installable package; renamed from `src/` by board item 28e —
same role, same rules below that still say `src/` in older prose), `util/`
(operational scripts split out of `src/` by the Layout PR,
board item 28 — `util/plot/`, `util/run/`; relocation of existing scripts, not
new scope, and no physics code), `historical_versions/` (frozen zips/tars of prior versions, read-only —
see rule 7), `testsys/` and `.github/` (in scope for this project like `pie/`
— CI config and the test suite, maintained by whoever is doing the current
campaign work; no separate team owns them). `results/` is a run artifact, not
tracked (README's `mkdir results` step). No new top-level `.md`/notes files —
a session's own working notes go in `docs/notes/` (create the directory only
when the first note needs it).

**Rationale**: this project has no root-structure rule today and no `docs/`
directory; this proposes the boundary before the root accumulates
`NOTES_*.md`/`STATUS_*.md` files the way sibling projects (EQdyna) did before
they had one.

**How to apply**: before adding any new root-level file, ask whether it
belongs in `pie/`, `docs/notes/`, or one of the four named documents instead.

---

## 1a. Git tags are the version source of truth; `CHANGELOG.md` holds the change list

The released version is the annotated git tag `vX.Y.Z` (and its GitHub
release). `CHANGELOG.md` at the root carries the per-release change list, and
`CITATION.cff` `version:` is bumped in the same release PR. There is no
version file inside `src/`: release bookkeeping must never touch the physics
code tree, so `src/` can be compared byte-for-byte with an archived release
(e.g. Zenodo 10.5281/zenodo.16929504). `update_log` is the pre-v1.0.5
development log, frozen: kept for history, never deleted, no new entries.

**Incident**: `src/VERSION` (removed in v1.1.0, history moved to
`CHANGELOG.md`) disagreed with `update_log` on the v1.0.5 entry, and editing it
for a release tripped the `src/`-unmodified contract test and blurred the
"src/ == published code" check. v1.0.2 and v1.0.3 were never tagged (only
zipped externally, `historical_versions/`); don't tag them retroactively.

**How to apply**: each release PR adds a dated `CHANGELOG.md` entry and bumps
`CITATION.cff` `version:`; the tag is created after merge (rule 13).
`update_log` gets no entries dated after 20250708.

---

## 2. No silent fallbacks, swallowed errors, or placeholder data

Missing input, config, or a failed comparison fails loudly and immediately.
No substituted default, no skipped step, no stub that looks valid.

**Rationale**: `src/coreEos.py:...get_mass_core` shipped for months missing a
factor of `pi` in a volume/mass integral — no error, no warning, a
plausible-looking wrong number, fixed only at `bb37b0a` (v1.0.5). A silent
numerical placeholder is exactly the failure mode this rule exists to
prevent, and it survived because nothing compared the function's output
against an analytical bound (rule 6/the truth anchors on the board).

**How to apply**: any physical quantity computed from a formula that has an
independent closed-form check (a sphere volume, a homogeneous-body CMR2 of
0.4, a liquidus limit) gets that check run against it, and a mismatch raises,
it does not print and continue.

---

## 3. Gate every stage; pass before moving on

Named command: `/usr/bin/python3 testsys/run.py` (fast tiers: unit /
contract / integration, the CI gate on every push and PR) and
`testsys/run.py all` (adds e2e, including the `published_wide` sweep that
needs `~/shared_dataset`). Landed in v1.1.0. A stage is "gated" only when the
named command was run and its pass/fail counts are quoted.

Environment: `/usr/bin/python3`, not the `python3` first on `PATH` (a venv
missing `h5py`). No conda for this project.

**Rationale**: PIE has never had an automated test — every prior "it works"
claim rests on eyeballing plots or comparing a Monte Carlo run's shape to
expectation. That is the gap `testsys/` exists to close.

**How to apply**: once `testsys/run.py all` exists, a change does not merge
until it exits with every tier's cases passing (unit/contract green always;
integration/e2e per the matrix that effort defines). Until then, state
explicitly in a PR or commit what was actually run by hand.

---

## 3a. A refactor of `src/` runs testsys green before and after, one module at a time

A refactor — deduplicating star imports, splitting `libCore.py`, deleting a
dead file — is gated on `testsys/run.py` (all tiers) passing on the
pre-refactor tree, then again on the post-refactor tree, for each module
touched, before moving to the next. A refactor landed while testsys is not
yet green, or landed across multiple modules in one change with the gate run
only at the end, is not verified — it is asserted.

**Rationale**: `src/` today imports by `from globalvar import *`, `from
libCore import *`, `from planet_input import *` (files:
`main.py`, `drivere.py`, `driverp.py`, `shoote.py`, `shootp.py`,
`summaryPlot.py`, `visualization_evolution.py`,
`visualization_present.py`, `libCore.py` itself,
`TEST_visualization_evolution.py`) and a flat layout with no package
structure. (`src/test.py` and `src/main_abbey_plot.py`, formerly listed here
as dead/scratch files, were confirmed unreferenced and broken on current
`src/` and deleted in item 9's dead-file triage slice;
`TEST_visualization_evolution.py` was confirmed NOT dead — `src/drivere.py`
imports it — so it stays, pending the same star-import cleanup as the rest
of this list.) Fixing any of this without a gate that can actually observe a
broken numerical result is exactly how a star-import removal silently drops
a name one file depended on.

**How to apply**: `testsys/run.py all` (or the closest tier that exists at
the time) is run and recorded green immediately before the refactor starts
and immediately after each module's change lands, output pasted into the PR
or commit message. This rule is blocked on testsys existing at all — see
`PATHWAY_FORWARD.md` item 1 and item 9.

**Tier**: unenforceable as a mechanical gate until `testsys/run.py` exists;
a norm until then.

---

## 3b. Every dependency manifest pins exact versions; a pin change ships with a green `testsys/run.py all`

Every Python dependency manifest in this repo — `requirements.txt`,
`testsys/requirements.txt`, and any future one — pins exact versions
(`pkg==x.y.z`); no ranges, no unpinned lines. Changing a pin ships together
with a green `/usr/bin/python3 testsys/run.py all` run under the new version,
in the same commit/PR, not a follow-up — and, for anything bitwise/tolerance-
sensitive (rule 5's regression anchors, Monte Carlo output), a documented
numeric diff between the old-pin and new-pin runs, not just a pass/fail count.
Only once both land does the new pin set become the one supported
environment rule 3c requires.

**Rationale**: `testsys/requirements.txt` already did this by convention
(all exact pins) with no rule saying so.

**Incident**: PR #3 (unmerged) initially added a root `requirements.txt` with
unpinned lines; caught in review before merge, not by any gate.

**How to apply**: `testsys/contract/test_dependency_pins_match.py` (added in
PR #3) is the mechanical enforcement — fails on an unpinned line in any
manifest, or on root and `testsys/` disagreeing about a shared package's
version.

---

## 3c. The pinned dependency manifest is the one supported environment; unpinned is a canary, never a gate

Rule 3b's manifests (`requirements.txt`, `testsys/requirements.txt`, kept in
lockstep) define THE supported environment for PIE — there is exactly one.
An unpinned or "latest-package" install is not a lighter-weight alternative a
contributor can expect to work; it is explicitly unsupported. Any CI job that
installs against unpinned or newer-than-pinned dependencies (e.g.
`fast-latest`) exists only as an early-warning canary: it must be configured
non-blocking (its failure does not gate merge or release) and must say so in
its own workflow comment. Replacing the pin set itself follows rule 3b's own
gate — the full test tier green on the new pins plus the documented old-vs-new
numeric diff — not a lighter bar because an unpinned job happened to pass.

**Rationale**: an unpinned environment passing is evidence the code tolerates
whatever versions happened to resolve today, not evidence the supported
environment works — conflating the two turns a canary into a second,
uncalibrated gate (rule 5).

**Incident (2026-10-02)**: a mid-campaign request asked to validate both a
pinned and an unpinned/pins-stripped environment for the same PR, then was
reversed by the project owner specifically because PIE does not support
unpinned environments — the ambiguity this rule closes so it isn't
re-litigated next time.

**How to apply**: a CI job touching unpinned/newer dependencies carries a
leading comment stating it is a non-blocking canary and is not listed as a
required check in branch protection; a PR or release is never blocked, held,
or re-scoped on that job's result.

---

## 4. Only fresh runs are evidence

A number in `README.md`, `CHANGELOG.md`, or a prior session's summary is a
hypothesis until reproduced on the current `src/` and the SHA it's attached
to. Be most skeptical of "already fixed" — v1.0.3/v1.0.4 both predate the
`bb37b0a` pi fix and are known to contain it.

**How to apply**: before citing an old run's output as ground truth (rule 7's
regression anchors, item 2 on the board), state explicitly that it is
untested legacy code, not verified truth.

---

## 5. One calibrated definition of "pass" — never invent a metric

This project has two different classes of comparison and they are not
interchangeable:

- **Regression anchors** (old PIE versions, S-only/Si-only endmembers):
  pass means numeric parity with the old code's own output, within a stated
  tolerance — evidence of no unintended behaviour change, not evidence of
  correctness.
- **Truth anchors** (analytical limits, Steinbruegge et al. 2020, Margot
  CMR2/CMC fit, published liquidus data): pass means agreement with an
  independently-derived value.

A result that only passes a regression anchor may not be reported as
"verified correct" — say "matches the untested prior version" instead.

**How to apply**: name which class of comparison produced a "pass" claim in
the same sentence as the claim.

---

## 6. Every result carries its provenance

Any number cited outside the repo (a CMR2/CMC fit, a core radius, a
liquidus-derived light-element fraction) records the git SHA and the input
parameters (CMR2, CMC, light-element choice, Si%wt) that produced it.

**How to apply**: `git rev-parse --short HEAD` next to any number quoted in a
report or plot caption.

---

## 7. Reference data is read-only

`historical_versions/` and the external oracle trees this project cites
(`~/3.Krista_Soderlund/MercuryInterior_MonteCarlo/dliu_20221021_v1.0.3/`,
`~/3.Krista_Soderlund/MercuryEvolution/Mercury_present_evolution_v1.0.4_20230127/`)
are ground truth for regression comparison only (rule 5) — nothing writes
through them, ever, including "just to patch the known pi bug for a cleaner
comparison." If a comparison needs the bug fixed, fix it in a copy.

**How to apply**: run regression anchors by invoking those trees' own
interpreters/scripts read-only; never edit them in place.

---

## 8. Never delete evidence unless the result is a confirmed pass

A failed comparison's output (a diverging CMR2 fit, a NaN light-element
fraction) is the only record of what happened. Keep it until root-caused.

---

## 9. Cheap targeted check before expensive run

Before a large Monte Carlo ensemble (`TACC.LS6.create.parallel.launcher.py` +
`sbatch`), run the single-case path (`scheduler.py CMR2 CMC`) and the
analytical-limit checks (rule 6 truth anchors) locally first.

---

## 10. Every bug gets a regression test before the fix ships

**Rationale**: the `bb37b0a` pi fix and the iron-snow layer classification
fix (`2a9d576`) both shipped with no accompanying test — nothing in the repo
would catch either regressing.

**How to apply**: once `testsys/` exists, a fix to `src/*.py` that isn't
covered by an existing case adds one in the same change, not a follow-up.
Until then, state explicitly in the commit what manual check was run.

---

## 11. Docs move with the code, in the same change

A file rename or removal updates every reference to it in `README.md`,
`CLAUDE.md`, and `CHANGELOG.md` in the same commit.

**Rationale**: `README.md:32` still reads `python TACC.create.parallel.launcher.py`;
the file is `src/TACC.LS6.create.parallel.launcher.py` — renamed without the
doc following (commit `1ac69a7`/`171d799`, "rename folders for clarity").

**How to apply**: `grep` every renamed filename against `README.md` and
`CLAUDE.md` before committing a rename.

---

## 12. A living status board, prioritised and re-checked on a schedule

`PATHWAY_FORWARD.md` at the repo root records every open issue, to-do, and
standing claim, each with a priority (P1/P2/P3), a re-check interval, the
date last checked, and the exact command whose output was read. No
`TODO.md`/`STATUS.md`/`BACKLOG.md` anywhere in the tree — this project has
none today; keep it that way.

**How to apply**: `git ls-files | grep -iE '(TODO|STATUS|ROADMAP|BACKLOG|TASKS|PLAN)\.(md|txt)$'`
must come back empty (excluding `historical_versions/`'s frozen archives,
which are not tracked as extracted files).

---

## 13. Land through one gated PR at a time; release in one sequence; state the grant

Release sequence: one PR per release; `testsys/run.py all` green locally,
counts pasted in the PR; green CI on the PR head; merge; green CI on the
merge SHA; add a `CHANGELOG.md` entry and bump `CITATION.cff` `version:` (in the PR); a stranger-clone
verification (rule 13a) must have written and the release agent must have
read back a `clone: PASS <sha>` line before the next step is taken; only then
annotated tag `vX.Y.Z` on the merge SHA; `gh release create vX.Y.Z
--verify-tag --latest`. State the grant (who authorised the release, when) in
the PR. `v1.0.5` is tagged on `683a51d`, the exact code archived for
Dunnigan et al. 2026 (rule 14); `v1.1.0` is the first tested baseline.
`v1.0.2`/`v1.0.3` were never tagged in git — do not retroactively tag them;
treat their zipped/tarred copies as historical record only (rule 7).

**How to apply**: do not tag ahead of a green testsys run; do not skip the
GitHub release step after tagging.

**Incident (2026-10-02, v1.4.0)**: the release agent launched the
stranger-clone verification (clone fresh, follow README, run the documented
first command) in the background, then created the annotated tag and ran
`gh release create` while that clone was still running — it later checked in
and found the clone had in fact passed, but the tag and release predated the
confirmation. A release is not gated by a check that is merely running; it is
gated by a check whose result has been read.

### 13a. The stranger-clone check runs in an isolated, from-scratch environment

The clone-verification step (rule 13) must build its own virtualenv from the
repo's dependency manifest inside the fresh clone, under `env -i` (or
equivalent: no inherited `PATH`/`PYTHONPATH`/site-packages from the invoking
shell), never reuse packages already installed in the ambient shell. It must
record the dependency versions actually resolved and diff them against the
pinned manifest (rule 3b) as part of its pass/fail evidence, and it must write
the literal log line `clone: PASS <sha>` on success or `clone: FAIL <reason>`
on failure — this is the line rule 13 requires the release agent to read back
before tagging. No tag or `gh release create` runs until that line exists and
has been read.

**Incident (2026-10-02, v1.4.0)**: the clone-verification step ran in the
invoking shell and resolved h5py 3.12.1 from the host's already-installed
packages, not the pinned h5py 3.6.0 in `requirements.txt` — so it proved the
host's ambient packages happen to work, not that a bare clone following the
README actually produces a working environment. That is the entire point of
the stranger-clone gate, and an ambient-shell clone cannot prove it.

**How to apply**: the clone step's evidence block names the venv path, the
`env -i` invocation, the resolved vs. pinned versions, and the `clone:
PASS|FAIL` line, pasted into the release PR.

---

## 14. Every paper that uses PIE output is citable from the repo

Each publication built on PIE output gets its paper DOI, Zenodo code DOI and
Zenodo data DOI recorded in `CITATION.cff` (paper as `preferred-citation`,
archives under `references`) and in the README's Citation section, plus a git
tag on the exact code that produced the archived data.

**Incident**: Dunnigan et al. 2026, JGR Planets 131(4) e2025JE009368
(doi:10.1029/2025JE009368) published code (10.5281/zenodo.16929504) and data
(10.5281/zenodo.16459292) from v1.0.5, but the repo carried no citation and
no v1.0.5 tag.

**How to apply**: `grep -c 10.1029/2025JE009368 CITATION.cff README.md` is
non-zero for both; each paper's code DOI maps to a tag (`git tag`).

---

## 15. Shared machines: cap PIE's parallelism to leave headroom for others

Shared machines: cap PIE's parallelism to leave headroom for others
(PIE_WORKERS default max(4, ⌊free cores/2⌋), nice 10, one BLAS thread per
worker); never signal, renice or kill a process PIE didn't start; long runs
are resumable and stop cleanly; check `uptime`/`who` before a large run.

**Rationale**: moving testsys from serial to pytest-xdist + ProcessPoolExecutor
pools on knox (a shared 64-core box also running other users' ML training
jobs) first ran xdist at `-n` equal to the full `PIE_WORKERS` budget, which
collapsed every in-test pool down to 1 worker — safe with respect to not
overloading the shared box, but it silently erased the whole speedup. This is
a correctness/safety rule about shared-machine courtesy, not a performance
rule.

**How to apply**: `testsys/conftest.py`'s `pie_workers()`/`pool_workers()`
is the enforcement mechanism — it derives the single `PIE_WORKERS` cap that
both xdist and every in-test process pool read, so the two never double up.
The knox `xargs` launcher recipe in README's "Large ensemble Monte Carlo
simulation" section is the other consumer of the same knob.

---

## 16. An audit confirms the question and population, not just the arithmetic

Before signing off a quantitative or verification claim, an auditor restates
(a) the exact population/subset the claim is drawn from and (b) the exact
question being answered, and confirms both match what the task brief
actually asked — not just that the arithmetic inside the stated check is
correct. A claim can be computed exactly right and still answer a question
nobody asked.

**Rationale**: a check that is internally consistent can still be checking
the wrong thing; verifying its arithmetic gives false confidence that the
headline is right.

**Incident (2026-10-04)**: item 31's pilot (PR #79) verifier omitted
`pie/driverp.py:287-288`'s post-convergence `chi>=0` check; lars-eriksson's
and priya-nair's audits passed the verifier's fidelity and count arithmetic
without noticing it was missing a production check entirely — the headline
reversed from "HEAD-over-constrains" to "undetermined" once caught. Days
later, item 31c (PR #85) ran its `sort_models` filter check against HEAD's
own all-NaN failed-row diagnostics instead of v1.0.5's published row — both
audits again passed the check's internal consistency without noticing it was
answering the wrong question.

**How to apply**: an audit sign-off states, in one line each, the population
the check ran over and the question the task brief asked, before stating the
check passed. If either line can't be written, the audit is incomplete, not
passing.

