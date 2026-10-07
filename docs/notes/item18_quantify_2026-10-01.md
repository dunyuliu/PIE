**SUPERSEDED SUMMARY (condensed 2026-10-07, docs-lean pass, item 37) — UNAUDITED, not for
coauthor communication.** Original 199-line narrative dropped; headline counts preserved below.
Source of truth for these counts: `testsys/reference/v1_2_0_sweeps/v130_measure36.json`, derived
mechanically (not hand-typed) by `testsys/integration/test_measure36_counts.py`.

# Item 18 "quantify" step — headline counts

Board: `PATHWAY_FORWARD.md` item 18. Regression-class only (self-consistent re-derivation from
PIE's own v1.0.5 output), no truth-class claim (`PROJECT_RULES.md` rule 5).

- 37 affected compositions sampled (one case per populated MOI x composition x failure-mode x
  radius-stage stratum; n=1 per stratum, not a random/weighted sample).
- 892 radii beyond each case's published v1.0.5 stop point.
- 39 admissible rows among those 892 (**4%, CI95 3-6%**); 16/37 cases gain >=1 admissible row
  (**43%, CI95 27-61%**).
- Failure-mode split of the 39 admissible recoveries: **74% `newton_maxit`, 23% `crash_stderr`,
  3% `detJ0`**.
- 43.6% (17/39) of all admissible recoveries concentrate in a single MOI x composition pair
  (margot S+Si 0.05) — the pooled rate is not representative of the other sampled compositions.

These counts are regenerated fresh by `testsys/integration/test_measure36_counts.py` from the
raw fixture on every test run; treat that test, not this file, as authoritative if the two ever
disagree.
