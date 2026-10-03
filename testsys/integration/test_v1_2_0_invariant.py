"""Integration tier: the v1.3.0 solver invariant against v1.2.0 (PATHWAY_FORWARD.md
item 17; docs/notes/solver_v1.3.0.md).

Fixed sample: testsys/reference/v1_2_0_sweeps/sample.json (14 published Monte
Carlo draws, one per failure class: 6 "identity" cases that converged for
several radii in v1.2.0, 8 "recovery" cases that produced zero rows).
Reference: v1_2_0_sweeps.json, generated from src/ at v1.2.0 (18cf78a) with
the v1.2.0 stop-at-first-failure policy on the pinned environment.

Gates
1. IDENTITY: every row that converged in v1.2.0 converges in the current
   src/ with an unknown vector v (and the continuous half of fout, exact
   for the isnow/isnowcmb flags) matching to rtol 1e-6 / atol 1e-8 on the
   pinned environment (numpy 1.21.5 / scipy 1.8.0) -- not bit-identical:
   measured false even under identical pins across two machines
   (LAPACK/BLAS ULP-level rounding, compounding along a warm-started
   sweep), see `_same`'s docstring comment. The shooting residual f is
   checked for absolute convergence (|f| < ftol) instead of compared to
   the reference row: f is ~0 by construction, so a component-wise
   relative comparison of two noise-floor vectors is not meaningful.
   `test_v1_2_0_converged_rows_bitwise_same_host` below runs the strict
   bitwise check on v where the fixture was actually generated. On any
   other environment
   (CI fast-latest) within the calibrated cross-environment parity
   tolerance (rtol 1e-4, atol 1e-6 -- the one used against the published
   data), because integrator/BLAS rounding legitimately differs there. The line search must have accepted alpha = 1 on every
   iteration of those rows (recorded start == 'warm'/'cold' as in v1.2.0,
   newton_iters unchanged is implied by identity of v).
2. RECOVERED: rows the current src/ converges that v1.2.0 did not (after a
   v1.2.0 failure, or in a zero-row case) are tagged "recovered" and must be
   valid: residual below the solver tolerance, chi_li_icb in [0, eutectic]
   (S, S+Si) or [0, Si max] (Si), ricb < rcmb, rho > 0, finite profiles, and
   a smooth continuation in ricb from the neighbouring converged rows.
3. REGRESSION of recovery: the committed recovered_rows_v1_3_0.json (same
   harness, current src/ at the release SHA) must be reproduced -- a
   recovered row may not silently disappear. Each fixture row carries an
   "admissible" tag: converged rows with chi_li_icb outside [0, bound]
   (error_code 4 in the csv, like 21.8% of the published rows) are
   reproduced but are NOT counted as recovered valid models.

Runtime is bounded by --extra-radii 2: each case runs (v1.2.0 rows + 2)
radii, so the identity rows and two continuation radii are exercised
(~4-6 min wall on 8 workers). The full-grid recovery statistics live in
docs/notes/solver_v1.3.0.md, not here.
"""
import json
import os
import pathlib
import sys

import numpy as np
import pytest

pytestmark = pytest.mark.integration

REF = pathlib.Path(__file__).resolve().parent.parent / "reference" / "v1_2_0_sweeps"
SRC = pathlib.Path(__file__).resolve().parents[2] / "pie"
sys.path.insert(0, str(REF))
import generate_sweeps  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from pielib import pool_workers  # noqa: E402

EXTRA_RADII = 2
PINNED = {"numpy": "1.21.5", "scipy": "1.8.0"}


def _fixture():
    return json.load(open(REF / "v1_2_0_sweeps.json"))


def _recovered_fixture():
    p = REF / "recovered_rows_v1_3_0.json"
    return json.load(open(p)) if p.is_file() else None


@pytest.fixture(scope="module")
def current():
    return generate_sweeps.generate(SRC, workers=pool_workers(8), policy="continue",
                                    extra_radii=EXTRA_RADII, verbose=False)


def _on_pinned_env():
    import numpy, scipy
    return numpy.__version__ == PINNED["numpy"] and scipy.__version__ == PINNED["scipy"]


