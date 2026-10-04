"""Item 31 pilot: independent residual + admissibility recheck of a v1.0.5
Newton root, using v1.0.5's OWN shoot_mercmodel (not HEAD's), run in this
scratch copy of the vendored src/ (never the read-only zenodo tree).
Usage: python3 verify_v105_root.py <json_task_file> <json_out_file>
task = {CMR2, CMC, light, chi_Si_icb(or null), ricb_m, v:[5 floats]}
"""
import sys, json, os
task = json.load(open(sys.argv[1]))
CMR2 = task['CMR2']; CMC = task['CMC']; light = task['light']
chi = task.get('chi_Si_icb')
ricb_m = task['ricb_m']; v = task['v']
out_file = sys.argv[2]  # capture BEFORE sys.argv is reassigned below

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
    normf = float(np.linalg.norm(f))
    rcmb_m = v[2] * scale['a']
    chi_li_icb = v[4]
    Picb = float(fout[0])
    if light == 'Si':
        import globalvar as gv
        chi_max = gv.max_Si_Edmund2022
    else:
        chi_max = 0.11 + 0.187 * np.exp(-0.065 * Picb * 1e-9)
    # Match pie/shootp.py::mercmodel_box EXACTLY (CHI_MIN=None, no lower
    # bound on chi -- see that function's docstring): admissible requires
    # finite f/fout (guaranteed here, we already have f), rcmb>ricb, and
    # chi<=chi_max only. Do NOT add a chi>=0 floor here; HEAD's own live
    # rejection rule does not have one.
    admissible = bool(chi_li_icb <= chi_max) and bool(rcmb_m > ricb_m) and bool(np.all(np.isfinite(f)))
    out.update(status='ok', normf=normf, f=list(np.asarray(f, dtype=float)),
               rcmb_m=float(rcmb_m), chi_li_icb=float(chi_li_icb), Picb_Pa=Picb,
               chi_max=float(chi_max), admissible=admissible, err0=bool(err0))
except BaseException as e:
    out.update(status='exception', exc=type(e).__name__, message=str(e)[:400])
json.dump(out, open(out_file, 'w'), indent=1, default=str)
print(json.dumps(out, default=str))
