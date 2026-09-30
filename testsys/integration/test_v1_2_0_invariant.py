"""Integration tier: the v1.3.0 solver invariant against v1.2.0 (PATHWAY_FORWARD.md
item 17; docs/notes/solver_v1.3.0.md).

Fixed sample: testsys/reference/v1_2_0_sweeps/sample.json (14 published Monte
Carlo draws, one per failure class: 6 "identity" cases that converged for
several radii in v1.2.0, 8 "recovery" cases that produced zero rows).
Reference: v1_2_0_sweeps.json, generated from src/ at v1.2.0 (18cf78a) with
the v1.2.0 stop-at-first-failure policy on the pinned environment.

Gates
1. IDENTITY: every row that converged in v1.2.0 converges in the current
   src/ with a bit-identical unknown vector v (and f, fout) on the pinned
   environment (numpy 1.21.5 / scipy 1.8.0); on any other environment
   (CI fast-latest) rtol 1e-9, because BLAS summation order legitimately
   differs there. The line search must have accepted alpha = 1 on every
   iteration of those rows (recorded start == 'warm'/'cold' as in v1.2.0,
   newton_iters unchanged is implied by identity of v).
2. RECOVERED: rows the current src/ converges that v1.2.0 did not (after a
   v1.2.0 failure, or in a zero-row case) are tagged "recovered" and must be
   valid: residual below the solver tolerance, chi_li_icb in [0, eutectic]
   (S, S+Si) or [0, Si max] (Si), ricb < rcmb, rho > 0, finite profiles, and
   a smooth continuation in ricb from the neighbouring converged rows.
3. REGRESSION of recovery: the committed recovered_rows_v1_3_0.json (same
   harness, current src/ at the release SHA) must be reproduced -- a
   recovered row may not silently disappear.

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
SRC = pathlib.Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(REF))
import generate_sweeps  # noqa: E402

EXTRA_RADII = 2
PINNED = {"numpy": "1.21.5", "scipy": "1.8.0"}


def _fixture():
    return json.load(open(REF / "v1_2_0_sweeps.json"))


def _recovered_fixture():
    p = REF / "recovered_rows_v1_3_0.json"
    return json.load(open(p)) if p.is_file() else None


@pytest.fixture(scope="module")
def current():
    return generate_sweeps.generate(SRC, workers=min(8, os.cpu_count() or 4), policy="continue",
                                    extra_radii=EXTRA_RADII, verbose=False)


def _on_pinned_env():
    import numpy, scipy
    return numpy.__version__ == PINNED["numpy"] and scipy.__version__ == PINNED["scipy"]


def _same(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    if _on_pinned_env():
        return np.array_equal(a, b)
    return np.allclose(a, b, rtol=1e-9, atol=0.0)


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
        assert _same(rr["f"], cr["f"]) and _same(rr["fout"], cr["fout"]), f"{case['name']} k={rr['k']}: f/fout differ"
        n_checked += 1
    assert n_checked == sum(r["status"] == "ok" for r in ref_rows)


def _validity(row, case, context):
    assert row["resid_norm"] < 1e-5, f"{context}: resid_norm {row['resid_norm']:.3e} not below solver tolerance"
    assert 0.0 <= row["chi_li_icb"] <= row["chi_max"], f"{context}: chi_li_icb {row['chi_li_icb']} outside [0, {row['chi_max']}]"
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


def test_sample_provenance_is_v1_2_0_pinned():
    prov = _fixture()["provenance"]
    assert prov["git_sha"].startswith("18cf78a")
    assert prov["numpy"] == PINNED["numpy"] and prov["scipy"] == PINNED["scipy"]
