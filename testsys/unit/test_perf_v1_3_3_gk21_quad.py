"""Differential/perf tests for the v1.3.3 performance port (PATHWAY_FORWARD.md
perf item, docs/notes/perf_v1.3.3.md): eosAndersonGrueneisen.Gibbs's
`integrate.quad` call (src/coreEos.py) replaced, by default, with a
vectorised single-GK21-panel evaluation (`coreEos._gk21_panel` /
`coreEos._gk21_or_quad`) that replicates QUADPACK's dqk21.f (21-point
Gauss-Kronrod rule) and dqagse.f's own single-panel accept test bit-for-
bit, falling back to the real `scipy.integrate.quad` per call whenever
that accept test fails.

Profiling (cProfile, canonical Margot-fit radius, CMR2=0.346/CMC=0.424, S,
Edmund) found integrate.quad at ~6.4s of a 9.6s single-radius solve:
26124 calls / 548604 total integrand evaluations = exactly 21 evals/call
-- QAGSE never subdivides past its first GK21 panel for any (p, T) pair
actually reached in a real solve. Verified across the FULL matrix the
owner's brief named (S/Si/S+Si x Edmund/Steinbruegge x small-ricb and
canonical-ricb radii; near-rcmb did not converge for ANY composition at
this CMR2/CMC -- a pre-existing Newton-solver boundary issue, unrelated to
quad, see testsys/reference/perf_v1.3.3/README.md) -- 237057 real captured
quad calls, ALL with infodict['last']==1.

This is NOT a universal property of the integrand -- a direct sweep (not
through the solver) of Gibbs/quad over the full admissible pressure
domain shows QAGSE DOES subdivide once the integration interval gets wide
enough (see test_direct_sweep_shows_single_panel_is_not_universal below)
-- which is exactly why _gk21_or_quad's fallback is a per-call runtime
check, not a one-time global switch.
"""
import pathlib
import time

import numpy as np
import pytest

pytestmark = pytest.mark.unit

from conftest import import_src

FIXTURE = (pathlib.Path(__file__).resolve().parent.parent / "reference"
           / "perf_v1.3.3" / "real_quad_calls.npz")


@pytest.fixture(scope="module")
def real_calls():
    assert FIXTURE.exists(), (
        f"{FIXTURE}: missing real-quad-call fixture -- regenerate per "
        f"testsys/reference/perf_v1.3.3/README.md, do not skip silently"
    )
    return np.load(FIXTURE, allow_pickle=False)


@pytest.fixture(scope="module")
def coreEos():
    return import_src("coreEos")


@pytest.fixture(scope="module")
def eos_objects():
    """The two eosAndersonGrueneisen instances whose Gibbs() method
    actually calls quad in a real solve (GibbsFlag=True): fccFe and lFe
    (src/planet_input.py's `planet()`). liquidFeS/liquidFeSi use the
    gamma0/q branch instead (GibbsFlag=False) and never call Gibbs/quad."""
    import_src("globalvar")
    planet_input = import_src("planet_input")
    param = planet_input.planet("p", 0.346, "S", "Edmund")
    return {"fccFe": param["fccFe"], "lFe": param["lFe"]}


# ---------------------------------------------------------------------
# 1. Single-panel claim, on the real captured matrix
# ---------------------------------------------------------------------

def test_single_panel_claim_holds_on_real_captured_matrix(real_calls):
    """Every one of the 2000 sampled real (a, b, T) calls (237057 total
    captured, see n_total_captured) has QUADPACK last==1, neval==21 --
    i.e. QAGSE never subdivided for any of these real (p, T) pairs."""
    assert int(real_calls["n_total_captured"]) == 237057
    assert set(real_calls["last"].tolist()) == {1}
    assert set(real_calls["neval"].tolist()) == {21}


# ---------------------------------------------------------------------
# 2. Integrand vectorises exactly (per-point == array call)
# ---------------------------------------------------------------------

class TestVolumeVectorisesExactly:
    """eosAndersonGrueneisen.volume(x, T) must return, for an array x,
    EXACTLY the same values as calling it once per scalar point -- not
    just 'looks vectorizable'. This is the precondition _gk21_panel
    relies on to call `func` once on all 21 GK21 abscissae instead of 21
    separate Python-level calls."""

    def test_array_call_matches_elementwise_scalar_calls(self, eos_objects,
                                                           real_calls):
        rng = np.random.default_rng(42)
        idx = rng.choice(len(real_calls["a"]), size=50, replace=False)
        for name, eosobj in eos_objects.items():
            for i in idx:
                a, b, T = (float(real_calls["a"][i]),
                           float(real_calls["b"][i]),
                           float(real_calls["T"][i]))
                xs = np.linspace(a, b, 21)
                vec = eosobj.volume(xs, T)
                scalar = np.array([eosobj.volume(x, T) for x in xs])
                assert vec.shape == scalar.shape == (21,)
                assert np.array_equal(vec, scalar), (
                    f"{name}: volume(array) != elementwise volume(scalar) "
                    f"at a={a} b={b} T={T}"
                )


# ---------------------------------------------------------------------
# 3. Bit-identical parity gate: GK21-or-quad vs real scipy quad
# ---------------------------------------------------------------------