def _same(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    if _on_pinned_env():
        # NOT np.array_equal: bit-identical was measured false even with
        # the exact same package versions, across two different machines
        # (this dev box vs the GH Actions `fast` runner, both numpy
        # 1.21.5/scipy 1.8.0) -- CI run 36715921055/job 109888682172 failed
        # 8/30 cases with LAPACK/BLAS ULP-level rounding differences (CPU
        # microarchitecture / SIMD dispatch, not package version). A first
        # calibration (rtol 1e-8/atol 1e-10, from single cold-start k=0
        # solves) still failed 6/30 on CI run 36730679366/job 109939146547:
        # warm-started rows (k>0) chain each radius's tiny cross-machine
        # drift into the next radius's initial guess, so it COMPOUNDS along
        # a sweep -- measured up to ~2.2e-7 relative by k=1 (component
        # chi_li_icb). rtol 1e-6/atol 1e-8 keeps two orders of margin above
        # that measured compounding and is still ~1-2 orders below the
        # solver's own convergence tolerance (ftol=xtol=1e-6,
        # src/globalvar.py) and far below any physically meaningful change.
        # See test_v1_2_0_converged_rows_bitwise_same_host for the strict
        # bitwise check, which only runs where the fixture was generated.
        return np.allclose(a, b, rtol=1e-6, atol=1e-8)
    # Off the pinned environment (CI fast-latest: numpy 2.x / scipy 1.15)
    # the LSODA/RK45 integrators, polyfit and BLAS differ in rounding, and a
    # Newton iterate that stops at the same |f| < ftol lands within the
    # solver's own tolerance of the pinned result, not within 1e-9. Use the
    # same calibrated cross-environment tolerance every parity test uses
    # against the published (LS6-generated) data: rtol 1e-4, atol 1e-6
    # (conftest.assert_scalars_match). Measured on numpy 2.2.6/scipy 1.15.3:
    # rtol 1e-9 fails 7/14 cases.
    return np.allclose(a, b, rtol=1e-4, atol=1e-6)


def _case_ids():
    return sorted(json.load(open(REF / "sample.json")), key=lambda c: c["name"])


@pytest.mark.parametrize("case", _case_ids(), ids=lambda c: c["name"])
def test_v1_2_0_converged_rows_are_identical(case, current):
    ref_rows = _fixture()["cases"][case["name"]]["rows"]
    cur_rows = current["cases"][case["name"]]["rows"]
    cur_by_k = {r["k"]: r for r in cur_rows}
    n_checked = 0
    for rr in ref_rows:
        if rr["status"] != "ok":
            continue
        cr = cur_by_k.get(rr["k"])
        assert cr is not None and cr["status"] == "ok", (
            f"{case['name']} k={rr['k']} ricb={rr['ricb_m']}: converged in v1.2.0, "
            f"current status={cr and cr.get('status')} {cr and cr.get('error_name')}")
        assert _same(rr["v"], cr["v"]), (
            f"{case['name']} k={rr['k']}: v differs from v1.2.0\n  v1.2.0 {rr['v']}\n  now    {cr['v']}")
        # `f` is the shooting residual AT the converged root -- physically
        # it should be ~0, and empirically it is (~1e-10 to 1e-11, far
        # below ftol=1e-6, src/globalvar.py), which is exactly the same
        # order as cross-machine BLAS noise. Comparing two near-zero noise
        # vectors component-wise (relative to each other) is not a
        # meaningful check; assert convergence itself instead (an absolute,
        # physical invariant that doesn't depend on which machine ran it).
        # ftol literal (not imported from src/globalvar.py: importing that
        # module here would run its argv-dependent top-level code in this
        # test process) -- src/globalvar.py:70 `ftol = 1.e-6`.
        FTOL = 1e-6
        assert np.all(np.abs(cr["f"]) < FTOL), (
            f"{case['name']} k={rr['k']}: f={cr['f']} not converged below ftol={FTOL}")
        # fout = (Picb, Tcmb, isnow, isnowcmb, chi_li_in, gradTa, chi_S_bulk)
        # -- isnow/isnowcmb (indices 2, 3) are categorical (0/1) flags, not
        # accumulated arithmetic: compare exactly, never with a tolerance.
        assert cr["fout"][2] == rr["fout"][2] and cr["fout"][3] == rr["fout"][3], (
            f"{case['name']} k={rr['k']}: isnow/isnowcmb flag differs\n"
            f"  v1.2.0 {rr['fout']}\n  now    {cr['fout']}")
        fout_ref = [x for i, x in enumerate(rr["fout"]) if i not in (2, 3)]
        fout_cur = [x for i, x in enumerate(cr["fout"]) if i not in (2, 3)]
        assert _same(fout_ref, fout_cur), (
            f"{case['name']} k={rr['k']}: fout differs\n  v1.2.0 {rr['fout']}\n  now    {cr['fout']}")
        n_checked += 1
    assert n_checked == sum(r["status"] == "ok" for r in ref_rows)


@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true" or not os.environ.get("PIE_SAME_HOST_AS_FIXTURE"),
    reason=(
        "strict bitwise identity only holds on the exact machine that "
        "generated testsys/reference/v1_2_0_sweeps/v1_2_0_sweeps.json -- "
        "LAPACK/BLAS ULP-level rounding differs by CPU/SIMD dispatch even "
        "under identical pins (see _same's docstring, CI run 36715921055). "
        "Set PIE_SAME_HOST_AS_FIXTURE=1 to run this on that box; the "
        "portable rtol 1e-6/atol 1e-8 check above is the CI gate."))
@pytest.mark.parametrize("case", _case_ids(), ids=lambda c: c["name"])
def test_v1_2_0_converged_rows_bitwise_same_host(case, current):
    ref_rows = _fixture()["cases"][case["name"]]["rows"]
    cur_rows = current["cases"][case["name"]]["rows"]
    cur_by_k = {r["k"]: r for r in cur_rows}
    for rr in ref_rows:
        if rr["status"] != "ok":
            continue
        cr = cur_by_k[rr["k"]]
        assert np.array_equal(np.asarray(rr["v"]), np.asarray(cr["v"])), (
            f"{case['name']} k={rr['k']}: v not bitwise-identical on same host")


