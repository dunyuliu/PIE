"""item31c verifier (v3): same three HEAD production acceptance checks as
verify_v105_root_v2.py, but reads `liquidus_eq` PER ROW from the task file
instead of hardcoding 'Edmund' (v2 lines 32/56). This was moot for item31b's
sample (30 Si-only candidates, all chi_Si_icb=0.00, item31b note section 0)
but is NOT moot here: item31c samples from S/Si/S+Si rows directly selected
by error_code, so the liquidus model used for each row's own chi_max bound
must match what that row actually ran under.

chi_max plumbing, confirmed against pie/shootp.py:348-355 (mercmodel_box)
and pie/driverp.py:137-139 (S+Si pre-sweep check):
  - light == 'Si':   chi_max = max_Si_Steinbruegge2020 if liquidus_eq ==
                      'Steinbruegge' else max_Si_Edmund2022 (a liquidus-
                      dependent CONSTANT, shootp.py:350).
  - light in ('S','S+Si'): chi_max = 0.11 + 0.187*exp(-0.065*Picb*1e-9)
                      (Dumberry & Rivoldini 2015 eq 28 eutectic-S bound,
                      shootp.py:353) -- NOT liquidus-dependent; same
                      formula regardless of liquidus_eq.
  - light == 'S+Si' ADDITIONALLY has a one-time, radius-independent
    pre-sweep gate on the fixed chi_Si_icb input itself
    (driverp.py:137-149): si_max = max_Si_Steinbruegge2020 if
    liquidus_eq=='Steinbruegge' else max_Si_Edmund2022; chi_Si_icb>si_max
    -> SI_ABOVE_LIQUIDUS_MAX (code 6), composition never even sweeps.
    Checked here as `si_gate_pass` and folded into full_head_accept for
    S+Si rows (a v1.0.5 root for an S+Si composition HEAD would never
    even have attempted sweeping cannot be "accepted" by HEAD).

PRECONDITION CONFIRMED (item31c, before any pilot row was run): the actual
source population for this phase (item18a's main_manifest.csv, which
item30/31/31b's full-rerun population derives from) is 100% liquidus_eq=
'Edmund' -- `design.py:108` hardcodes 'Edmund' when writing every manifest
row; `cut -d, -f4 main_manifest.csv | sort -u` confirms only 'Edmund' (plus
the header) appears. There is no Steinbruegge stratification available in
this population; this verifier still reads liquidus_eq per-row (future-
proof, correct) but every row in the actual item31c sample will in practice
carry liquidus_eq='Edmund'.

Usage: python3 verify_v105_root_v3.py <json_task_file> <json_out_file>
task = {CMR2, CMC, light, liquidus_eq, chi_Si_icb(or null), ricb_m, v:[5 floats]}
"""
import sys, json, os
task = json.load(open(sys.argv[1]))
CMR2 = task['CMR2']; CMC = task['CMC']; light = task['light']
liquidus_eq = task['liquidus_eq']
chi = task.get('chi_Si_icb')
ricb_m = task['ricb_m']; v = task['v']
out_file = sys.argv[2]

if liquidus_eq not in ('Edmund', 'Steinbruegge'):
    raise ValueError('liquidus_eq must be Edmund or Steinbruegge (got %r)' % (liquidus_eq,))

sys.argv = ['main.py', 'p', str(CMR2), str(CMC), light, liquidus_eq] + ([str(chi)] if light == 'S+Si' else [])
import numpy as np
import planet_input
import shootp as lc
import globalvar as gv
from globalvar import CMC as GCMC  # noqa: confirm globalvar actually parsed argv

param = planet_input.planet('p', float(CMR2), light, liquidus_eq)
param['CmC'] = float(CMC)
scale = param['scale']; rhocr = param['rhocr']; rh = param['rh']
ricb_nd = ricb_m / scale['a']

out = dict(task)
try:
    # --- S+Si pre-sweep gate (driverp.py:137-149), radius-independent ---
    si_gate_pass = True
    si_max_gate = None
    if light == 'S+Si':
        si_max_gate = gv.max_Si_Steinbruegge2020 if liquidus_eq == 'Steinbruegge' else gv.max_Si_Edmund2022
        si_gate_pass = bool(float(chi) <= si_max_gate)

    f, r, yy, fout, err0 = lc.shoot_mercmodel(v, ricb_nd, rhocr, rh, param, scale)
    f = np.asarray(f, dtype=float)
    fout_arr = np.asarray(fout, dtype=float)
    normf = float(np.linalg.norm(f))
    rcmb_nd = v[2]
    rcmb_m = rcmb_nd * scale['a']
    chi_li_icb = v[4]
    chi_li_profile = np.asarray(yy[5], dtype=float)
    Picb = float(fout[0])
    if light == 'Si':
        chi_max = gv.max_Si_Steinbruegge2020 if liquidus_eq == 'Steinbruegge' else gv.max_Si_Edmund2022
    else:
        chi_max = 0.11 + 0.187 * np.exp(-0.065 * Picb * 1e-9)

    # --- Check 1: mercmodel_box (pie/shootp.py:319-358), CHI_MIN=None ---
    finite_f = bool(np.all(np.isfinite(f)))
    finite_fout = bool(np.all(np.isfinite(fout_arr)))
    box_finite_ok = finite_f and finite_fout
    box_rcmb_ok = bool(rcmb_nd > ricb_nd)
    box_chimax_ok = bool(chi_li_icb <= chi_max)
    box_pass = box_finite_ok and box_rcmb_ok and box_chimax_ok

    # --- Check 2: driverp.py:287-288, full converged chi_li profile ---
    chi_profile_negative = bool((chi_li_profile < 0).any())

    # --- Check 3: driverp.py:252, dimensional rs[k] >= rcmb ---
    ricb_ge_rcmb_final = bool(ricb_m >= rcmb_m)

    full_head_accept = (si_gate_pass and box_pass and (not chi_profile_negative)
                         and (not ricb_ge_rcmb_final))

    out.update(status='ok', normf=normf, f=list(f),
               rcmb_m=float(rcmb_m), chi_li_icb=float(chi_li_icb), Picb_Pa=Picb,
               chi_max=float(chi_max), err0=bool(err0),
               liquidus_eq=liquidus_eq,
               si_gate_pass=si_gate_pass, si_max_gate=(float(si_max_gate) if si_max_gate is not None else None),
               finite_f=finite_f, finite_fout=finite_fout,
               box_finite_ok=box_finite_ok, box_rcmb_ok=box_rcmb_ok,
               box_chimax_ok=box_chimax_ok, box_pass=box_pass,
               chi_li_profile_min=float(chi_li_profile.min()),
               chi_profile_negative=chi_profile_negative,
               ricb_ge_rcmb_final=ricb_ge_rcmb_final,
               full_head_accept=full_head_accept,
               admissible=box_pass)
except BaseException as e:
    out.update(status='exception', exc=type(e).__name__, message=str(e)[:400])
json.dump(out, open(out_file, 'w'), indent=1, default=str)
print(json.dumps(out, default=str))
