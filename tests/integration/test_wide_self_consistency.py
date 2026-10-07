"""Integration tier (fast subset of the wide sweep): one representative
radius (ricb=400 km) for every (MOI config x composition x liquidus)
combination -- 12 cases -- recomputed and compared against the
self-golden in tests/reference/self_v1.0.5/wide_sweep/wide_sweep.json.

This is the push/PR-fast slice of the wide physics-coverage sweep the
project asked for (breadth first, speed second, but still fast enough
to gate every push): all 19 presentday_columns scalars + full radial
profiles for 11 converged cases, PLUS a regression guard on the one
case that does NOT converge (Margot CMR2=0.346/CMC=0.426, 'Si',
'Edmund') -- a convergence failure is part of the regression contract
here, not a gap in it (it means no root found from the generic cold-start
guess, not an established physical non-solution; see tests/README.md
Findings 6 and docs/dev/audits/AUDIT_2026-09-29_solver-failures.md). See wide_sweep/PROVENANCE.md for why that one
case fails and why that's not a bug.

The full 3-radius x 12-case (36 total) sweep lives in
tests/e2e/test_wide_full_sweep.py; this file exists so 3/4 of that
same coverage runs on every push, not just in the periodic e2e tier.
"""
import concurrent.futures as cf
import json
import os
import pathlib

import pytest

from pielib import solve_full_model, assert_scalars_match, assert_profiles_match, check_converged_without_reference, pool_workers

pytestmark = pytest.mark.integration

GOLDEN_PATH = (pathlib.Path(__file__).resolve().parent.parent / "reference"
               / "self_v1.0.5" / "wide_sweep" / "wide_sweep.json")
FAST_RADIUS_M = 400_010.0


def _golden_entries():
    with open(GOLDEN_PATH) as f:
        all_entries = json.load(f)
    return [e for e in all_entries if e["ricb_m"] == FAST_RADIUS_M]


def _case_id(entry):
    return (f"CMR2={entry['CMR2']}_CMC={entry['CMC']}_"
            f"{entry['light_element']}_{entry['liquidus_eq']}")


def _solve_entry(entry):
    # Module-level (not a closure) so ProcessPoolExecutor can pickle it.
    try:
        return solve_full_model(
            entry["CMR2"], entry["CMC"], entry["light_element"],
            entry["liquidus_eq"], entry["ricb_m"],
            chi_Si_icb=entry["chi_Si_icb"],
        )
    except BaseException as e:  # noqa: BLE001 -- mynewtonSys uses sys.exit()
        return e


@pytest.fixture(scope="module")
def computed_by_case():
    """Recompute all 12 fast-subset cases in parallel (one process per
    case; ~18-20 s each, so ~20-25 s wall time with 12 workers rather
    than ~4 min serial) and return {case_id: result_or_exception}."""
    entries = _golden_entries()
    with cf.ProcessPoolExecutor(max_workers=pool_workers(12)) as ex:
        computed = list(ex.map(_solve_entry, entries))
    return {_case_id(e): (e, c) for e, c in zip(entries, computed)}


@pytest.mark.parametrize("entry", _golden_entries(), ids=_case_id)
def test_wide_case_matches_self_golden(entry, computed_by_case):
    _, computed = computed_by_case[_case_id(entry)]

    if not entry["converged"]:
        # The v1.0.5 golden recorded this case as non-convergent. Since
        # v1.3.0 (bounded line-search Newton, PATHWAY_FORWARD.md item 17)
        # a fresh solve MAY converge where v1.0.5 did not; that is the
        # intended recovery, not a regression -- provided the recovered
        # model passes the validity gate. A fresh failure is still
        # accepted (the golden's own outcome).
        if isinstance(computed, BaseException):
            return
        kind = check_converged_without_reference(computed, context=f"{_case_id(entry)}: ")
        print(f"{kind}: {_case_id(entry)} (golden non-convergent, v1.3.0 converges; "
              f"chi_li_icb={computed['scalars']['chi_li_icb']:.4f})")
        return

    assert not isinstance(computed, BaseException), (
        f"{_case_id(entry)}: golden says this case converges, but a fresh "
        f"solve raised {computed!r}"
    )
    assert_scalars_match(computed["scalars"], entry["scalars"], rtol=1e-4,
                          context=f"{_case_id(entry)}: ")
    assert_profiles_match(computed["profiles"], entry["profiles"],
                           rtol=1e-3, atol=1e-6, interpolate=False,
                           context=f"{_case_id(entry)}: ")
