"""Truth anchor (PROJECT_RULES.md rule 5, PATHWAY_FORWARD.md item 21):
compares PIE's Fe-S and Fe-Si present-day core solves against the
vendored Steinbruegge et al. (2020, doi:10.1029/2020GL089895)
predecessor code (`tests/reference/steinbruegge2020_8dc6466/`,
pinned commit 8dc64663c574bc9dc1b3ecbb74252fbb3b1a2383, MIT). This is
INDEPENDENT CODE (a different repository, not a copy of `src/`), so
agreement is a truth-anchor pass in `PROJECT_RULES.md` rule 5's sense,
not a same-code regression check -- see
`docs/dev/notes/steinbruegge_anchor_2026-09-30.md` for the full physics
diff this file's tolerances are derived from (measured worst-case
differences, not assumed noise floors).

Units of every tolerance below (PROJECT_RULES.md rule 2 -- state units
explicitly rather than assume a scale matches):
  rcmb, r         -- metres
  rhom, rho       -- kg/m^3
  Pcmb, Picb, P   -- Pa
  Tcmb, T         -- K
  chi_li_icb, chi_li_in, chi_li -- dimensionless mass fraction
  g               -- m/s^2 (gravitational acceleration)
  core_mass       -- kg

Both sides compute in RAW SI UNITS end to end (verified explicitly,
task brief subtlety #1): PIE's `src/shootp.py` calls
`get_mass_core(rs*a, rhos*rhomean)` -- physical metres and kg/m^3, not
the normalized `rs`/`rhos` fit variables -- and
`tests/conftest.py::solve_full_model` re-dimensionalises every
scalar/profile the same way before returning it (`r_phys = scale['a']
* r`, `rho_phys = rhomean * yy[4]`, etc.). The vendored
`run_steinbruegge_case.py` does the identical re-dimensionalisation
using the vendored code's OWN `scale`/`rhomean` (see that file's
`solve_one_case`). A spot check on this box (2026-09-30, S, ricb=10 m):
both sides report rcmb ~1.96e6 m (~1960 km) and rhom ~3024 kg/m^3 --
sane physical magnitudes, not a normalized fraction that would read
as ~0.8.

Tolerances (measured worst-case on this box, 2026-09-30, 3 runs each
at ricb in {10 m, 500 km, 1000 km} for Fe-S, 1 run at ricb=10 m for
Fe-Si -- see docs/dev/notes/steinbruegge_anchor_2026-09-30.md "Results"):
  Fe-S:  rcmb <=1.03e-5 m (bound 0.01 m), rhom <=1.44e-11 rel (bound
         1e-8), Pcmb/Picb <=4.14e-11 rel (bound 1e-7), Tcmb
         <=4.3e-7 K (bound 1e-3 K), chi_li_icb/chi_li_in <=5.8e-11
         (bound 1e-7), fluid-node profiles <=4.6e-10 rel (bound
         1e-7), chi_li <=3.4e-11 abs (bound 1e-6).
  Fe-Si (ricb=10 m only -- see module docstring on why not larger
         ricb): rcmb=0.245 m (bound 1 m), Tcmb=1.1e-3 K (bound
         0.01 K), chi_li_icb=6.9e-7 (bound 1e-5).
Every bound above is the measured worst case rounded up by roughly an
order of magnitude or more, not an assumed number.

Fe-Si is anchored ONLY at ricb=10 m. `docs/dev/notes/steinbruegge_anchor_
2026-09-30.md` "Physics diff" item 1 documents that at larger ricb the
vendored code's Fe-Si branch is internally inconsistent (pure fcc-Fe in
the inner-core ODE but FeSi density in the MoI polynomial), while PIE's
`eos.eosInnerCore` is consistently FeSi throughout -- so PIE and the
vendored code are EXPECTED to diverge there (up to ~1% at 1000 km, per
the note), and that divergence is not a PIE bug. Asserting parity at
larger Fe-Si ricb would be asserting the vendored code's inconsistency
onto PIE; not done here.

core_mass has no vendored-code counterpart (`docs/dev/notes/...` "PIE-only
outputs") -- the `test_core_mass_quadrature_bias_is_bounded` case below
checks it against an INDEPENDENT oracle instead (`numpy.trapz` on the
same PIE-computed density/radius profile PIE's own `get_mass_core`
integrates), documenting PATHWAY_FORWARD.md item 12 / item 20's known
~0.3% quadrature bias as a bound, not fixing it (constraint: no `src/`
edits).
"""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.parity]

from pielib import solve_full_model