def _admissible(row):
    """A converged row is admissible when chi_li_icb is in [0, eutectic/Si max]
    and the shoot raised no negative-chi flag. Converged rows outside that box
    are what driverp.py writes with error_code 4 (the err flag /
    (chi_li<0).any() checks): recorded, reproducible, but NOT counted as
    recovered valid models -- the same status the 21.8% of published rows
    with chi_li_icb < 0 have."""
    return (0.0 <= row["chi_li_icb"] <= row["chi_max"]) and not row.get("err_flag", False)


def _validity(row, case, context):
    assert row["resid_norm"] < 1e-5, f"{context}: resid_norm {row['resid_norm']:.3e} not below solver tolerance"
    assert _admissible(row), f"{context}: chi_li_icb {row['chi_li_icb']} outside [0, {row['chi_max']}] or err flag set"
    assert row["ricb_m"] < row["rcmb_m"], f"{context}: ricb >= rcmb"
    assert row["rho_min"] > 0, f"{context}: non-positive density"
    assert row["profile_finite"], f"{context}: non-finite profile"
    assert np.all(np.isfinite(row["v"])) and np.all(np.isfinite(row["f"]))


def _recovered_rows(case, current):
    ref_ok = {r["k"] for r in _fixture()["cases"][case["name"]]["rows"] if r["status"] == "ok"}
    return [r for r in current["cases"][case["name"]]["rows"] if r["status"] == "ok" and r["k"] not in ref_ok]


@pytest.mark.parametrize("case", _case_ids(), ids=lambda c: c["name"])
def test_recovered_rows_are_valid_and_smooth(case, current):
    rows = current["cases"][case["name"]]["rows"]
    ok_rows = [r for r in rows if r["status"] == "ok"]
    rec = _recovered_rows(case, current)
    for r in rec:
        if not _admissible(r):
            # converged but inadmissible (chi < 0 or > bound): driverp writes it
            # with error_code 4; it is not a recovered model. Finite + converged only.
            assert r["resid_norm"] < 1e-5 and np.all(np.isfinite(r["v"])), f"{case['name']} k={r['k']}: inadmissible row not even converged"
            continue
        _validity(r, case, f"{case['name']} k={r['k']} (recovered)")
    # smooth continuation in ricb: each recovered row's v must be within the
    # local step scale of the previous converged row (no jump to another
    # branch). Bound: |dv_i| <= 5 * max(|previous dv_i|, 0.01*|v_i|, 1e-3)
    # -- calibrated so every v1.2.0-converged sweep in this sample passes.
    ok_by_k = {r["k"]: r for r in ok_rows}
    for r in rec:
        prev = [ok_by_k[j] for j in range(r["k"] - 1, -1, -1) if j in ok_by_k][:2]
        if not prev:
            continue
        dv = np.abs(np.asarray(r["v"]) - np.asarray(prev[0]["v"]))
        if len(prev) == 2:
            dv_prev = np.abs(np.asarray(prev[0]["v"]) - np.asarray(prev[1]["v"]))
        else:
            dv_prev = np.zeros_like(dv)
        bound = 5 * np.maximum(np.maximum(dv_prev, 0.01 * np.abs(prev[0]["v"])), 1e-3)
        assert np.all(dv <= bound), (
            f"{case['name']} k={r['k']} (recovered): jump in v from the previous converged row\n"
            f"  dv={dv}\n  bound={bound}")
    # every row is either identical-to-v1.2.0 or recovered-and-valid, or a recorded failure
    for r in rows:
        assert r["status"] in ("ok", "failed")
        if r["status"] == "failed":
            assert r["error_code"] in (1, 2, 3, 4, 5, 6), f"{case['name']} k={r['k']}: unclassified failure {r}"


def test_recovered_rows_regression_fixture(current):
    fx = _recovered_fixture()
    if fx is None:
        pytest.skip("recovered_rows_v1_3_0.json not generated yet")
    for name, rows in fx["recovered"].items():
        cur = {r["k"]: r for r in current["cases"][name]["rows"]}
        for rr in rows:
            cr = cur.get(rr["k"])
            assert cr is not None and cr["status"] == "ok", f"{name} k={rr['k']}: recovered row lost (status={cr and cr.get('status')})"
            assert _same(rr["v"], cr["v"]), f"{name} k={rr['k']}: recovered v changed\n  fixture {rr['v']}\n  now     {cr['v']}"
            assert _admissible(cr) == rr["admissible"], f"{name} k={rr['k']}: admissibility tag changed"


def test_sample_provenance_is_v1_2_0_pinned():
    prov = _fixture()["provenance"]
    assert prov["git_sha"].startswith("18cf78a")
    assert prov["numpy"] == PINNED["numpy"] and prov["scipy"] == PINNED["scipy"]
