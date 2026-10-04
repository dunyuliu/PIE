"""item31b CORRECTED verifier: reproduces ALL THREE of HEAD's production
acceptance checks, not just mercmodel_box (the item31 pilot's gap that the
conductor flagged):

  1. pie/shootp.py::mercmodel_box (mid-solve trial rejection): finite f AND
     finite fout (BOTH -- the original item31 verifier only checked f, a
     gap lars-eriksson found), rcmb<=ricb, chi>chi_max, CHI_MIN=None (no
     chi>=0 floor at this stage).
  2. pie/driverp.py:287-288 post-convergence check: (chi_li<0).any() over
     the FULL converged radial chi_li profile (yy[5]), not just the ICB
     value v[4]. This is the check that actually enforces chi>=0 and is
     what confounded the original item31 pilot's "over-constrains" count.
  3. pie/driverp.py:252 rs[k]>=rcmb physical-domain check, evaluated on the
     final (dimensional, meters) converged rcmb -- distinct code path from
     mercmodel_box's own (non-dimensional, mid-solve) rcmb<=ricb test, even
     though on a converged root the two should agree to roundoff.

A v1.0.5 root counts as "HEAD's production code would accept it" only if
it passes ALL THREE (full_head_accept). Any one failing -> HEAD-correctly-
-rejects at that check.

Usage: python3 verify_v105_root_v2.py <json_task_file> <json_out_file>
task = {CMR2, CMC, light, chi_Si_icb(or null), ricb_m, v:[5 floats]}
"""
import sys, json, os
task = json.load(open(sys.argv[1]))
CMR2 = task['CMR2']; CMC = task['CMC']; light = task['light']
chi = task.get('chi_Si_icb')
ricb_m = task['ricb_m']; v = task['v']
out_file = sys.argv[2]

sys.argv = ['main.py', 'p', str(CMR2), str(CMC), light, 'Edmund'] + ([str(chi)] if light == 'S+Si' else [])
import numpy as np
import planet_input
import shootp as lc
from globalvar import CMC as GCMC  # noqa: confirm globalvar actually parsed argv

param = planet_input.planet('p', float(CMR2), light, 'Edmund')
param['CmC'] = float(CMC)
scale = param['scale']; rhocr = param['rhocr']; rh = param['rh']
ricb_nd = ricb_m / scale['a']

out = dict(task)
try:
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
        import globalvar as gv
        chi_max = gv.max_Si_Edmund2022
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

    full_head_accept = box_pass and (not chi_profile_negative) and (not ricb_ge_rcmb_final)

    out.update(status='ok', normf=normf, f=list(f),
               rcmb_m=float(rcmb_m), chi_li_icb=float(chi_li_icb), Picb_Pa=Picb,
               chi_max=float(chi_max), err0=bool(err0),
               finite_f=finite_f, finite_fout=finite_fout,
               box_finite_ok=box_finite_ok, box_rcmb_ok=box_rcmb_ok,
               box_chimax_ok=box_chimax_ok, box_pass=box_pass,
               chi_li_profile_min=float(chi_li_profile.min()),
               chi_profile_negative=chi_profile_negative,
               ricb_ge_rcmb_final=ricb_ge_rcmb_final,
               full_head_accept=full_head_accept,
               # retained for continuity with the superseded original pilot verifier
               admissible=box_pass)
except BaseException as e:
    out.update(status='exception', exc=type(e).__name__, message=str(e)[:400])
json.dump(out, open(out_file, 'w'), indent=1, default=str)
print(json.dumps(out, default=str))
