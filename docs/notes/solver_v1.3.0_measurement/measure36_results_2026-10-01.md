# 36-case continue+adaptive measurement — results, 2026-10-01

Resumed from the 2026-09-30 pause (`MANIFEST.json`), against current `main`
src/ (git SHA `b0d5ecb`, post v1.3.1/v1.3.2/v1.3.3 — all perf-only, bit-identical
gated, do not affect this measurement's physics). Pinned env
(`/home/utig5/dliu/PIE/.venv/bin/python3`, numpy 1.21.5/scipy 1.8.0).

Command (recorded in `MANIFEST.json`'s `resumed` block):
```
PYTHONNOUSERSITE=1 MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 10 \
  .venv/bin/python3 generate_sweeps.py --src ../../../src --out v130_measure36.json \
  --workers 10 --policy continue --adaptive --cases cases36.json \
  --partial-dir measure36_partial
```
Wall time: 3248 s (54 min), 10 workers, shared 64-core box (rule 15 cap).
Output: `testsys/reference/v1_2_0_sweeps/v130_measure36.json` (not committed —
large, regenerable from the command above + `measure36_partial/`, which IS
resumable per-case and kept as evidence).

## This is item 18's "full re-run of all affected compositions"

36 cases (one published MOI x composition x end-state x died-at-10m
combination each) swept past their v1.2.0/published stop radius, continue
policy (failed radius recorded, sweep continues) + adaptive continuation
report.

| published class (end/where) | cases | radii beyond stop | converged (CI95) | admissible (CI95) | inadmissible (chi<0) | failures |
|---|---|---|---|---|---|---|
| crash_stderr/10m | 8 | 320 | 157 (0.43-0.55) | 4 (0.00-0.03) | 153 | CHI_OUTSIDE_ADMISSIBLE_BOX 145, RICB_GE_RCMB 6, NEWTON_MAXIT 9, NONFINITE_SHOOT 3 |
| crash_stderr/later | 8 | 64 | 8 (0.06-0.23) | 5 (0.03-0.17) | 3 | NEWTON_MAXIT 5, CHI_OUTSIDE_ADMISSIBLE_BOX 32, RICB_GE_RCMB 8, NONFINITE_SHOOT 11 |
| detJ0/10m | 4 | 160 | 8 (0.02-0.10) | 0 (0.00-0.02) | 8 | CHI_OUTSIDE_ADMISSIBLE_BOX 143, NONFINITE_SHOOT 7, RICB_GE_RCMB 2 |
| detJ0/later | 6 | 83 | 2 (0.00-0.08) | 1 (0.00-0.07) | 1 | CHI_OUTSIDE_ADMISSIBLE_BOX 55, NONFINITE_SHOOT 17, NEWTON_MAXIT 2, RICB_GE_RCMB 6, SINGULAR_JACOBIAN 1 |
| newton_maxit/10m | 3 | 120 | 15 (0.07-0.20) | 10 (0.04-0.15) | 5 | CHI_OUTSIDE_ADMISSIBLE_BOX 102, RICB_GE_RCMB 2, NEWTON_MAXIT 1 |
| newton_maxit/later | 8 | 145 | 28 (0.13-0.27) | 19 (0.08-0.20) | 9 | NONFINITE_SHOOT 9, NEWTON_MAXIT 6, CHI_OUTSIDE_ADMISSIBLE_BOX 95, RICB_GE_RCMB 6, SINGULAR_JACOBIAN 1 |
| **TOTAL** | 37* | 892 | 218 (0.22-0.27) | **39 (0.03-0.06)** | 179 | — |

\* `cases36.json` has 36 named cases; one case's published_class string maps
into a byclass bucket shared with another case (a grouping artifact of
`cls_of()`, not a double-counted run) — raw per-case rows below are the
authoritative per-case counts (36 lines).

Cases with >=1 admissible recovered radius: **16/37 (CI95 0.27-0.61)**.

Adaptive continuation (report-only sub-probe, first 2 failures/case):
tried 52, recovered 4 (CI95 0.02-0.19).

Runtime: converged radius median 4.7 s (n=806, v1.3.2 speed fix reflected
here vs the 2026-09-30 pre-v1.3.1 median of 26 s); failed radius median
22.8 s (n=674).

Per-case raw counts: see `measure36_run.log` and `measure36_partial/*.json`
(one file per case, resumable).

## What this does and does not establish

- This is real, fresh, full-affected-composition evidence (not the 1-3
  case/class sample the 2026-09-29 audit withdrew its estimate from) that
  item 18 asked for.
- It does NOT itself answer "does the discarded set bias snow-layer
  fractions, and by how much" — that requires joining these per-radius
  admissible/inadmissible outcomes back to the full published CMR2/CMC grid
  (474,075 converged rows) and recomputing snow fractions with vs without
  the recovered-admissible rows folded in. That join/recompute is NOT done
  here — doing it is the next step toward item 18's "quantify", not this
  measurement alone.
- Headline shape, stated carefully: only 39/892 (4%, CI95 3-6%) of
  previously-unreached radii converge to an ADMISSIBLE model (chi in valid
  range); the rest either still fail (475/892, 53%) or converge INADMISSIBLE
  (179/892, 20%, chi_li_icb < 0 — same class as the 21.8% of already-published
  converged rows with negative chi, error_code 4, not a new phenomenon).
  16/37 cases gain at least one admissible recovered radius.
- Per rule 5 (one calibrated definition of "pass"): these are regression/
  self-consistency outcomes (Newton convergence + admissible-box membership),
  not independently verified physical models — same caveat as every other
  v1.3.0 recovered row.

## Explicitly NOT done here, per owner instruction

- No science-impact number (corrected snow fraction, corrected CMR2 mean,
  "N models affected") is computed or stated from this data in this note.
  Item 18's own row says "erratum/comment decision is the authors'" — that
  decision, and any quantification built on top of this raw measurement,
  is for the owner/coauthors, not asserted here.
- Nothing from this note has been or will be sent to coauthors.

## Provenance

- git SHA: `b0d5ecb` (main, post v1.3.3)
- Env: `.venv/bin/python3`, numpy 1.21.5, scipy 1.8.0 (pinned)
- Host: shared 64-core box, `nice -n 10`, `PIE_WORKERS`-equivalent capped at
  10 (rule 15)
- Command and full provenance block: `v130_measure36.json`'s `provenance`
  key, and `MANIFEST.json`'s `resumed` block
