"""PATHWAY_FORWARD.md item 23(c): is PIE's Fe-Si disagreement with the
vendored Steinbruegge et al. (2020, doi:10.1029/2020GL089895) code at
`ricb > 10 m` fully explained by `docs/notes/steinbruegge_anchor_
2026-09-30.md` physics-diff item 1 (the published code uses pure
fcc-Fe in its inner-core ODE / r0-density call, but its OWN FeSi
density in the moment-of-inertia polynomial 30 lines later -- an
internal inconsistency, not a PIE bug)?

This file tests a PATCHED COPY of the vendored code
(`testsys/reference/steinbruegge2020_8dc6466_fesi_ic_patch/`, NOT the
read-only original -- see that directory's README.md for the exact
2-call-site patch) and shows: once the vendored code's inner-core EOS
is made internally consistent (FeSi density used BOTH at r0/in the
ODE AND in the MoI polynomial, matching PIE's own
`eos.eosInnerCore` convention in `src/shootp.py`), it matches PIE to
solver tolerance up to ricb=1000 km -- not just ricb=10 m as
`test_steinbruegge_anchor.py::test_fe_si_matches_steinbruegge_2020_at_
ricb_10m` anchors the UNPATCHED code.

Caveat on independence (read before reusing these tolerances
elsewhere): this is a weaker claim than the Fe-S anchor, which needs
NO patching to match PIE from a cold start. Patching one codebase's
inner-core EOS convention to match the other's, then observing
agreement, demonstrates "the disagreement is fully attributed to the
one documented EOS choice", not "two independently-written codebases
agree from a cold start" -- the patched tree is still substantively
the SAME third-party solver (shooting method, Newton iteration, EOS
classes, melting curves) as the unpatched one. The companion test
`test_fe_si_patch_explains_the_unpatched_disagreement` below locks in
the OTHER half of the claim: that the unpatched code's disagreement
with PIE is large and grows with ricb (i.e. the patch is doing real
work, not coincidentally landing both sides in the same noise floor).

Units (PROJECT_RULES.md rule 2): rcmb, r -- metres; rhom, rho --
kg/m^3; Pcmb, Picb, P -- Pa; Tcmb, T -- K; chi_li_icb, chi_li_in,
chi_li -- dimensionless mass fraction; g -- m/s^2.

Tolerances below are the measured worst case (2026-10-02, this box,
4 ricb in {100 km, 500 km, 800 km, 1000 km}) rounded up to the next
power of ten above 10x the worst value seen (never an assumed noise
floor -- see this repo's PROJECT_RULES.md rule 2 / the test-gate
convention this mirrors from test_steinbruegge_anchor.py):
  rcmb:        worst |diff|=7.35e-6 m   -> atol 1e-4 m
  rhom:        worst rel=1.02e-11       -> rtol 1e-9
  Pcmb:        worst rel=2.25e-10       -> rtol 1e-8
  Picb:        worst rel=3.60e-11       -> rtol 1e-8
  Tcmb:        worst |diff|=7.00e-7 K   -> atol 1e-5 K
  chi_li_icb:  worst |diff|=1.62e-11    -> atol 1e-9
  chi_li_in:   worst |diff|=1.41e-11    -> atol 1e-9
  fluid-node profiles (rho/P/T/g): worst rel=3.16e-10 -> rtol 1e-8
  fluid-node profile chi_li:       worst |diff|=1.62e-11 -> atol 1e-9
"""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.parity]

from conftest import solve_full_model

REF_PATCHED = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "reference",
    "steinbruegge2020_8dc6466_fesi_ic_patch",
)
RUNNER_PATCHED = os.path.join(REF_PATCHED, "run_steinbruegge_case_fesi_ic_patch.py")

REF_ORIG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "reference",
    "steinbruegge2020_8dc6466",
)
RUNNER_ORIG = os.path.join(REF_ORIG, "run_steinbruegge_case.py")

CMR2 = 0.333
CMC = 0.148 / 0.333
NC_FLUID = 51

RICB_VALUES = [100_000.0, 500_000.0, 800_000.0, 1_000_000.0]


