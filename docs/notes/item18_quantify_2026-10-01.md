**UNAUDITED — not for coauthor communication, not an erratum, pending independent audit (recommend priya-nair or equivalent)**

# Item 18 "quantify" step — joining the 36/37-case recovery measurement to the published grid

Board: `PATHWAY_FORWARD.md` item 18. Inputs: `testsys/reference/v1_2_0_sweeps/v130_measure36.json`
(regenerated locally from the committed `measure36_partial/*.json`, which this note re-derives from —
see §0), `docs/notes/solver_v1.3.0_measurement/measure36_results_2026-10-01.md`,
`docs/notes/solver_v1.3.0.md`, `docs/notes/failure_analysis_2026-09-28.md` +
`docs/audits/AUDIT_2026-09-29_*.md` (the withdrawn 2026-09-29 estimate and its audit).

## 0. Fresh re-derivation (this note's own evidence, not just inherited)

The 37 committed `measure36_partial/*.json` files were re-read and re-aggregated independently of
`measure36_results_2026-10-01.md`, applying `testsys/conftest.py::is_admissible`'s own rule
(`0 <= chi_li_icb <= chi_max` and no `err_flag`) row-by-row. Result: **892 radii beyond the v1.0.5
stop point, 218 converged, 39 admissible, 16/37 cases with >=1 admissible row** — exact match to the
posted summary. This is a regression-class self-check (same data, independently re-parsed), not new
data; it is reported fresh here because it surfaced a fact the rolled-up table does not show (§2).

## 1. Join methodology — is the 37-case sample representative?

**Population it is drawn from.** Restricting to the 4 compositions the 37-case sample actually covers
(S, Si, S+Si 0.05, S+Si 0.10 — it does **not** cover S+Si 0.00 or S+Si 0.12, both present in the
published grid), the published per-composition end-state census in
`docs/notes/failure_analysis_2026-09-28.md` §1.1 gives, per MOI, exactly 1024 draws/composition
(internal check: maxit+detJ0+traceback+finished sums to 1024 in every row of that table — re-verified
here, holds in all 8 rows used):

| MOI | composition | non-finished draws |
|---|---|---|
| margot | S | 1024 |
| margot | Si | 766 |
| margot | S+Si 0.05 | 1024 |
| margot | S+Si 0.10 | 1024 |
| genova | S | 1024 |
| genova | Si | 422 |
| genova | S+Si 0.05 | 1024 |
| genova | S+Si 0.10 | 1024 |
| **total** | | **7332** |

(Excludes the IndexError/"Mode C" geometric-limit deaths near ricb/rcmb>=0.99875, ~745 draws total,
which measure36 does not sample and which item 17/18 have treated throughout as a near-complete,
not-solver-bug-limited branch end — a scope choice inherited here, not re-justified.)

**Sample design.** `measure36`'s 37 cases are **one draw per non-empty (MOI x composition x
failure-mode x radius-stage) cell**, i.e. an exhaustive-stratum convenience sample at **n=1 per
stratum**, not a random or size-weighted sample of the 7332-draw population, and not covering 2 of
the 6 populated compositions at all. This is the same structural shape as the withdrawn 2026-09-29
estimate's weakness (thin per-cell n) — improved here only in that (a) every populated
MOI x composition x failure-mode x stage cell that measure36 targets has exactly one case, not an
arbitrary 1-3 pick, and (b) CIs are carried through rather than dropped. It is **not** a fix for the
underlying statistical thinness; see §4.

## 2. What the fresh re-derivation shows that the rolled-up table does not: extreme concentration

