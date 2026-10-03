"""Differential/perf tests for the v1.3.3 performance port (PATHWAY_FORWARD.md
perf item, docs/notes/perf_v1.3.3.md): eosAndersonGrueneisen.Gibbs's
`integrate.quad` call (src/coreEos.py) uses, by DEFAULT since the owner's
2026-10-02 ruling (PIE_FAST_QUAD defaults to True; an explicit
PIE_FAST_QUAD=0 is the escape hatch), a vectorised single-GK21-panel
evaluation (`coreEos._gk21_panel` / `coreEos._gk21_or_quad`) that
replicates QUADPACK's dqk21.f (21-point Gauss-Kronrod rule) and
dqagse.f's own single-panel accept test bit-for-bit, falling back to the
real `scipy.integrate.quad` per call whenever that accept test fails.

On the pinned environment (numpy==1.21.5, scipy==1.8.0) GK21 is exactly
bit-identical to real quad. A first attempt at shipping this as the
default (PR #15) broke CI's fast-latest job (current numpy/scipy) with an
~8.3e-17 difference, traced to eosAndersonGrueneisen.volume's CubicSpline
not being bit-identical between a vectorised array call and
one-scalar-call-per-point on non-pinned numpy/scipy; the owner's
2026-10-02 ruling is that this bounded (not eliminated) divergence is
acceptable, so default-on ships with that divergence bounded by
GK21_PORTABLE_RTOL rather than papered over. So this test file has two
tiers: exact-equality tests that only make sense (and only run
meaningfully) on the pinned environment, and a portable relative-diff-
bound test that runs and asserts on ANY environment including
fast-latest.

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
import os
import pathlib
import time

import numpy as np
import pytest

pytestmark = pytest.mark.unit

from pielib import import_src

FIXTURE = (pathlib.Path(__file__).resolve().parent.parent / "reference"
           / "perf_v1.3.3" / "real_quad_calls.npz")

# Same pattern as testsys/integration/test_v1_2_0_invariant.py's
# _on_pinned_env: exact equality is only expected (and only measured) on
# the exact environment the GK21 port's bit-identical claim was validated
# on; off that environment we still bound the divergence, we just don't
# require it to be exactly 0.
PINNED = {"numpy": "1.21.5", "scipy": "1.8.0"}
GK21_PORTABLE_RTOL = 1e-14


def _on_pinned_env():
    import numpy, scipy
    return numpy.__version__ == PINNED["numpy"] and scipy.__version__ == PINNED["scipy"]


@pytest.fixture(scope="module")
def real_calls():
    assert FIXTURE.exists(), (
        f"{FIXTURE}: missing real-quad-call fixture -- regenerate per "
        f"testsys/reference/perf_v1.3.3/README.md, do not skip silently"
    )
    return np.load(FIXTURE, allow_pickle=False)


@pytest.fixture(scope="module")
def _loaded_planet_input():
    """ONE `import_src("planet_input")` call, module-scoped (its result is
    cached as stable object references, not re-looked-up later): `coreEos`
    and `eos_objects` below are both derived from this single load, so they
    are guaranteed to be the exact same `pie.coreEos` module instance the
    `eosAndersonGrueneisen` objects were actually built against.

    This replaced two INDEPENDENT `import_src` calls (one for a bare
    `coreEos` fixture, one inside `eos_objects` via `import_src("planet_input")`)
    -- `import_src` deletes `pie.coreEos` (and friends) from `sys.modules`
    and re-imports fresh every time it runs, so two separate calls produced
    two DIFFERENT module objects; mutating `PIE_FAST_QUAD` on one silently
    had no effect on the other's bound `Gibbs()` methods. A first fix
    (`coreEos` fixture doing `sys.modules["pie.coreEos"]` lazily, depending
    on `eos_objects`) was ALSO wrong: with `eos_objects` cached from an
    earlier test, `coreEos`'s lazy lookup could run much later, by which
    time an unrelated test in another file sharing this xdist worker could
    have called its own `import_src`/`solve_full_model` in between and
    deleted `pie.coreEos` from `sys.modules` again (`KeyError`). Capturing
    the module object HERE, in the same fixture body as the import_src
    call, immune to any later sys.modules churn, is what actually fixes it.
    Found while gating board item 28e's PR: the divergence is latent in
    `import_src`'s reload design (pre-dates this packaging change) and only
    became an observed, deterministic failure once this PR's new contract
    test (`test_dependency_pins_match.py`'s pyproject check) shifted
    pytest-xdist's `loadscope` fixture-setup/test-interleaving order enough
    to expose it.
    """
    import sys
    import_src("globalvar")
    planet_input = import_src("planet_input")
    coreEos_mod = sys.modules["pie.coreEos"]
    param = planet_input.planet("p", 0.346, "S", "Edmund")
    return coreEos_mod, {"fccFe": param["fccFe"], "lFe": param["lFe"]}


@pytest.fixture(scope="module")
def coreEos(_loaded_planet_input):
    return _loaded_planet_input[0]


@pytest.fixture(scope="module")
def eos_objects(_loaded_planet_input):
    """The two eosAndersonGrueneisen instances whose Gibbs() method
    actually calls quad in a real solve (GibbsFlag=True): fccFe and lFe
    (src/planet_input.py's `planet()`). liquidFeS/liquidFeSi use the
    gamma0/q branch instead (GibbsFlag=False) and never call Gibbs/quad."""
    return _loaded_planet_input[1]


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
    separate Python-level calls.

    This is the exact assertion that broke CI run 36881055265's
    fast-latest job during the PR #15 attempt ("AssertionError: fccFe:
    volume(array) != elementwise volume(scalar)"), with max abs diff
    ~8.3e-17 -- CubicSpline's array-call vs scalar-per-point-call is not
    bit-associative off the pinned environment. Confirmed via `gh run
    view <id> --log` that the PR-head run (36879868704, green) and the
    failing merge-SHA run (36881055265, red) resolved IDENTICAL package
    versions (numpy==2.5.3, scipy==1.18.1, pandas==3.0.6): this is
    CPU/SIMD-dependent floating-point nondeterminism across ephemeral
    GitHub-hosted runners, not a pip-resolution difference, and not
    reproducible on demand on any single fixed host -- see
    docs/notes/perf_v1.3.3.md. So, like the class below, this assertion
    is exact ONLY on the pinned environment; off it we bound the
    divergence instead of requiring exact equality."""

    def test_array_call_matches_elementwise_scalar_calls(self, eos_objects,
                                                           real_calls):
        rng = np.random.default_rng(42)
        idx = rng.choice(len(real_calls["a"]), size=50, replace=False)
        max_reldiff = 0.0
        for name, eosobj in eos_objects.items():
            for i in idx:
                a, b, T = (float(real_calls["a"][i]),
                           float(real_calls["b"][i]),
                           float(real_calls["T"][i]))
                xs = np.linspace(a, b, 21)
                vec = eosobj.volume(xs, T)
                scalar = np.array([eosobj.volume(x, T) for x in xs])
                assert vec.shape == scalar.shape == (21,)
                if _on_pinned_env():
                    assert np.array_equal(vec, scalar), (
                        f"{name}: volume(array) != elementwise volume"
                        f"(scalar) at a={a} b={b} T={T} on the pinned "
                        f"environment (numpy {PINNED['numpy']}/scipy "
                        f"{PINNED['scipy']})"
                    )
                else:
                    d = np.abs(vec - scalar)
                    rel = d / np.maximum(np.abs(scalar), 1e-300)
                    max_reldiff = max(max_reldiff, float(rel.max()))
        if not _on_pinned_env():
            # Reuses GK21_PORTABLE_RTOL rather than inventing a second
            # magic number: this is the SAME root cause (CubicSpline
            # array-vs-scalar non-associativity in
            # eosAndersonGrueneisen.volume) the constant was already
            # calibrated against -- the ~8.3e-17 absolute divergence
            # measured on CI run 36881055265, against volume values of
            # O(1) (see docs/notes/perf_v1.3.3.md), i.e. a relative
            # divergence of ~8.3e-17, ~1e5x inside this bound. On this
            # host's resolved numpy/scipy (see docs/notes/perf_v1.3.3.md
            # for the exact versions), the measured max_reldiff was
            # exactly 0.0 -- the nondeterminism is CPU/SIMD-dependent
            # across ephemeral runners and does not reproduce on every
            # host, so we keep the documented bound rather than
            # tightening it to today's (possibly lucky) zero.
            assert max_reldiff <= GK21_PORTABLE_RTOL, (
                f"volume(array) vs elementwise volume(scalar) exceeded "
                f"the portable rtol bound off the pinned environment: "
                f"max reldiff {max_reldiff!r} > {GK21_PORTABLE_RTOL}"
            )


# ---------------------------------------------------------------------
# 3. Bit-identical parity gate: GK21-or-quad vs real scipy quad
# ---------------------------------------------------------------------

class TestGK21MatchesRealQuadBitIdentically:
    """THE parity gate ON THE PINNED ENVIRONMENT. coreEos._gk21_or_quad(func,
    a, b) vs scipy.integrate.quad(func, a, b)[0], on the SAME real (a, b, T)
    triples and the SAME eos objects' volume() -- exact equality
    (np.array_equal / ==), not a tolerance. This tier only runs its strict
    assertion on numpy==1.21.5/scipy==1.8.0 (see module docstring): off that
    environment, exact equality is not expected (CubicSpline's
    vectorised-vs-scalar non-associativity), so this test reports the
    measured max diff and still enforces the portable rtol bound rather than
    silently skipping."""

    def test_max_diff_is_exactly_zero_on_real_sample(self, coreEos,
                                                       eos_objects,
                                                       real_calls):
        from scipy import integrate
        max_diff = 0.0
        max_reldiff = 0.0
        n_checked = 0
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
                    d = abs(fast - ref)
                    max_diff = max(max_diff, d)
                    max_reldiff = max(max_reldiff, d / max(abs(ref), 1e-300))
                n_checked += 1
        assert n_checked == 2 * len(real_calls["a"])
        if _on_pinned_env():
            assert max_diff == 0.0, (
                f"GK21 fast path diverged from real scipy.integrate.quad "
                f"on the pinned environment (numpy {PINNED['numpy']}/scipy "
                f"{PINNED['scipy']}): max diff {max_diff!r} over "
                f"{n_checked} (eos, real-call) pairs"
            )
        else:
            assert max_reldiff <= GK21_PORTABLE_RTOL, (
                f"GK21 fast path exceeded the portable rtol bound off the "
                f"pinned environment: max reldiff {max_reldiff!r} > "
                f"{GK21_PORTABLE_RTOL} over {n_checked} pairs"
            )

    def test_gibbs_end_to_end_matches_with_flag_toggled(self, coreEos,
                                                          eos_objects,
                                                          real_calls):
        """Stronger than the bare quad-vs-quad check above: call the
        ACTUAL Gibbs() method (which is what src/ calls) with
        PIE_FAST_QUAD True vs False, same (p, T), and compare its
        returned Gibbs energy -- exactly on the pinned environment, within
        the portable rtol bound elsewhere."""
        rng = np.random.default_rng(7)
        idx = rng.choice(len(real_calls["b"]), size=100, replace=False)
        max_reldiff = 0.0
        try:
            for name, eosobj in eos_objects.items():
                for i in idx:
                    b, T = float(real_calls["b"][i]), float(real_calls["T"][i])
                    p = b * eosobj.pMax
                    coreEos.PIE_FAST_QUAD = True
                    g_fast = eosobj.Gibbs(p, T)
                    coreEos.PIE_FAST_QUAD = False
                    g_quad = eosobj.Gibbs(p, T)
                    if _on_pinned_env():
                        assert g_fast == g_quad, (
                            f"{name}: Gibbs(p={p}, T={T}) differs between "
                            f"PIE_FAST_QUAD True/False on the pinned "
                            f"environment: {g_fast!r} vs {g_quad!r}"
                        )
                    else:
                        reldiff = abs(g_fast - g_quad) / max(abs(g_quad), 1e-300)
                        max_reldiff = max(max_reldiff, reldiff)
            if not _on_pinned_env():
                assert max_reldiff <= GK21_PORTABLE_RTOL, (
                    f"Gibbs(PIE_FAST_QUAD=True) exceeded the portable rtol "
                    f"bound off the pinned environment: max reldiff "
                    f"{max_reldiff!r} > {GK21_PORTABLE_RTOL}"
                )
        finally:
            # board item 28e hazard found while gating this PR: an assertion
            # failure anywhere in the loop above used to skip this restore,
            # leaking PIE_FAST_QUAD=False into every OTHER test that shares
            # this xdist worker process for the rest of the session (this
            # module's own global `coreEos` is one process-wide singleton).
            # Adding one new, unrelated contract test
            # (test_dependency_pins_match.py's pyproject-pin check, this PR)
            # shifted xdist's loadscope worker assignment enough to put a
            # leaking run of this test ahead of
            # TestDefaultBehaviourIsGK21On::test_gibbs_takes_gk21_path_by_default
            # in the same worker, turning a latent bug into an observed,
            # deterministic failure (`-n 0`/serial always passed; only
            # `-n <workers>` showed it). Fixed with `finally` rather than
            # reverting the triggering test, since the bug is the missing
            # restore-on-failure here, not the new test.
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


# ---------------------------------------------------------------------
# 7. Default behaviour is GK21-on: no flag set -> GK21, not a silent
#    fallback to quad (owner's 2026-10-02 ruling flips this default)
# ---------------------------------------------------------------------

class TestDefaultBehaviourIsGK21On:
    """Since the 2026-10-02 ruling, GK21 is the default; PIE_FAST_QUAD=0 is
    the explicit escape hatch back to pre-v1.3.3 real-quad-only behaviour.
    These tests prove the default actually takes the GK21 path, not merely
    that quad and GK21 happen to agree."""

    def test_module_default_flag_is_on(self, coreEos):
        assert coreEos.PIE_FAST_QUAD is True, (
            "coreEos.PIE_FAST_QUAD must default to True -- GK21 is the "
            "default integrator, PIE_FAST_QUAD=0 is the escape hatch"
        )

    def test_env_var_truth_table(self):
        """Re-import coreEos fresh (not the module-scoped fixture, which
        may have been mutated by other tests in this file) for each of
        unset / "1" / "0", and pin the exact truth table: unset->True,
        "1"->True, "0"->False. Only an explicit "0" is the escape hatch;
        unsetting the variable must NOT be read as off."""
        had_old = "PIE_FAST_QUAD" in os.environ
        old = os.environ.get("PIE_FAST_QUAD", None)
        try:
            if had_old:
                del os.environ["PIE_FAST_QUAD"]
            assert import_src("coreEos").PIE_FAST_QUAD is True, (
                "PIE_FAST_QUAD unset must resolve to True (default on)"
            )
            os.environ["PIE_FAST_QUAD"] = "1"
            assert import_src("coreEos").PIE_FAST_QUAD is True
            os.environ["PIE_FAST_QUAD"] = "0"
            assert import_src("coreEos").PIE_FAST_QUAD is False, (
                'PIE_FAST_QUAD="0" must resolve to False (explicit escape '
                "hatch)"
            )
        finally:
            if had_old:
                os.environ["PIE_FAST_QUAD"] = old
            elif "PIE_FAST_QUAD" in os.environ:
                del os.environ["PIE_FAST_QUAD"]

    def test_gibbs_takes_gk21_path_by_default(self, coreEos, eos_objects,
                                               real_calls):
        """With PIE_FAST_QUAD left at its module default (True), Gibbs()
        must call _gk21_or_quad -- not fall back to real
        scipy.integrate.quad -- confirmed by monkeypatching the real
        scipy.integrate.quad to raise if invoked on the default path (not
        the other way around: proving we no longer silently fall back to
        quad, which is the actual risk of this default flip)."""
        assert coreEos.PIE_FAST_QUAD is True
        eosobj = eos_objects["fccFe"]
        b, T = float(real_calls["b"][0]), float(real_calls["T"][0])
        p = b * eosobj.pMax

        from scipy import integrate

        def _boom(*a, **k):
            raise AssertionError(
                "default path (PIE_FAST_QUAD unset) called real "
                "scipy.integrate.quad -- default is silently falling back "
                "instead of taking the GK21 path"
            )

        orig = integrate.quad
        integrate.quad = _boom
        try:
            # Must not raise: default path never reaches real quad (the
            # per-call dqagse accept-test fallback inside _gk21_or_quad
            # is exercised elsewhere, e.g. test
            # test_direct_sweep_shows_single_panel_is_not_universal; this
            # (p, T) pair is one of the real captured single-panel calls).
            eosobj.Gibbs(p, T)
        finally:
            integrate.quad = orig