def _run_runner(runner, cwd, ricb_m, tmp_path, tag):
    out_path = os.path.join(str(tmp_path), "stb_%s_%s.json" % (tag, ricb_m))
    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"
    env["MPLBACKEND"] = "Agg"
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    proc = subprocess.run(
        [sys.executable, runner, "Si", str(ricb_m), out_path],
        cwd=cwd, env=env, timeout=120,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert proc.returncode == 0, (
        "%s failed (ricb_m=%r): %s" % (runner, ricb_m, proc.stdout)
    )
    with open(out_path) as fh:
        return json.load(fh)


def run_steinbruegge_patched(ricb_m, tmp_path):
    """Run the FeSi-inner-core-PATCHED copy, in its own subprocess
    (same module-name-clash reasoning as test_steinbruegge_anchor.py's
    run_steinbruegge, plus this patched dir ALSO clashes with the
    unpatched reference dir's own coreEos/libcore -- never import
    either into this process)."""
    return _run_runner(RUNNER_PATCHED, REF_PATCHED, ricb_m, tmp_path, "patched")


def run_steinbruegge_unpatched(ricb_m, tmp_path):
    """Run the UNPATCHED vendored code (same runner
    test_steinbruegge_anchor.py uses), for the attribution check
    below."""
    return _run_runner(RUNNER_ORIG, REF_ORIG, ricb_m, tmp_path, "unpatched")


def _assert_close(name, pie_val, stb_val, bound, kind, context):
    """`not (diff > bound)`, never `diff <= bound`: a NaN diff must
    FAIL loudly (mirrors test_steinbruegge_anchor.py's own
    _assert_close docstring/rationale)."""
    if kind == "atol":
        diff = abs(pie_val - stb_val)
    else:
        assert kind == "rtol"
        diff = abs(pie_val - stb_val) / abs(stb_val)
    assert not (diff > bound), (
        "%s%s: PIE=%r patched-Steinbruegge=%r diff=%r exceeds %s=%r" %
        (context, name, pie_val, stb_val, diff, kind, bound)
    )


FE_SI_PATCHED_SCALAR_TOL = [
    ("rcmb", "atol", 1e-4),
    ("rhom", "rtol", 1e-9),
    ("Pcmb", "rtol", 1e-8),
    ("Picb", "rtol", 1e-8),
    ("Tcmb", "atol", 1e-5),
    ("chi_li_icb", "atol", 1e-9),
    ("chi_li_in", "atol", 1e-9),
]


@pytest.mark.parametrize("ricb_m", RICB_VALUES)
def test_fe_si_matches_patched_steinbruegge_2020(ricb_m, tmp_path):
    """Fe-Si at 4 inner-core radii (100 km-1000 km, i.e. BEYOND the
    ricb=10 m limit test_steinbruegge_anchor.py's Fe-Si anchor is
    restricted to): once the vendored code's inner-core EOS
    inconsistency (physics-diff item 1) is patched out, every scalar
    agrees with PIE to solver-tolerance-scale bounds (this file's
    module docstring)."""
    pie = solve_full_model(CMR2, CMC, "Si", "Steinbruegge", ricb_m)
    stb = run_steinbruegge_patched(ricb_m, tmp_path)
    context = "Fe-Si (patched) ricb=%s m, " % ricb_m

    for field, kind, bound in FE_SI_PATCHED_SCALAR_TOL:
        _assert_close(field, pie["scalars"][field], stb["scalars"][field],
                      bound, kind, context)


@pytest.mark.parametrize("ricb_m", RICB_VALUES)
def test_fe_si_patched_fluid_node_profiles_match(ricb_m, tmp_path):
    """Fluid-core radial profiles (fixed 51-node RK4 grid -- the solid
    inner-core's adaptive LSODA grid is excluded from point-wise
    comparison for the same node-placement-artifact reason
    test_steinbruegge_anchor.py's Fe-S profile test documents)."""
    pie = solve_full_model(CMR2, CMC, "Si", "Steinbruegge", ricb_m)
    stb = run_steinbruegge_patched(ricb_m, tmp_path)
    context = "Fe-Si (patched) ricb=%s m, " % ricb_m

    pie_r = np.asarray(pie["profiles"]["r"][-NC_FLUID:])
    stb_r = np.asarray(stb["profiles"]["r"])
    assert pie_r.shape == stb_r.shape, (
        "%sfluid-node count differs: PIE %s vs patched-Steinbruegge %s" %
        (context, pie_r.shape, stb_r.shape)
    )

    for field in ("r", "rho", "P", "T", "g"):
        pie_v = np.asarray(pie["profiles"][field][-NC_FLUID:])
        stb_v = np.asarray(stb["profiles"][field])
        rel = np.abs(pie_v - stb_v) / np.abs(stb_v)
        worst = float(np.max(rel))
        assert not (worst > 1e-8), (
            "%sfluid-node profile '%s': worst rel diff=%r at index %d "
            "exceeds rtol=1e-8" %
            (context, field, worst, int(np.argmax(rel)))
        )

    pie_chi = np.asarray(pie["profiles"]["chi_li"][-NC_FLUID:])
    stb_chi = np.asarray(stb["profiles"]["chi_li"])
    abs_diff = np.abs(pie_chi - stb_chi)
    worst_chi = float(np.max(abs_diff))
    assert not (worst_chi > 1e-9), (
        "%sfluid-node profile 'chi_li': worst abs diff=%r at index %d "
        "exceeds atol=1e-9" %
        (context, worst_chi, int(np.argmax(abs_diff)))
    )


# (ricb_m, expected sign of PIE-rcmb minus unpatched-STB-rcmb, min and
# max |diff| in metres) -- measured worst case 2026-10-02, this box;
# the bound is a RANGE (not just an upper bound) because disappearance
# of the disagreement would itself be informative (either the vendored
# code changed underneath this test -- it cannot, it is pinned -- or
# this test's own patched-vs-unpatched wiring broke).
UNPATCHED_DISAGREEMENT = [
    (100_000.0, -1, 2.0, 6.0),
    (500_000.0, -1, 400.0, 700.0),
    (800_000.0, -1, 2000.0, 3500.0),
    (1_000_000.0, -1, 6000.0, 9000.0),
]


@pytest.mark.parametrize("ricb_m,sign,lo,hi", UNPATCHED_DISAGREEMENT)
def test_fe_si_patch_explains_the_unpatched_disagreement(ricb_m, sign, lo, hi, tmp_path):
    """Locks in the ATTRIBUTION, not just the fix: the UNPATCHED
    vendored code's rcmb disagreement with PIE must (a) have the
    documented sign (PIE's rcmb below the unpublished code's, i.e.
    PIE's consistently-FeSi inner core is slightly less dense than the
    published code's inconsistent one at the same ricb -- see
    docs/notes/steinbruegge_anchor_2026-09-30.md "Fe-Si as published
    vs PIE" line) and (b) fall in the measured range at each ricb. If
    this test starts FAILING because the gap shrank or vanished, that
    is NOT evidence the patch stopped mattering -- investigate before
    touching this test (PROJECT_RULES.md rule 2's "a metric moving to
    zero is not evidence of a fixed problem" rule applies here too)."""
    pie = solve_full_model(CMR2, CMC, "Si", "Steinbruegge", ricb_m)
    unpatched = run_steinbruegge_unpatched(ricb_m, tmp_path)
    diff = pie["scalars"]["rcmb"] - unpatched["scalars"]["rcmb"]
    context = "Fe-Si (vs UNPATCHED) ricb=%s m, " % ricb_m

    assert not (diff * sign < 0), (
        "%srcmb diff=%r does not have the expected sign (sign=%r) -- "
        "see docs/notes/steinbruegge_anchor_2026-09-30.md" %
        (context, diff, sign)
    )
    mag = abs(diff)
    assert not (mag < lo) and not (mag > hi), (
        "%s|rcmb diff|=%r m outside expected range [%r, %r] m -- if this "
        "shrank, the attribution in docs/notes/steinbruegge_anchor_2026-"
        "09-30.md needs re-checking before loosening this bound (rule 2: "
        "a moved metric isn't evidence of a fixed problem)" %
        (context, mag, lo, hi)
    )