Of the 39 admissible rows, **16 (41%) come from a single MOI x composition pair**
(margot S+Si 0.05, CMR2 ~ 0.3536-0.3537, split across its `newton_maxit/10m` case (10 admissible
rows) and its `newton_maxit/later` case (6 admissible rows) — almost certainly the same physical
branch sampled at two failure-mode labels). The `newton_maxit` failure mode alone supplies 29/39 (74%)
of all admissible recoveries; `crash_stderr` supplies 9/39 (23%); `detJ0` supplies 1/39 (3%) — even
though `crash_stderr` and `detJ0` dominate the raw *count* of affected draws (§1 table, and
`failure_analysis_2026-09-28.md` §2). Per-composition admissible counts (from §0's re-derivation):
margot S 1, margot Si 3 (genova, not margot — see raw table), margot S+Si 0.05 16, margot S+Si 0.10 5,
genova S 4, genova Si 3, genova S+Si 0.05 5, genova S+Si 0.10 2.

**Consequence: the pooled 39/892 (4%, CI95 3-6%) and 16/37 (43%, CI95 27-61%) rates are not a
homogeneous property of the affected population — they are dominated by one recovering branch.**
Any flat-rate scaling of either number to the 7332-draw population (as the withdrawn estimate did at
finer grain) would implicitly assume every composition recovers like margot S+Si 0.05, which this
same data contradicts (margot S, Si, and both 10-m crash_stderr/detJ0 cases for margot recovered 0-1
admissible rows each). This is the single largest reason the number below is reported as a bound, not
a point estimate.

## 3. Before/after, bounded

**Before (published, inherited from `docs/notes/failure_analysis_2026-09-28_scripts/runs_bias_estimate.txt`,
itself built from a full census of the published Zenodo dataset, NOT re-run fresh in this note — flagged
as inherited, not fresh):**

| moi/composition | published draws (>=1 converged row) | published isnow>0 row-fraction | published CMR2 mean |
|---|---|---|---|
| margot/S | 585 | 0.385 | 0.3386 |
| margot/Si | 452 | 0.038 | 0.3336 |
| margot/S+Si 0.05 | 560 | 0.263 | 0.3434 |
| margot/S+Si 0.10 | 511 | 0.199 | 0.3482 |
| genova/S | 1006 | 0.152 | 0.3330 |
| genova/Si | 1006 | 0.004 | 0.3326 |
| genova/S+Si 0.05 | 620 | 0.049 | 0.3359 |
| genova/S+Si 0.10 | 150 | 0.029 | 0.3409 |

**After: cannot be computed as a snow-fraction number.** The `generate_sweeps.py` measurement that
produced the 39 admissible rows records `v, f, fout, chi_li_icb, chi_max, rcmb_m, profile_finite,
rho_min` per row — **no `isnow`/`isnowcmb` field** (verified by reading the raw JSON schema directly,
`measure36_partial/*.json`, in this note). Snow-layer state requires the full adiabat-vs-liquidus
profile classification that `solve_full_model` (not `generate_sweeps.py`) computes. **This is a real
gap, not a rounding-down**: a corrected snow-fraction number requires re-solving the 39 admissible
(CMR2, CMC, ricb) triples with `solve_full_model` to get `isnow`, which this note does not do (scope:
docs/analysis only, no new physics runs beyond the already-committed measurement).

**What can be bounded without that re-solve:**
- *Row-count impact.* Scaling the pooled rate 39/892 (CI95 3-6%) by the ratio of population "beyond-stop"
  radii to the 892 sampled (approximated as draws x ~24 radii/case, the sample's own average) gives an
  **order-of-magnitude** range of 5,000-11,000 newly-admissible rows across the 7332-draw affected
  population **if** the pooled rate generalized — which §2 shows it plausibly does not, since it is
  carried by one branch. The genuinely defensible statement is only: **0 (if recovery is as
  composition-specific as the per-case table in §2 suggests) to low-order-thousands (if the pooled rate
  generalizes) new admissible rows**, against a published denominator of 474,075 converged rows overall,
  or a few hundred to ~1000 rows for any single affected composition (table above). Either way this is a
  **single-digit-percent** change to the row denominator for the affected compositions, not a reversal.
- *CMR2, not confounded by a missing re-solve (CMR2 is a draw input, already known for every case).*
  The dominant recovering case (margot S+Si 0.05, CMR2 ~0.3536-0.3537) sits **above** that composition's
  published CMR2 mean (0.3434) — i.e. at the **opposite** edge from the "recovered models skew low-CMR2"
  direction item 18's framing states and the withdrawn 2026-09-29 estimate assumed (that direction was
  established only for the `crash_stderr` class, which this measurement shows supplies a minority, 23%,
  of admissible recoveries). The `crash_stderr`-class admissible rows in this sample (genova S, genova
  S+Si 0.05/0.10, margot S+Si 0.05/0.10 — see §2) are each single rows per case at CMR2 within
  0.01-0.02 of their composition's published mean, not at a visible edge. **Net CMR2 effect: direction is
  not uniformly "low-CMR2 skew" as previously assumed; it depends on which failure mode dominates the
  recovered rows for a given composition, and this sample does not resolve it below the single-case level.**

## 4. Regression-class vs truth-class (PROJECT_RULES.md rule 5)

Everything in this note is **regression-class**: self-consistent re-derivation from this repo's own
measurement and census data (the published Zenodo dataset is itself PIE v1.0.5 output, not an
independent truth source). There is **no truth-class statement anywhere in this note** — not the
admissible-row counts, not the CMR2 observation, not the population totals. All of it stays internal
to PIE per `CLAUDE.md`/`PATHWAY_FORWARD.md` item 18's standing instruction.

## 5. Caveats / known limitations

- **isnow is not computable from this measurement** (§3) — the single largest gap. Closing it needs a
  fresh `solve_full_model` pass over the 39 (CMR2, CMC, ricb) triples; not done here.
- **S+Si 0.00 and S+Si 0.12 are entirely unsampled** by the 37-case measurement; their contribution to
  the affected population (margot 1024+557 draws, genova 1024+? — S+Si 0.12 counts not fully
  transcribed in the inherited census table) is excluded from every number above. The true affected
  population is larger than the 7332 used here.
- **n=1 per stratum.** No stratum-level CI is meaningful; only the pooled n=37/n=892 CIs are (and even
  those assume the 6 published-class buckets are internally homogeneous across the compositions pooled
  into them, which §2 shows is false for at least `newton_maxit`).
- **The dominant recovering case might be a labeling duplicate.** `measure36_results_2026-10-01.md`
  itself flags that one case's `published_class` groups into a bucket shared with another
  (`cls_of()` grouping artifact) — raw per-case rows (used here) are authoritative, but this note did
  not independently re-verify that margot S+Si 0.05's two recovering cases (`newton_maxit/10m`,
  `newton_maxit/later`) are genuinely distinct draws rather than two labels on the same one.
