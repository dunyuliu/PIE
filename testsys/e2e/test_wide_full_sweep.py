"""E2E tier: the FULL wide sweep -- 2 MOI configs x 6 compositions x 3
inner-core radii (36 cases; see
testsys/reference/self_v1.0.5/wide_sweep/PROVENANCE.md) -- recomputed
and compared against the self-golden.

testsys/integration/test_wide_self_consistency.py already runs 12 of
these 36 (one radius per composition/MOI) on every push/PR; this file
is the other 2/3 (the other two radii per case), run only in the
periodic/CI-matrix e2e tier. Parallelized the same way (one process per
case) -- measured ~55 s wall time for all 36 on this 64-core box (vs
~4.4 min for the ORIGINAL single-composition full-CLI-subprocess e2e
test in test_full_composition_sweep.py, which this does not replace --
see that file and testsys/README.md for why one true
CLI/file-I/O-subprocess smoke test is still kept alongside this faster,
wider, direct-solve sweep).

CI shards this by composition (see .github/workflows/test.yml's e2e
matrix): each shard is one `light_element` x `liquidus_eq` pair (2 MOI x
3 radii = 6 cases/shard, ~20 s/shard wall time parallelized).
"""
import concurrent.futures as cf
import json
import os
import pathlib

import pytest

from conftest import solve_full_model, assert_scalars_match, assert_profiles_match

pytestmark = pytest.mark.e2e

GOLDEN_PATH = (pathlib.Path(__file__).resolve().parent.parent / "reference"
               / "self_v1.0.5" / "wide_sweep" / "wide_sweep.json")

# CI matrix shards by composition; PIE_E2E_SHARD=light_element,liquidus_eq
# restricts this run to one shard. Unset (local/default) runs all 36.
_SHARD = os.environ.get("PIE_E2E_SHARD")


def _golden_entries():
    with open(GOLDEN_PATH) as f:
        entries = json.load(f)
    if _SHARD:
        light, liq = _SHARD.split(",")
        entries = [e for e in entries
                   if e["light_element"] == light and e["liquidus_eq"] == liq]
    return entries


def _case_id(entry):
    return (f"CMR2={entry['CMR2']}_CMC={entry['CMC']}_"
            f"{entry['light_element']}_{entry['liquidus_eq']}_"
            f"ricb={entry['ricb_m']:.0f}")


def _solve_entry(entry):
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
    entries = _golden_entries()
    with cf.ProcessPoolExecutor(max_workers=min(36, os.cpu_count() or 4)) as ex:
        computed = list(ex.map(_solve_entry, entries))
    return {_case_id(e): (e, c) for e, c in zip(entries, computed)}


@pytest.mark.parametrize("entry", _golden_entries(), ids=_case_id)
def test_wide_case_matches_self_golden(entry, computed_by_case):
    _, computed = computed_by_case[_case_id(entry)]

    if not entry["converged"]:
        assert isinstance(computed, BaseException), (
            f"{_case_id(entry)}: golden says non-convergent, fresh solve "
            f"succeeded -- regenerate the golden deliberately if intended."
        )
        return

    assert not isinstance(computed, BaseException), (
        f"{_case_id(entry)}: golden says convergent, fresh solve raised {computed!r}"
    )
    assert_scalars_match(computed["scalars"], entry["scalars"], rtol=1e-4,
                          context=f"{_case_id(entry)}: ")
    assert_profiles_match(computed["profiles"], entry["profiles"],
                           rtol=1e-3, atol=1e-6, interpolate=False,
                           context=f"{_case_id(entry)}: ")
