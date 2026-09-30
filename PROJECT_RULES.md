# PIE Project Rules

Index — read this list first; jump to a rule only when it's load-bearing.

1. Minimal changes; no new files until necessary — and a curated root.
1a. Git tags are the version source of truth; `CHANGELOG.md` holds the change list.
2. No silent fallbacks, swallowed errors, or placeholder data.
3. Gate every stage; pass before moving on.
3a. A refactor of `src/` runs testsys green before and after, one module at a time.
3b. Every dependency manifest pins exact versions; a pin change ships with a green `testsys/run.py all`.
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
14. Every paper that uses PIE output records its Zenodo DOIs and a matching git tag.

---

## 1. Minimal changes; no new files until necessary — and a curated root

Smallest edit that solves the problem; fold content into the file it belongs
to; never refactor unrelated code in the same change.

The root is a whitelist: `README.md`, `CLAUDE.md`, `PATHWAY_FORWARD.md`,
`PROJECT_RULES.md`, `LICENSE`, `CITATION.cff` (see rule 14), `CHANGELOG.md` (rule 1a), `update_log` (frozen, see 1a), plus
`src/`, `historical_versions/` (frozen zips/tars of prior versions, read-only —
see rule 7), `testsys/` and `.github/` (owned by the testing effort, out of
scope for this rule book's own writer). `results/` is a run artifact, not
tracked (README's `mkdir results` step). No new top-level `.md`/notes files —
a session's own working notes go in `docs/notes/` (create the directory only
when the first note needs it).

**Rationale**: this project has no root-structure rule today and no `docs/`
directory; this proposes the boundary before the root accumulates
`NOTES_*.md`/`STATUS_*.md` files the way sibling projects (EQdyna) did before
they had one.

**How to apply**: before adding any new root-level file, ask whether it
belongs in `src/`, `docs/notes/`, or one of the four named documents instead.

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
libCore import *`, `from planet_input import *` (six files:
`main.py`, `drivere.py`, `driverp.py`, `shoote.py`, `shootp.py`,
`main_abbey_plot.py`, `summaryPlot.py`, `visualization_evolution.py`,
`visualization_present.py`, `libCore.py` itself, `test.py`,
`TEST_visualization_evolution.py`), plus known-dead/scratch files
(`src/test.py`, `src/TEST_visualization_evolution.py`,
`src/main_abbey_plot.py`) and a flat layout with no package structure. Fixing
any of this without a gate that can actually observe a broken numerical
result is exactly how a star-import removal silently drops a name one file
depended on.

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
in the same commit/PR, not a follow-up.

**Rationale**: `testsys/requirements.txt` already did this by convention
(all exact pins) with no rule saying so.

**Incident**: PR #3 (unmerged) initially added a root `requirements.txt` with
unpinned lines; caught in review before merge, not by any gate.

**How to apply**: `testsys/contract/test_dependency_pins_match.py` (added in
PR #3) is the mechanical enforcement — fails on an unpinned line in any
manifest, or on root and `testsys/` disagreeing about a shared package's
version.

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
merge SHA; add a `CHANGELOG.md` entry and bump `CITATION.cff` `version:` (in the PR); annotated tag `vX.Y.Z` on
the merge SHA; `gh release create vX.Y.Z --verify-tag --latest`. State the
grant (who authorised the release, when) in the PR. `v1.0.5` is tagged on
`683a51d`, the exact code archived for Dunnigan et al. 2026 (rule 14);
`v1.1.0` is the first tested baseline.
`v1.0.2`/`v1.0.3` were never tagged in git — do not retroactively tag them;
treat their zipped/tarred copies as historical record only (rule 7).

**How to apply**: do not tag ahead of a green testsys run; do not skip the
GitHub release step after tagging.

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

