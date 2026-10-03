**UNAUDITED -- not for coauthor communication, not an erratum, pending owner review and priya-nair audit**

# Item 18 "snow-fraction" step -- re-solving the 39 admissible recoveries for `isnow`

Board: `PATHWAY_FORWARD.md` item 18. Predecessor: `docs/notes/item18_quantify_2026-10-01.md`
(identified the 39 admissible rows but did not compute a snow-fraction "after"). This note closes
that gap. Everything here is regression-class (PIE output compared to PIE output); nothing is
truth-class (`PROJECT_RULES.md` rule 5).

Script + artifacts: `docs/notes/item18_snowfraction_2026-10-03_scripts/` --
`resolve_and_census.py` (4 stages), `census_measure36.json` (stage 1), `resolve39.json` (stage 2,
with provenance block), `published_census.json` (stage 3), `table.md` (stage 4).

## 0. Fresh re-derivation of the 39/892 split (cross-check, not inherited)

Re-read the 37 raw `docs/notes/solver_v1.3.0_measurement/measure36_partial/*.json` with
`testsys/pielib.py::is_admissible` verbatim: **892 beyond-stop radii, 218 converged, 39 admissible,
16/37 cases with >=1 admissible row**; per composition margot S 1, margot Si 0, margot S+Si 0.05 17,
margot S+Si 0.10 5, genova S 4, genova Si 3, genova S+Si 0.05 5, genova S+Si 0.10 4. Exact match to
the predecessor note (post-correction) and to `testsys/integration/test_measure36_counts.py`. No
mismatch.

## 1. Re-solve of the 39 triples under current code

Method: `testsys/pielib.py::solve_full_model(CMR2, CMC, light, liquidus, ricb_m, chi_Si_icb)`,
**cold start** at each radius (no warm start from the previous radius, unlike the `measure36`
sweep harness), 12-worker `ProcessPoolExecutor`. Provenance (`resolve39.json`): git `33c8b0a`
(origin/main at the time, worktree `item18-snowfraction`), pinned env Python 3.12.15 / numpy 2.5.3 /
scipy 1.18.1 (`the pinned project venv`), host knox (64 cores, load 10.2 at launch --
**contended**, timing not a measurement), 2026-10-03 16:27 CDT, 3-11 s per solve.

Result: **38/39 converge and are admissible fresh**; converged `v` agrees with the `measure36`
value to max |dv| <= 3e-8 (most <= 1e-9), `error_code` 0 and `err_flag` False for all 38.

**1 of 39 does not re-converge cold:** `genova_S_000_crash_stderr_10m`, k=38, ricb = 1900 km,
CMR2 0.31983. `SolverError: Line search failed at Newton iteration 6: no admissible step down to
alpha=0.000976562 (trial chi_li_icb=0.233825 > bound 0.230159)`. `measure36` reached this radius
only via warm start from k=37 (its own row says `start: warm`). It is a genuine warm-start-only
recovery, not a harness artefact; it is **excluded from the fresh "after" below** and reported
separately (§3) using its `measure36` value.

**Correction to the predecessor note's schema claim, found during this re-solve.** The `measure36`
JSON rows *do* carry the snow index: `fout` is `shoot_mercmodel`'s output tuple and
`fout[2] = isnow`, `fout[3] = isnowcmb` (`pie/shootp.py` docstring lines 66-67; same unpacking
`solve_full_model` performs). The field is unlabelled, not absent. Fresh `isnow` agrees with
`measure36 fout[2]` for **38/38** re-solved rows. The predecessor note's "no `isnow` field" wording
has been corrected in place (see §5). PIE itself (`pie/driverp.py`, `pMetaData_*.csv`) has always
written `isnow`/`isnowcmb`; the published Zenodo CSVs have both columns.

Per-row `isnow` of the 38 fresh solves (`resolve39.json`): 27 rows isnow=0; 11 rows isnow>0, **all
11 in margot S+Si 0.05** (`newton_maxit_10m` k=1..7: 2,2,1,1,1,1,1; `newton_maxit_later` k=5..8:
1,1,1,2) at ricb 50-400 km. `isnowcmb = 0` for all 38. The excluded warm-start row has
`measure36 fout[2] = 2`.

## 2. Published "before", re-derived fresh from the raw Zenodo CSVs