- **Mode C (IndexError, geometric limit) is excluded from scope**, inherited from item 17/18's framing,
  not re-justified here.
- **No number here should be read as a percentage-point snow-fraction correction.** The only quantities
  computed to more than order-of-magnitude precision are population counts (§1, cross-checked via the
  1024-identity) and the fresh 39/892/16-37 re-derivation (§0); everything downstream of those is
  explicitly bounded, not point-estimated.

## 6. Headline (for the owner, not for coauthors)

- Affected population (4 sampled compositions, both MOI, excl. Mode C): **7332 draws** (fresh count,
  cross-checked).
- Admissible-recovery rate: **39/892 radii (4%, CI95 3-6%)**; **16/37 draws (43%, CI95 27-61%)** gain
  >=1 admissible row — both fresh re-derivations, matching the posted summary exactly.
- **41% of all admissible recoveries concentrate in one MOI x composition pair** (margot S+Si 0.05) —
  the pooled rate is not representative of the other 7 sampled compositions, several of which recovered
  zero admissible rows.
- Snow-fraction before/after: **before** is the inherited published census (table in §3); **after
  cannot be computed** — `isnow` is not in the measurement's output schema. Row-count impact is bounded
  at roughly 0 to low-thousands of newly-admissible rows against a 474,075-row published denominator
  (single-digit-percent at most for any one affected composition), not a reversal of direction.
  CMR2 direction is **not** uniformly low-CMR2 as previously assumed; it depends on which failure mode
  dominates a given composition's recoveries.
