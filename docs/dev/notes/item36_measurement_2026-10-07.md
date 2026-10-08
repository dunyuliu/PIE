# Item 36 measurement (2026-10-07): does `mercmodel_box` on the returned iterate change any published result?

## Question

`PATHWAY_FORWARD.md` item 36: `pie/shootp.py::mynewtonSys`'s admissible-box
test (`box_fun`, Mercury: `mercmodel_box`) runs on every line-search trial
but never on the final returned iterate (the `converged_now` fast path
skips the trial block entirely) nor on `x0`. Owner-approved plan: measure
first, across the published/regression sweeps the test system already
carries, how many converged rows' returned iterate (and `x0`) would fail
`mercmodel_box` if it were checked. If zero and bit-identical, the check
may default on; otherwise ship opt-in/default-off and report the count.

## Method

No re-solve was needed: `mercmodel_box`'s three live checks (`CHI_MIN` is
`None`, so the lower-chi branch never fires) are all already reconstructible
from columns every `pMetaData_*.csv` row already carries:

- non-finite: `rcmb`, `ricb`, `chi_li_icb`, `Picb`, `Tcmb` all finite
- `rcmb <= ricb` (scale-invariant: comparing the dimensional columns is
  equivalent to the non-dimensional in-code comparison, same scale factor
  on both sides)
- `chi_li_icb > chi_max`: for `Si`-only rows, `chi_max` is the constant
  `max_Si_Edmund2022=0.12` / `max_Si_Steinbruegge2020=0.15`
  (`pie/globalvar.py`); for `S`/`S+Si` rows, `chi_max` is exactly the
  `chi_li_eut_icb` column (`pie/driverp.py`'s
  `chi_li_eut_icb=0.11+0.187*np.exp(-0.065*Picb*1e-9)`, the same formula
  `mercmodel_box` uses, `pie/shootp.py:351`) -- already computed per row.

Filtered to converged rows (`error_code == 0`) in each dataset. The
measurement script itself is not tracked in this repo (PROJECT_RULES.md
rule 1b forbids new `*_scripts` artifact trees under `docs/`, one
documented exception predating this rule); it read only the columns listed
above from each `pMetaData_*.csv` and wrote no new output files.

## Populations checked

1. **Published v1.0.5 Zenodo dataset** (`~/shared_dataset/zenodo.16459292/extracted/PIE/work.{margot,genova}/results/*`,
   read-only, the project's primary regression anchor, item 2): 17,141
   files, 474,075 converged rows -- matches the board's independently
   committed census (item 18, `inventory.py`/`summarize_inventory.py`:
   margot 201,633 + genova 272,442 = 474,075), cross-checking that this run
   read the right population.
2. **`tests/reference/zenodo_v1.0.5/mc_wide`** (the committed, curated
   slice that runs in CI): 14 files, 424 converged rows.
3. **`tests/reference/self_v1.0.5`**: 1 file, 17 converged rows.

(`v1.0.3_20221021`/`v1.0.4_20230127` use an older, pre-error-code CSV
schema with different column names -- out of scope here, already flagged
on the board as superseded/bug-bearing anchors, not this measurement's
target population.)

## Result

| population | converged rows | fail non-finite | fail rcmb<=ricb | fail chi>chi_max | fail ANY |
|---|---|---|---|---|---|
| published v1.0.5 (full) | 474,075 | 0 | 0 | **1,502** | **1,502 (0.317%)** |
| mc_wide (curated, CI) | 424 | 0 | 0 | 0 | 0 |
| self_v1.0.5 | 17 | 0 | 0 | 0 | 0 |

All 1,502 failures are `light_element == "Si"` rows (168 distinct
compositions), `chi_li_icb` exceeding the Edmund Si cap (0.12) by
1.2e-5 to 0.102 (median 0.0065), spanning the full `ricb` sweep
(10 m to 1,950,010 m) -- not isolated to one radius or composition.
**Not zero.** The committed curated regression fixture (`mc_wide`, 424
rows) happens to sample none of the 168 affected compositions, which is
why this gap was invisible to the existing test suite (consistent with the
board row's "not yet run" status).

## Conclusion

Per the owner's standing rule (solver/policy changes are opt-in or proven
bit-identical) and this item's own pre-agreed decision tree: the count is
NOT zero, so the final/x0 box-check (`PIE_BOX_CHECK_FINAL`,
`pie/shootp.py`) ships **opt-in, default off** -- default behaviour is
unchanged (the flag is read once at import and gates both new check sites;
unset or `"0"` reproduces the exact pre-item-36 code path). Regression
tests (`tests/unit/test_line_search.py`,
`test_final_iterate_box_check_default_off_then_opt_in`,
`test_x0_box_check_default_off_then_opt_in`) lock both halves of that
claim: default-off is bit-identical even when the box would reject
everything, and the opt-in path raises with the box's own error code and a
`box_check_final: True` context flag.

## x0 note (not separately counted)

`x0` for every radius after the first is the previous radius's converged
`v` -- already covered by the table above (an in-box converged row is also
an in-box `x0` for the next radius). The only genuinely distinct `x0` is
the generic cold start `param['v0'] = [0.8, 1.0, 0.8, 0.7, 0.05]`
(`pie/planet_input.py:59`), non-dimensional `rcmb=0.8`. Mercury's radius
`scale['a'] = 2,439,360 m` (`pie/planet_input.py:37`), so this cold start
fails `rcmb <= ricb` once `ricb_nd > 0.8`, i.e. `ricb > 1,951,488 m` --
within the swept range (`rs=np.arange(1e1, 2e6, dr)`,
`pie/main.py:168`). No converged row in the published dataset reaches
past `ricb=1,950,010 m` (the table's own max), consistent with -- but not
proof of -- this being a contributing cause of non-convergence at the
largest radii; not re-solved to confirm causation (out of this
measurement's scope).
