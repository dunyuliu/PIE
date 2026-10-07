# Fe-Si inner-core-EOS patch of the vendored Steinbruegge (2020) code

**Not the vendored reference tree** (`tests/reference/steinbruegge2020_8dc6466/`
is read-only per `PROJECT_RULES.md` rule 7 and is never edited). This
directory is a derived COPY, patched for one documented purpose: item 23(c)
on `PATHWAY_FORWARD.md` asked whether the Fe-Si disagreement between PIE and
the published Steinbruegge (2020) code at `ricb > 10 m` is fully explained by
physics-diff item 1 in
`docs/dev/notes/steinbruegge_anchor_2026-09-30.md` (the published code uses pure
fcc-Fe in its inner-core ODE / r0-density call, but FeSi density in its own
moment-of-inertia polynomial -- internally inconsistent for `li_el='Si'`).

## What is patched

`libcore.py`, two call sites, both gated on `param['li_el'] == 'Si'`
(`li_el == 'S'` is untouched -- byte-identical behaviour to the vendored
original, verified by running the Fe-S case through both trees and diffing
JSON output):

1. `shoot_mercmodel`'s r0-density call (vendored line 81): was unconditionally
   `eos.solidFccFe(P1/1E+9,T1,param)[1]`; now uses
   `eos.solidFccFeSi(chiSicb, P1/1E+9, T1, param)[1]` for `li_el='Si'`, with
   `chiSicb = v[4]` (same ICB Si content already used by the ICB melting-point
   and MoI-polynomial code 30 lines below it in the SAME unpatched file).
2. `rhs_PTrhog_solid_snow`'s inner-core ODE (vendored lines 372-401): gained an
   optional `chiSicb=0.0` parameter; for `li_el='Si'` it calls
   `eos.solidFccFeSi(chiSicb, ...)` instead of `eos.solidFccFe(...)`. The
   `solve_ivp` lambda in `shoot_mercmodel` now passes `chiSicb` through.

`coreEos.py` is copied verbatim, unmodified (it already has `solidFccFeSi`;
no new EOS code needed). This is exactly the "2-line patch" the anchor note
(`docs/dev/notes/steinbruegge_anchor_2026-09-30.md` "Fe-Si STB with FeSi
inner-core ODE" line) refers to.

This mirrors PIE's own `src/shootp.py` convention
(`eos.eosInnerCore(chi_icb, ...)` used at BOTH the r0 call, line 93, and the
MoI polynomial, line 144) -- i.e. this patch makes the vendored code
internally consistent in the same way PIE already is, nothing more.

## Provenance / independence note

This is still, in substance, the SAME third-party solver (shooting method,
Newton iteration, EOS classes, melting curves) as
`tests/reference/steinbruegge2020_8dc6466/` -- only the two call sites
above differ. Matching PIE here is a weaker claim than the Fe-S anchor (which
needed zero patching): it demonstrates "the published code's Fe-Si output
converges to PIE's once its one documented internal inconsistency is
removed", not "two independently-written codebases agree from a cold start".
`tests/integration/test_steinbruegge_fesi_inner_core_patch.py` states this
distinction explicitly and does not claim this patched tree is an
independent-from-PIE oracle in the rule-5 sense the Fe-S anchor is.

## Usage

Same subprocess-only convention as the unpatched runner (module name clash
with `src/coreEos.py`/PIE's `coreEos`):

```
/usr/bin/python3 run_steinbruegge_case_fesi_ic_patch.py Si <ricb_m> out.json
```