REF_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "reference",
    "steinbruegge2020_8dc6466",
)
RUNNER = os.path.join(REF_DIR, "run_steinbruegge_case.py")

CMR2 = 0.333
CMC = 0.148 / 0.333
NC_FLUID = 51  # libcore.py's/shootp.py's own hard-coded fluid-core RK4 node count


def run_steinbruegge(li_el, ricb_m, tmp_path):
    """Run the vendored Steinbruegge code in ITS OWN subprocess (never
    imported into this process, which has already imported PIE's
    `src/coreEos` via `conftest.solve_full_model` above -- the two
    modules share the name `coreEos` and a same-process import would
    silently pick whichever the import cache saw first, see this
    file's module docstring and `run_steinbruegge_case.py`'s own
    docstring)."""
    out_path = os.path.join(str(tmp_path), "stb_%s_%s.json" % (li_el, ricb_m))
    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"
    env["MPLBACKEND"] = "Agg"
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    proc = subprocess.run(
        [sys.executable, RUNNER, li_el, str(ricb_m), out_path],
        cwd=REF_DIR, env=env, timeout=120,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert proc.returncode == 0, (
        "vendored Steinbruegge run_steinbruegge_case.py failed "
        "(li_el=%r ricb_m=%r): %s" % (li_el, ricb_m, proc.stdout)
    )
    with open(out_path) as fh:
        return json.load(fh)


def _assert_close(name, pie_val, stb_val, bound, kind, context):
    """`not (diff > bound)`, never `diff <= bound`: a NaN diff must
    FAIL loudly, not silently pass a comparison NaN always evaluates
    False for (mirrors `conftest.assert_scalars_match`'s own comment)."""
    if kind == "atol":
        diff = abs(pie_val - stb_val)
        bound_val = bound
    else:
        assert kind == "rtol"
        diff = abs(pie_val - stb_val) / abs(stb_val)
        bound_val = bound
    assert not (diff > bound_val), (
        "%s%s: PIE=%r vendored-Steinbruegge=%r diff=%r exceeds %s=%r" %
        (context, name, pie_val, stb_val, diff, kind, bound_val)
    )


FE_S_SCALAR_TOL = [
    ("rcmb", "atol", 0.01),
    ("rhom", "rtol", 1e-8),
    ("Pcmb", "rtol", 1e-7),
    ("Picb", "rtol", 1e-7),
    ("Tcmb", "atol", 1e-3),
    ("chi_li_icb", "atol", 1e-7),
    ("chi_li_in", "atol", 1e-7),
]


@pytest.mark.parametrize("ricb_m", [10.0, 500_000.0, 1_000_000.0])
def test_fe_s_matches_steinbruegge_2020(ricb_m, tmp_path):
    """Fe-S at 3 inner-core radii spanning the full sampled range (10 m
    to 1000 km): every scalar PIE and the vendored code both compute
    must agree to the tolerances derived in this file's module
    docstring, and isnow/isnowcmb (categorical snow-classification
    labels) must match EXACTLY."""
    pie = solve_full_model(CMR2, CMC, "S", "Steinbruegge", ricb_m)
    stb = run_steinbruegge("S", ricb_m, tmp_path)
    context = "Fe-S ricb=%s m, " % ricb_m

    for field, kind, bound in FE_S_SCALAR_TOL:
        _assert_close(field, pie["scalars"][field], stb["scalars"][field],
                      bound, kind, context)

    for field in ("isnow", "isnowcmb"):
        assert pie["scalars"][field] == stb["scalars"][field], (
            "%s%s: categorical field must match EXACTLY (PIE=%r "
            "vendored=%r)" % (context, field, pie["scalars"][field],
                               stb["scalars"][field])
        )


@pytest.mark.parametrize("ricb_m", [10.0, 500_000.0, 1_000_000.0])
def test_fe_s_fluid_node_profiles_match_steinbruegge_2020(ricb_m, tmp_path):
    """Fe-S fluid-core radial profiles (the fixed 51-node RK4 grid,
    NOT the adaptive-step solid inner-core grid -- see module
    docstring on why the solid segment is excluded from a point-wise
    compare) match to rtol=1e-7 (rho/P/T/g) or atol=1e-6 (chi_li,
    which starts at/near zero at the ICB where a relative bound would
    be meaningless)."""
    pie = solve_full_model(CMR2, CMC, "S", "Steinbruegge", ricb_m)
    stb = run_steinbruegge("S", ricb_m, tmp_path)
    context = "Fe-S ricb=%s m, " % ricb_m

    pie_r = np.asarray(pie["profiles"]["r"][-NC_FLUID:])
    stb_r = np.asarray(stb["profiles"]["r"])
    assert pie_r.shape == stb_r.shape, (
        "%sfluid-node count differs: PIE %s vs vendored %s" %
        (context, pie_r.shape, stb_r.shape)
    )

    for field in ("r", "rho", "P", "T", "g"):
        pie_v = np.asarray(pie["profiles"][field][-NC_FLUID:])
        stb_v = np.asarray(stb["profiles"][field])
        rel = np.abs(pie_v - stb_v) / np.abs(stb_v)
        worst = float(np.max(rel))
        assert not (worst > 1e-7), (
            "%sfluid-node profile '%s': worst rel diff=%r at index %d "
            "exceeds rtol=1e-7" %
            (context, field, worst, int(np.argmax(rel)))
        )

    pie_chi = np.asarray(pie["profiles"]["chi_li"][-NC_FLUID:])
    stb_chi = np.asarray(stb["profiles"]["chi_li"])
    abs_diff = np.abs(pie_chi - stb_chi)
    worst_chi = float(np.max(abs_diff))
    assert not (worst_chi > 1e-6), (
        "%sfluid-node profile 'chi_li': worst abs diff=%r at index %d "
        "exceeds atol=1e-6" %
        (context, worst_chi, int(np.argmax(abs_diff)))
    )


def test_fe_si_matches_steinbruegge_2020_at_ricb_10m(tmp_path):
    """Fe-Si at ricb=10 m ONLY -- see module docstring for why larger
    Fe-Si ricb is not anchored here (an attributed, documented
    inner-core EOS difference in the vendored code, not a PIE bug).
    At ricb=10 m the solid inner core is negligible in extent, so the
    two codes' differing inner-core EOS choice has no room to diverge
    them yet."""
    ricb_m = 10.0
    pie = solve_full_model(CMR2, CMC, "Si", "Steinbruegge", ricb_m)
    stb = run_steinbruegge("Si", ricb_m, tmp_path)
    context = "Fe-Si ricb=%s m, " % ricb_m

    _assert_close("rcmb", pie["scalars"]["rcmb"], stb["scalars"]["rcmb"],
                  1.0, "atol", context)
    _assert_close("Tcmb", pie["scalars"]["Tcmb"], stb["scalars"]["Tcmb"],
                  0.01, "atol", context)
    _assert_close("chi_li_icb", pie["scalars"]["chi_li_icb"],
                  stb["scalars"]["chi_li_icb"], 1e-5, "atol", context)


def test_core_mass_quadrature_bias_is_bounded():
    """`get_mass_core` (PATHWAY_FORWARD.md item 12/20) is a
    right-endpoint shell sum with a documented ~0.3% low bias vs
    `numpy.trapz` on the SAME density/radius profile it integrates --
    an INDEPENDENT oracle (a different quadrature rule applied to
    PIE's own output, not a copy of `get_mass_core`'s own arithmetic).
    This asserts the bias stays within TODAY's measured bound (a
    documented, not-yet-fixed bias -- PROJECT_RULES.md rule 2 requires
    it be checked and stated, not fixed here; `src/libCore.py` is not
    touched by this test suite). Measured worst case on this box,
    2026-09-30, ricb in {10 m, 500 km, 1000 km}: 0.317% (10 m). Bound
    is set an order of magnitude above the measured 0.32% worst case,
    matching the note's own recommended <4e-3."""
    for ricb_m in (10.0, 500_000.0, 1_000_000.0):
        pie = solve_full_model(CMR2, CMC, "S", "Steinbruegge", ricb_m)
        r = np.asarray(pie["profiles"]["r"])
        rho = np.asarray(pie["profiles"]["rho"])
        _trapz = getattr(np, "trapezoid", None) or np.trapz
        mass_trapz = _trapz(4 * np.pi * rho * r ** 2, r)
        core_mass = pie["scalars"]["core_mass"]
        rel_bias = abs(core_mass - mass_trapz) / mass_trapz
        assert not (rel_bias > 4e-3), (
            "ricb=%s m: PIE core_mass=%r vs trapz oracle=%r, rel "
            "bias=%r exceeds the documented 4e-3 bound (see "
            "docs/dev/notes/steinbruegge_anchor_2026-09-30.md 'Core "
            "mass' finding) -- if this bias got WORSE, something "
            "regressed; if it got better, PATHWAY_FORWARD.md item "
            "12/20 may be closeable, tighten this bound then, don't "
            "just delete the check" % (ricb_m, core_mass, mass_trapz,
                                        rel_bias)
        )
