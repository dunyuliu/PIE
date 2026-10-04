# Item 18(b) -- paper filter recompute (sort_models.py / paper_figures.py) -- 2026-10-04

**UNAUDITED -- pending priya-nair, not for coauthor communication.**
Regression-class analysis only (PROJECT_RULES rule 5): same-code-family
comparison (published Zenodo data vs the item 18(a) v1.6.0 re-run), not an
independent truth oracle. No coauthor numbers; owner (dunyu-liu) only.

Author: jordan-kim (data-integrity audit). Scripts and raw outputs:
`item18b_paper_filter_recompute_2026-10-04_scripts/` (`analyze.py`,
`trace.py`, `item18b_results.json`). Zenodo tree read-only throughout;
item 18(a)'s worktree `pie/results/` (`.claude/worktrees/agent-a7d2fd536939b904f`)
read-only throughout -- not reaped, nothing written there.

## 0. Correcting the task brief against the actual scripts

`sort_models.py` (read, not re-typed -- `analyze.py` reimplements its row
logic exactly since the published script is read-only and not importable
as a module):

- Scope: **only `*_S+Si_Edmund` folders**, and within those, only files
  where `chi_Si_icb` (the first row's value) is **> 0**. Pure-S and pure-Si
  runs, and the `S+Si_0.00` composition, are **not in the paper's sample at
  all** for any of Figs 1-5/S5-S10. Item 18(a)'s population table reports
  snow-fraction deltas for `margot/S`, `genova/S`, `margot/Si`, `genova/Si`,
  and `S+Si_0.00` -- none of those rows feed any paper figure. This is a
  bigger scope mismatch than the brief's filter list implied.
- Row-level filter actually applied: `chi_S_bulk > 0` (not "chi_S_bulk > 0
  AND chi_Si in 1-12wt%" as one block -- the chi_Si bound is enforced by
  which **files** exist/are globbed, not a row predicate; in practice the
  published runs only ever produced `chi_Si_icb` in {0.01,...,0.12} for
  S+Si, so the 1-12wt% bound is observationally true but not something
  `sort_models.py` itself checks).
- `isnow in {1,3}` -- confirmed, matches the brief (and corrects item 18(a)'s
  `isnow > 0`, which also included class 2).
- `goodTCMB`: `1700 <= Tcmb <= 2100` -- confirmed.
- `goodchiS`: `chi_S_bulk < 0.02`, **applied only on top of `goodTCMB`**
  (`goodTCMB_goodchiS`, not a standalone `chi_S_bulk<0.02` filter) -- confirmed.
- **No admissibility-box filter anywhere in `sort_models.py` or
  `paper_figures.py`.** Confirms the course-correction note's point 1: item
  18(a)'s `is_admissible` (`chi_li_icb` inside `[0, chi_li_eut_icb]`) is not
  one of the paper's filters and must not be carried over. (It also means
  the paper does not exclude negative-`chi_S_bulk` rows via the admissibility
  box -- it excludes them via the blunter `chi_S_bulk > 0` row filter, which
  is a weaker cut: anything with positive but out-of-eutectic-range
  `chi_S_bulk` is **kept** by the paper and would have been **dropped** by
  item 18(a)'s box.)
- Confirms point 2: `paper_figures.py`'s five heat-map-style panels (Figs 1,
  2, 4, S5, S7/S8, S9/S10 -- everything built from `counts_*`/`chiS_*` 3-D
  arrays) bin only `ricb in [10, 1,800,010]` m (37 steps of 50 km). Rows at
  ricb > 1800 km enter `all_df`/`sl_df`/`goodTCMB_df`/etc. (and therefore the
  MoI histograms S6/Figs1-2's lower panel, and Fig 5's unbinned scatter) but
  are **invisible to every heat map**. Published data happens to top out at
  ricb = 1,750,010 m (checked directly, both MoI), so this distinction is
  inert for the published rows alone -- it only bites once item 18(a)'s
  recovered rows (which run to ricb ~1.95 Mm) are added in.
- Confirms point 3: `paper_figures.py:388-402`, the S9/S10 middle row is
  titled `$T_{CMB}$ Constraint + Snow Layer` but plots `frac_counts_sl`
  (the plain snow-layer constraint, **no** TCMB filter) -- a pre-existing
  mislabeling bug in the *published* script, not something this recompute
  introduces or can fix (read-only). Flagged for whoever regenerates panels.
- Point 4 (cross-check hook) used as designed: one published row and one
  recovered row traced end-to-end through the filter logic below (section 5).

