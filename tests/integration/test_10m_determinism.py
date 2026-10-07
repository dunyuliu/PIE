"""Integration tier: the ricb = 10 m solve is deterministic (bug B5 closed,
PATHWAY_FORWARD.md items 17/19).

Before v1.3.0, getk2 at nrs = 0 (the 10-m first radius) read the never-set
g[399] of an np.empty array through a k+nrs-1 = -1 index wrap, so the 10-m
solve depended on heap contents: the same input converged in one process
and raised "Factor is exactly singular" / NONFINITE_SHOOT in another. Seen
in tests/e2e/test_published_wide_sweep.py (1 vs 2 failures, same seed)
and once in the FAST tier on CI run 36661040573 (fast-latest, py3.12):
test_mc_wide_parity.py::test_mc_wide_case[genova_S+Si_high_cmr2_extreme]
failed with NONFINITE_SHOOT at ricb = 10 m and passed on re-run.

This test solves that exact published case, plus the fixed-seed
published_wide flake case, N times in N FRESH processes (fresh heap each
time -- an in-process loop would reuse the same allocator state and could
hide the bug) and requires every run to converge to the bit-identical v.
"""
import concurrent.futures as cf
import os

import numpy as np
import pytest

from pielib import solve_full_model

pytestmark = [pytest.mark.integration]

N_REPEAT = int(os.environ.get("PIE_10M_REPEAT", "6"))

CASES = [
    # (label, CMR2, CMC, light, chi_Si) -- both are published-converged at 10 m
    ("mc_wide genova S+Si high_cmr2_extreme (CI flake 36661040573)",
     0.3517235672309141, 0.4194174452437264, "S+Si", 0.05),
    ("published_wide margot S+Si fixed-seed flake (tests README Findings #5)",
     0.33521178639464477, 0.43971007578615007, "S+Si", 0.05),
]


def _solve(args):
    _, cmr2, cmc, light, chi = args
    try:
        return solve_full_model(cmr2, cmc, light, "Edmund", 10.0, chi_Si_icb=chi)
    except BaseException as e:  # noqa: BLE001
        return e


@pytest.mark.parametrize("case", CASES, ids=lambda c: c[0])
def test_ricb_10m_solve_is_deterministic_across_fresh_processes(case):
    # max_workers == N_REPEAT with one task each => every solve runs in its
    # own freshly forked worker, so no two repeats share allocator history.
    with cf.ProcessPoolExecutor(max_workers=N_REPEAT) as ex:
        results = list(ex.map(_solve, [case] * N_REPEAT))
    failures = [r for r in results if isinstance(r, BaseException)]
    assert not failures, (
        f"{case[0]}: {len(failures)}/{N_REPEAT} fresh-process solves at ricb=10 m failed "
        f"({failures[0]!r}) -- the nrs=0 getk2 path is not deterministic")
    v0 = np.asarray(results[0]["v"])
    for i, r in enumerate(results[1:], 1):
        assert np.array_equal(v0, np.asarray(r["v"])), (
            f"{case[0]}: repeat {i} converged to a different v\n  {v0}\n  {np.asarray(r['v'])}")
    # These are published-CONVERGED rows (v1.0.5 parity cases), not recovered
    # models: the recovered-row validity gate does not apply (the margot case
    # has chi_li_icb = -6.5e-4, one of the 21.8% of published rows with a
    # slightly negative chi, carrying error_code 4). Gate finiteness and the
    # residual only; scalar parity is gated by test_mc_wide_parity.py.
    assert np.all(np.isfinite(v0)) and results[0]["resid_norm"] < 1e-5