Stage 3 reads every `pMetaData_*.csv` under
`~/shared_dataset/zenodo.16459292/extracted/PIE/work.{margot,genova}/results/CMR2_*/`
(read-only): **36,864 files, 474,075 rows** (margot 201,633 + genova 272,442). This is the first
committed census artifact for the 474,075 denominator the 2026-10-02 audit flagged as
unverifiable (`published_census.json`); both halves match the audit's partial figures exactly.
The published `error_code` column is 0 on every row (as `pielib.is_admissible`'s docstring says).

Two denominators are reported: (a) **all published rows** (what the paper's CSVs contain), and
(b) rows passing `is_admissible` (chi_li_icb in [0, chi_li_eut_icb] for S/S+Si, [0, max_Si] for Si)
-- because 21-27% of published rows have chi_li_icb outside that box and a reader may argue either
is "the paper's population". The before-fractions under (a) reproduce the inherited table in
`item18_quantify_2026-10-01.md` §3 to 3 decimals for all 8 compositions sampled (0.385/0.038/0.263/
0.199/0.152/0.004/0.049/0.029).

## 3. Before / after / delta, per MOI x composition

Only compositions with >=1 recovered triple are shown; all other 22 (moi x composition) cells
have zero recovered rows and zero delta (`table.md` has every cell). "added" = admissible fresh
re-solves / admissible `measure36` triples. Deltas in percentage points of row fraction.

| moi/composition | published rows | before isnow>0 | added | added isnow>0 | after | delta (pp) | before, adm-only denom | after, adm-only | delta (pp) |
|---|---|---|---|---|---|---|---|---|---|
| margot/S | 13168 | 0.3852 | 1/1 | 0 | 0.3851 | -0.003 | 0.4504 | 0.4503 | -0.004 |
| margot/S+Si 0.05 | 13195 | 0.2634 | 17/17 | 11 | 0.2639 | **+0.049** | 0.3047 | 0.3052 | +0.051 |
| margot/S+Si 0.10 | 13017 | 0.1990 | 5/5 | 0 | 0.1990 | -0.008 | 0.2305 | 0.2304 | -0.010 |
| genova/S | 27545 | 0.1517 | 3/4 | 1 | 0.1517 | +0.002 | 0.1774 | 0.1774 | +0.002 |
| genova/Si | 39430 | 0.0043 | 3/3 | 0 | 0.0043 | -0.000 | 0.0000 | 0.0000 | +0.000 |
| genova/S+Si 0.05 | 18901 | 0.0488 | 5/5 | 0 | 0.0488 | -0.001 | 0.0793 | 0.0792 | -0.003 |
| genova/S+Si 0.10 | 4864 | 0.0288 | 4/4 | 0 | 0.0288 | -0.002 | 0.0587 | 0.0586 | -0.010 |

Sensitivity to the one non-reconverging row: counting it with its `measure36` warm-start value
(isnow=2) makes genova/S "added 4/4, added isnow>0 = 2", after = 0.15174, delta +0.005 pp. Nothing
else changes.

**Largest delta anywhere: +0.05 pp (margot S+Si 0.05, 26.34% -> 26.39%).** Every other cell is
|delta| <= 0.01 pp. The 11 snow-bearing recovered rows are 0.3% of that composition's 3,475
published snow rows.

## 4. Does it matter for the paper's claims? (analysis only -- the call is the owner's)

- At the level of **the 39 rows actually recovered**, no: the published per-composition snow
  fractions are stable to the second decimal in percent. The recovered set looks notable in
  aggregate (16/37 cases, 43% of recoveries in one pair) but, divided into a 13k-39k-row
  denominator per composition, it is noise.
- This is **not** a statement about the full affected population. The 39 rows are n=1 per
  (MOI x composition x failure-mode x stage) stratum from `measure36`, not a census of the ~7,332
  non-finished draws (`item18_quantify` §1, §4). Scaling is not legitimate: the one stratum that
  does carry snow (margot S+Si 0.05 `newton_maxit`, CMR2 ~0.3536, ricb 50-400 km, isnow 1-2) is also
  the one that recovers most rows, so if that branch is common among margot S+Si 0.05's 1,024
  non-finished draws the composition-level delta could be larger than +0.05 pp -- but **in the
  direction of more snow, not less**, i.e. opposite to item 18's original "recovered models skew
  no-snow" framing. Across the other 6 sampled compositions all 27 recovered rows are isnow=0,
  consistent with the original framing but at magnitudes of -0.01 pp or smaller.
- Bounding the population effect needs a stratified re-run (per composition, many draws), which is
  the "full re-run" the board row says is done -- if those outputs exist with `isnow`, the same
  stage-3/4 code applies directly; if they are `measure36`-style JSON, `fout[2]` is already the
  snow index and no re-solve is needed.

## 5. Changes made to earlier notes in this PR

- `docs/notes/item18_quantify_2026-10-01.md` §3 "After", §5 first bullet, §6 snow-fraction bullet:
  "schema has no `isnow` field" reworded to say the gap was specific to the `measure36`/`generate_sweeps.py`
  JSON being unlabelled (`fout[2]`/`fout[3]` are isnow/isnowcmb), and that PIE's `driverp.py`
  CSVs always had the columns; pointer to this note added. History of the original text retained.
- `PATHWAY_FORWARD.md` item 18 status cell: pointer to this note and the committed 474,075 census
  artifact appended. Not closed.

## 6. What a reviewer would attack

- **Denominator choice.** Under the adm-only denominator, both Si-only compositions have snow
  fraction exactly 0.0000: every published Si row with isnow=2 has chi_li_icb outside
  [0, max_Si] (`max_Si` taken from `pie/globalvar.py` for the Edmund liquidus). Either the paper
  did not apply that gate to Si, or the Si snow rows are the inadmissible ones by construction.
  Not resolved here; affects only the (b) columns and not the deltas, which are ~0 for Si either way.
- **Cold vs warm start.** `measure36` was warm-started; this re-solve is cold. 38/39 agreement to
  <=3e-8 in `v` says the root is the same; the one disagreement is a convergence-basin effect at the
  admissible-bound edge, not a different root.
- **Environment.** Re-solve ran on the pinned 3.12 env; `measure36` ran on 3.10/numpy 1.21/scipy 1.8
  (`provenance` block in each JSON). Agreement across envs is itself a mild regression check.
- **n=1 per stratum** carries over from the predecessor; nothing here fixes it.
- **Not independently audited.** All arithmetic lives in one script; the three JSON artifacts are
  committed so priya-nair can re-derive every number without re-running the 39 solves (~1 min
  wall on 12 workers if she wants to).