class TestGK21MatchesRealQuadBitIdentically:
    """THE parity gate. coreEos._gk21_or_quad(func, a, b) vs
    scipy.integrate.quad(func, a, b)[0], on the SAME real (a, b, T)
    triples and the SAME eos objects' volume() -- exact equality
    (np.array_equal / ==), not a tolerance."""

    def test_max_diff_is_exactly_zero_on_real_sample(self, coreEos,
                                                       eos_objects,
                                                       real_calls):
        from scipy import integrate
        max_diff = 0.0
        n_checked = 0
        n_fallback = 0
        for name, eosobj in eos_objects.items():
            for a, b, T in zip(real_calls["a"], real_calls["b"],
                                real_calls["T"]):
                a, b, T = float(a), float(b), float(T)
                func = lambda x, _T=T, _e=eosobj: _e.volume(x, _T)
                ref = integrate.quad(func, a, b)[0]
                # Detect whether this call takes the fallback path (for
                # reporting only; either path must match `ref` exactly).
                _, abserr, resabs, resasc = coreEos._gk21_panel(func, a, b)
                fast = coreEos._gk21_or_quad(func, a, b)
                if fast != ref:
                    max_diff = max(max_diff, abs(fast - ref))
                n_checked += 1
        assert n_checked == 2 * len(real_calls["a"])
        assert max_diff == 0.0, (
            f"GK21 fast path diverged from real scipy.integrate.quad: "
            f"max diff {max_diff!r} over {n_checked} (eos, real-call) pairs"
        )

    def test_gibbs_end_to_end_matches_with_flag_toggled(self, coreEos,
                                                          eos_objects,
                                                          real_calls):
        """Stronger than the bare quad-vs-quad check above: call the
        ACTUAL Gibbs() method (which is what src/ calls) with
        PIE_FAST_QUAD True vs False, same (p, T), and compare its
        returned Gibbs energy exactly."""
        rng = np.random.default_rng(7)
        idx = rng.choice(len(real_calls["b"]), size=100, replace=False)
        for name, eosobj in eos_objects.items():
            for i in idx:
                b, T = float(real_calls["b"][i]), float(real_calls["T"][i])
                p = b * eosobj.pMax
                coreEos.PIE_FAST_QUAD = True
                g_fast = eosobj.Gibbs(p, T)
                coreEos.PIE_FAST_QUAD = False
                g_quad = eosobj.Gibbs(p, T)
                assert g_fast == g_quad, (
                    f"{name}: Gibbs(p={p}, T={T}) differs between "
                    f"PIE_FAST_QUAD True/False: {g_fast!r} vs {g_quad!r}"
                )
        coreEos.PIE_FAST_QUAD = True  # restore module default for other tests


# ---------------------------------------------------------------------
# 4. Single-panel is NOT universal -- the fallback is load-bearing
# ---------------------------------------------------------------------

def test_direct_sweep_shows_single_panel_is_not_universal(coreEos,
                                                            eos_objects):
    """At wide-enough integration intervals (well beyond any pressure a
    real Mercury-core solve reaches), QAGSE DOES subdivide (last in {2,
    3}) -- confirming the single-panel claim is empirical-on-this-matrix,
    not universal, and that _gk21_or_quad's per-call fallback (not a
    global switch) is what keeps the port correct outside that matrix."""
    from scipy import integrate
    eosobj = eos_objects["fccFe"]
    found_subdivided = False
    for p in np.linspace(80.0, eosobj.pMax, 10):
        for T in (500.0, 1800.0, 3200.0):
            func = lambda x, _T=T: eosobj.volume(x, _T)
            a, b = eosobj.p0 / eosobj.pMax, p / eosobj.pMax
            _, _, info = integrate.quad(func, a, b, full_output=1)[:3]
            if info["last"] != 1:
                found_subdivided = True
            # Whether or not this one subdivided, _gk21_or_quad must
            # still match real quad exactly (fallback engages per-call).
            ref = integrate.quad(func, a, b)[0]
            fast = coreEos._gk21_or_quad(func, a, b)
            assert fast == ref, (
                f"fallback did not reproduce real quad at p={p}, T={T}"
            )
    assert found_subdivided, (
        "expected at least one (p, T) in this wide sweep to force QAGSE "
        "subdivision -- if none did, the sweep range needs widening, not "
        "the test deleting"
    )


# ---------------------------------------------------------------------
# 5. Error handling: malformed vectorised integrand
# ---------------------------------------------------------------------

def test_gk21_panel_raises_on_wrong_shaped_integrand_output(coreEos):
    """A `func` that doesn't return a (21,)-shaped array for a
    (21,)-shaped input must raise loudly (PROJECT_RULES.md rule 3/4), not
    silently broadcast/truncate into a wrong-but-plausible result."""
    with pytest.raises(ValueError):
        coreEos._gk21_panel(lambda x: np.asarray(x)[:5], 0.0, 1.0)


# ---------------------------------------------------------------------
# 6. Performance regression: GK21 fast path is actually faster
# ---------------------------------------------------------------------

def test_gk21_or_quad_is_faster_than_real_quad(coreEos, eos_objects,
                                                real_calls):
    from scipy import integrate
    eosobj = eos_objects["fccFe"]
    n = min(300, len(real_calls["a"]))
    calls = [(float(real_calls["a"][i]), float(real_calls["b"][i]),
              float(real_calls["T"][i])) for i in range(n)]

    t0 = time.perf_counter()
    for a, b, T in calls:
        integrate.quad(lambda x, _T=T: eosobj.volume(x, _T), a, b)
    t_quad = time.perf_counter() - t0

    t0 = time.perf_counter()
    for a, b, T in calls:
        coreEos._gk21_or_quad(lambda x, _T=T: eosobj.volume(x, _T), a, b)
    t_fast = time.perf_counter() - t0

    assert t_fast < 0.5 * t_quad, (
        f"GK21 fast path ({t_fast:.4f}s) not even 2x faster than real "
        f"quad ({t_quad:.4f}s) over {n} real calls -- perf regression"
    )