## 1. Method

`analyze.py` re-implements `sort_models.py`'s row/file predicates (not
re-run against the original script, which is read-only in the Zenodo tree
and has hardcoded paths/plot calls -- re-coded faithfully, line-by-line,
against the read copy above) over two row sets:

- **(a) published** -- read directly from the Zenodo bundle's own
  already-sorted output CSVs (`all_models_*MoI.csv`,
  `goodTCMB_*MoI.csv`, `snowlayer_*MoI.csv`, `goodTCMB_snowlayer_*MoI.csv`,
  `goodTCMB_goodchiS_*MoI.csv` -- these are `sort_models.py`'s own committed
  output, i.e. exactly what the paper's figures were drawn from). Grouped by
  `(moi, chi_Si_icb)`. This is item 18(a)'s denominator restricted to the
  S+Si/chi>0 scope sort_models.py actually uses.
- **(b) published + recovered** -- for the 1,131 item-18(a) sampled runs
  with `light == "S+Si"` and `chi_Si_icb > 0` (of 1,400 total sampled; the
  269 excluded are S, Si, and `S+Si_0.00`, out of `sort_models.py`'s scope),
  read the **raw** `pMetaData_<chi>.csv` from the item-18(a) worktree's
  `pie/results/`, take rows **beyond** `published_rows` (`csv_rows` in
  `main_sample.csv` -- the exact published-stop index item 18(a) used),
  keep `error_code == 0` (converged), then apply the same `chi_S_bulk > 0`
  / `isnow in {1,3}` / `goodTCMB` / `goodTCMB_goodchiS` predicates row by
  row. All 1,131 pMetaData files were found (0 missing).

Population totals use item 18(a)'s own stratified design (`main_sample.csv`
columns `stratum`, `N_h`, `n_h`): per `(moi, chi_Si_icb)`, `A = sum over
strata of (N_h/n_h) * sum(per-run count)`, `var(A) = sum over strata of
N_h^2 * (1-n_h/N_h) * var(per-run count)/n_h` (Horvitz-Thompson, finite-
population correction, `n_h>1` strata only) -- the identical formula
`snowfraction.py::estimate()` uses, re-applied here (not reinvented) to five
categories (`all`, `sl`, `goodTCMB`, `goodTCMB_sl`, `goodTCMB_goodchiS`)
instead of just "admissible"/"snow". CI95 = `A +/- 1.96*sqrt(var(A))`.
Negative lower bounds (small/zero-inflated strata) are reported as-is, not
clipped, matching the predecessor note's convention of flagging rather than
hiding a degenerate CI.

## 2. Headline before/after, per figure-relevant category (both MoI, all 12 S+Si chi values summed)

| category (paper panel) | MoI | published | + recovered (full range) [CI95] | + recovered (heat-map-eligible, ricb<=1800km) | after (full) | delta |
|---|---|---|---|---|---|---|
| all (denominator for S5/S6/Fig5 sample size) | margot | 136,840 | +7,357 [4,154, 10,560] | +5,835 | 144,197 | +5.38% |
| all | genova | 116,214 | +9,349 [5,029, 13,669] | +4,650 | 125,563 | +8.04% |
| sl (Snow Layer Constraint panel, S5/S6/S9-S10) | margot | 27,817 | +256 [-74, 585] | +159 | 28,072 | +0.92% |
| sl | genova | 6,698 | +335 [-236, 907] | +34 | 7,033 | +5.01% |
| goodTCMB (Fig1, part of S5/S6) | margot | 80,731 | +732 [-222, 1,687] | +148 | 81,463 | +0.91% |
| goodTCMB | genova | 59,827 | +2,108 [297, 3,920] | +892 | 61,935 | +3.52% |
| **goodTCMB_sl (Fig 2 -- the headline snow-probability heat map)** | margot | 10,395 | **+14 [-13, 41]** | **+0** | 10,409 | **+0.14%** |
| **goodTCMB_sl** | genova | 4,824 | **+0 [0, 0]** | **+0** | 4,824 | **+0.00%** |
| goodTCMB_goodchiS (Fig 4, and Fig 5 via the merged `goodTCMBandS` set) | margot | 22,938 | +732 [-222, 1,687] | +148 | 23,670 | +3.19% |
| goodTCMB_goodchiS | genova | 28,822 | +2,053 [321, 3,785] | +837 | 30,875 | +7.12% |
| Fig 5 (`goodTCMB_goodchiS`, both MoI combined) | both | 51,760 | +2,785 [99, 5,472] | n/a (unbinned scatter) | 54,545 | +5.38% |

**What visibly moves and what does not:**
- **Fig 2 (goodTCMB + snow layer, the paper's headline heat map) barely
  moves at all** -- the recovery exercise adds essentially zero rows to the
  one panel that jointly requires `goodTCMB` *and* snow (margot +0.14%,
  genova +0.00%, both CIs span zero or are exactly zero). Per-composition
  breakdown (`item18b_results.json::estimates.goodTCMB_sl_full`) shows the
  added `goodTCMB_sl` count is 0 in 22 of 24 (moi, chi) cells; the two
  non-zero cells are margot chi=0.02 (+14.3) and margot chi=0.01 (recovered
  `sl` rows exist there but none also satisfy `goodTCMB`). **Mechanism:**
  recovered rows concentrate at the edges of the parameter sweep (high ricb,
  often Tcmb < 1700 K in the "crash"/"maxit" modes), which is exactly the
  region `goodTCMB` excludes; the published runs already captured nearly all
  of the (TCMB-good, snow) intersection before stopping.
- **Figs 1/4/S5/S9-S10 (the heat maps generally) move less than the raw
  `all`/`sl` numbers above suggest**, because 20-50% of the added rows sit
  at ricb > 1800 km and are invisible to every heat-map panel (margot: 5,835
  of 7,357 added `all` rows are heat-map-eligible, 79%; genova: 4,650 of
  9,349, only 50% -- genova's recovered population skews to higher ricb).
  The histogram panels (S6) and Fig 5's scatter **do** see the full added
  set, so S6/Fig5 move more than the heat maps for the same category.
- **Fig 4 / Fig 5's `goodTCMB_goodchiS` moves the most of the "real panel"
  categories** (genova +7.12% full-range), and for margot the entire
  `goodTCMB` addition passes the `chi_S_bulk<0.02` cut too (41/41 sampled
  added `goodTCMB` rows at margot have `chi_S_bulk<0.02`, confirmed directly
  against the raw rows, not a code artefact) -- i.e. at high MoI, nearly every
  recovered TCMB-admissible row is also sulfur-poor.
- **The predicate fix alone (independent of any row recovery) is the
  dominant effect, and item 18(a) never surfaced it**: on the *published*
  data alone, `isnow > 0` (item 18(a)'s predicate) vs `isnow in {1,3}` (the
  paper's) gives margot 39,853 vs 27,817 rows (+43.3% relative, because
  `isnow==2` alone contributes 12,036 published rows) and genova 11,420 vs
  6,698 (+70.5% relative, `isnow==2` contributes 4,722). This dwarfs every
  population-recovery delta in the table above by one to two orders of
  magnitude, and it is a pure labeling/predicate error, not a sampling
  question -- it does not need a re-run to see, only re-reading
  `sort_models.py`.

## 3. Cold-check-unstable rows -- sensitivity layer

Of the 1,098 item-18(a) recovered-admissible rows cross-checked cold
(`main_coldcheck.json`), 28 land on a different Newton root under a
cold-start solve, and of those, **20 flip from snow (`isnow in {1,2,3}`) to
no-snow (`isnow==0`) cold**. Matched back to this recompute's categories by
`(moi, composition, ricb_km)` (the cold-check json carries no row-level id
beyond that triple, so duplicate `ricb_km` values within a composition are
matched best-effort/first-available -- this changes which physical row is
flagged but not the per-composition count, which is all the stratified
estimator uses):

- Estimated (stratified, same weights) contribution of the 20 flip rows to
  the **full-range** `sl` addition: margot +124 of the +256 `sl` total
  (49%), genova +277 of the +335 (83%). Restricted to **heat-map-eligible**
  rows the flip-row contribution is margot +28 of +159 (18%), genova +34 of
  +34 (**100%** -- every heat-map-eligible genova `sl` addition in this
  sample is one of the 20 unstable rows).
- **Headline sensitivity test**: does excluding or cold-flipping these rows
  change section 2's conclusion? **No change to the headline** -- Fig 2
  (`goodTCMB_sl`) already shows ~0 added rows before touching the sensitivity
  case (margot's two non-zero `goodTCMB_sl` cells, chi=0.01/0.02, are not
  among the flagged rows), so Fig 2 is unaffected either way. The `sl`-only
  panel (S5/S9-S10 middle-left) and the histogram (S6) **do** shrink under
  the flip/exclude variant: margot `sl` addition drops from +256 to roughly
  +132 (flip) or +132 (exclude, same effect since excluded rows no longer
  count as snow or as anything), genova from +335 to +58. Both are still
  small relative to the published `sl` denominators (27,817 / 6,698), so the
  qualitative conclusion ("the recovery exercise is a small perturbation on
  `sl`, and effectively a null perturbation on `goodTCMB_sl`/Fig 2") is
  robust to this sensitivity case. The isnow==2-vs-{1,3} predicate error in
  section 2 remains the dominant finding regardless.

## 4. End-to-end trace

**Published row** (`all_models_highMoI.csv` row 0, margot, chi_Si_icb=0.01,
mass=0.9962329290491736): `Tcmb=2011.23` (in [1700,2100]), `isnow=0.0`,
`chi_S_bulk=0.0046858`. Predicted: in `goodTCMB_highMoI.csv` and
`goodTCMB_goodchiS_highMoI.csv`, absent from `snowlayer_highMoI.csv`.
Grepped directly on the unique `mass` value against all three files --
confirmed present/present/absent exactly as predicted.

**Recovered row** (genova, `CMR2=0.31985709385011124`,
`chi_Si_icb=0.01`, `pMetaData_0.01.csv` row index 38 of the 40-radius
re-run sweep, 0 published rows for this run i.e. fully new): `ricb=1,900,010`
m, `Tcmb=1613.88` K, `isnow=1`, `chi_S_bulk=0.003837`, `error_code=0`
(converged). Hand-applied filter: `chi_S_bulk>0` yes -> enters `all`;
`isnow in {1,3}` yes -> enters `sl`; `goodTCMB` (1700<=Tcmb<=2100)? **No**
(1613.88 < 1700) -> excluded from `goodTCMB`, `goodTCMB_sl`,
`goodTCMB_goodchiS`; `ricb=1,900,010 > 1,800,010` -> excluded from every
heat-map panel, present only in `all_df`/`sl_df`-derived histogram (S6) and
(if it had passed goodTCMB) Fig 5. `analyze.py`'s per-run aggregation
produces the identical classification for this row (script and hand trace
agree on all five category flags and the heat-map-eligibility flag).

## 5. Caveats (inherited from item 18(a), still apply)

- Same-code-family comparison; no independent truth oracle (rule 5).
- Item 18(a)'s 1,400-run sample (here: 1,131 S+Si/chi>0 runs) is itself
  biased low by the 326 mid-sweep crashes and 52 timeouts in that re-run
  (disproportionately losing high-ricb radii -- exactly where `sl` rows and
  heat-map-ineligible rows concentrate), so every "+recovered" number above
  is a lower bound on the true population addition, same caveat as item
  18(a) section 7.
- 121 of the 1,098 recovered-admissible rows fail to reconverge cold at all
  (`SolverError`) -- not used here since this recompute uses the warm
  (production) row values throughout, as `sort_models.py` would see them;
  flagged only as a reminder that "recovered" does not mean "robust".
- The cold-check join in section 3 is best-effort on `(moi, composition,
  ricb_km)`, not a row id -- fine for the aggregate counts used here, not
  fine for attributing the flip to one specific physical draw.
- `paper_figures.py`'s S9/S10 mislabeling (section 0) is a pre-existing
  published-code bug, reported but not fixed (read-only Zenodo tree); if
  marta-silva regenerates panels, decide whether to reproduce the bug
  faithfully or flag the discrepancy in the regenerated figure.
- This note does not re-derive the published CSVs from raw `pMetaData`
  (point 4 of the course-correction message) beyond the two single-row
  traces in section 4 -- a full re-derivation of 253,054 published rows from
  raw per-run csvs was judged out of proportion to what changes the verdict
  (the shipped `all_models_*.csv` etc. already *are* `sort_models.py`'s own
  committed output, i.e. not an independent recomputation target here, only
  a provenance check on `sort_models.py` itself, which the single-row trace
  already exercises end-to-end).

## 6. Open questions

- Whether a full raw-`pMetaData` re-derivation of the published CSVs
  reproduces them exactly (only spot-checked via one row in section 4) --
  route to a follow-up if an auditor wants that guarantee rather than the
  single-row trace.
- Whether `paper_figures.py`'s S9/S10 mislabeling changes the paper's stated
  conclusions in the SI text (not read here -- only the plotting script).

## Final note

Sign-off rests with priya-nair (pending) and the owner. Fixes/figure
regeneration are marta-silva's and a separate agent's job, not this note's.
