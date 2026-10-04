# Item 18(b) -- figure regeneration, published vs. published+recovered -- 2026-10-04

**INTERNAL DRAFT -- item 18b comparison, not for publication. UNAUDITED,
owner (dunyu-liu) only, not for coauthor communication.** Builds on
jordan-kim's `item18b_paper_filter_recompute_2026-10-04.md` (read, not
edited) -- that note is the methodology reference; this note only
describes the figure-regeneration artifacts.

Author: marta-silva (figure engineer). Scripts:
`item18b_figure_comparison_2026-10-04_scripts/{build_rowsets.py,make_figures.py}`.
Figures: `item18b_figure_comparison_2026-10-04_figs/*.png` (17 PNGs).
Does not edit or replace jordan-kim's note/scripts, the Zenodo copy of
`sort_models.py`/`paper_figures.py` (read-only reference, re-implemented
not imported), or item 18(a)'s worktree `pie/results/` (read-only).

## What was built

1. `build_rowsets.py` reads item 18(a)'s `main_sample.csv` (S+Si,
   chi_Si_icb>0 rows only, matching the paper's scope per jordan-kim's
   note sec. 0) and the raw `pMetaData_<chi>.csv` files in the item-18(a)
   worktree, keeps rows beyond the published-stop index, converged
   (`error_code==0`), `chi_S_bulk>0`, and tags each with its stratified
   Horvitz-Thompson weight (`N_h/n_h`, straight from `main_sample.csv`).
   Caches to `cache/recovered_all_{high,low}MoI.csv`. **Cross-check**:
   weighted row sums (7,357.2 / 9,349.2) match jordan-kim's reported
   population-level `all` additions (+7,357 / +9,349) exactly.
2. `make_figures.py` re-implements `paper_figures.py`'s own binning
   (ricb/chi_Si grid, category predicates: `sl`=isnow in {1,3},
   `goodTCMB`=1700<=Tcmb<=2100, `goodTCMB_goodchiS`=goodTCMB &
   chi_S_bulk<0.02) over BEFORE (published only, weight=1) and AFTER
   (published + weighted recovered rows), and renders every affected
   panel as a side-by-side BEFORE/AFTER comparison with shared color
   scales. No seaborn dependency added (not in `requirements.txt`);
   heatmaps use plain matplotlib `imshow`, same binning/flip/labeling
   `paper_figures.py` uses.

## Figures produced (17 PNGs, 2 per figure family x {high,low} MoI except Fig5)

| file | paper figure | category | heat-map ricb<=1800km limited? |
|---|---|---|---|
| fig1_goodTCMB_{high,low}MoI.png | Fig 1 | goodTCMB | yes (top heatmap row); histogram is full-range |
| fig2_goodTCMB_sl_{high,low}MoI.png | Fig 2 (headline) | goodTCMB_sl | yes / histogram full-range |
| fig3_meanCV_goodTCMB_sl_{high,low}MoI.png | Fig 3 | goodTCMB_sl mean/CV chiS | yes |
| fig4_goodTCMB_goodchiS_{high,low}MoI.png | Fig 4 | goodTCMB_goodchiS | yes |
| fig5_scatter_goodTCMBandS.png | Fig 5 | goodTCMB_goodchiS, both MoI combined | no -- full range, recovered points highlighted |
| figs5_heatmaps_{high,low}MoI.png | Fig S5 | all/goodTCMB/sl/goodTCMB_sl | yes |
| figs6_hist_{high,low}MoI.png | Fig S6 | all/goodTCMB/sl/goodTCMB_sl | no -- full range (text flag on each panel) |
| figs7_meanCV_all_highMoI.png / figs8_meanCV_all_lowMoI.png | Fig S7 / S8 | all mean/CV chiS | yes |
| figs9_fraccounts_highMoI.png / figs10_fraccounts_lowMoI.png | Fig S9 / S10 | goodTCMB, sl, goodTCMB_goodchiS fraction-of-max | yes |

Every heat-map-style panel carries a folded-in x-axis caveat line: "heat
map: ricb<=1800 km only; recovered rows to ~1950 km excluded -- see
S6/Fig5 for full range" (layout-reserved via `constrained_layout`, not a
floating annotation, so it cannot collide with the panel below). The
S9/S10 "Snow Layer Constraint" row's title states explicitly that the
published script's label ("TCMB Constraint + Snow Layer") is a
pre-existing `paper_figures.py` bug (jordan-kim's note sec. 0) and that
this regeneration reproduces the plotted array faithfully but WITHOUT
reproducing the mislabel.

## Visible delta vs. visually identical (by inspection of the rendered PNGs)

- **Visually identical / no detectable change**: `fig2_goodTCMB_sl_*`
  (both heatmap and histogram, both MoI) -- the headline panel. Matches
  jordan-kim's point estimate (+0.14%/+0.00%, heat-map-eligible +0 for
  both). `figs5_heatmaps_*` bottom row (goodTCMB_sl) likewise unchanged.
- **Small but visible change**: `fig1_goodTCMB_*` and
  `figs5_heatmaps_*`/`figs9_*`-`figs10_*` top/middle rows (goodTCMB, all,
  sl) -- a handful of new cells appear at high-chiSi/low-ricb edges in
  the AFTER heatmap, consistent with jordan-kim's 0.9-5% deltas.
  `fig4_goodTCMB_goodchiS_*` shows the same small addition (margot:
  entire goodTCMB addition also passes chiS<0.02, per her note).
- **Clearly visible change**: `fig5_scatter_goodTCMBandS.png` (recovered
  points extend ricb from ~1,650 km to ~1,950 km and mantle density down
  to ~2,750 kg/m^3, well outside the published envelope) and
  `figs6_hist_*` upper rows (all/goodTCMB), both full-range panels that
  are NOT heat-map-limited -- these see the recovered population most
  directly.
- `fig3`/`figs7`/`figs8` (mean/CV of chi_S,bulk): changes are confined to
  a few cells near the edges of the populated region; masked
  (zero-count) cells unaffected.

## Caveats

- Same caveats as jordan-kim's note (regression-anchored, not an
  independent oracle; sample itself biased low by mid-sweep crashes).
- AFTER heatmap/histogram counts are population point-estimates (sum of
  weights), not the stratified CI -- cross-checked against her point
  estimates (see above), not against her CI bounds.
- Fig 5's recovered points are plotted unweighted (1 sampled run = 1
  point) since weighting a scatter would require jittering duplicate
  points; this is a qualitative range-extension illustration, not a
  density estimate -- noted in the figure's legend.
