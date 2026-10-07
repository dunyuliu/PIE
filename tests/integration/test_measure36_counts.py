"""Regression test for PATHWAY_FORWARD.md item 18's measure36 counts
(docs/notes/item18_quantify_2026-10-01.md), derived fresh from the raw
fixture `tests/reference/v1_2_0_sweeps/v130_measure36.json` instead of
trusting any hand-rolled table.

Context: `docs/notes/item18_quantify_2026-10-01.md` and
`docs/notes/solver_v1.3.0_measurement/measure36_results_2026-10-01.md`
both quote a set of headline counts off this JSON (37 affected-composition
cases, continue-policy Newton-solve sweeps beyond each case's published
v1.2.0 stop radius). A priya-nair audit (2026-10-02) found a real
arithmetic error in the doc's hand-rolled per-composition admissible-row
table (one case undercounted) that nothing mechanical had caught -- the
doc's numbers were typed by hand from eyeballing the JSON, not computed by
a test. This file is that missing mechanical check: it re-derives every
count below BY ITERATING THE RAW JSON AND COMPUTING, not by asserting a
copy-pasted list of numbers with no path back to the data. If a future
edit to the fixture OR to the admissibility rule silently changes any of
these counts, this test goes red.

Admissibility reuses `conftest.py::is_admissible` verbatim (its own
docstring: "chi_li_icb in [0, eutectic at P_icb] (S, S+Si) or [0, liquidus
Si max] (Si) and no negative-chi err flag") -- this file does not
reimplement that formula, to avoid drifting from the one definition the
rest of the suite uses.

"Beyond published stop" radii: each case's `rows` list has up to 40
entries indexed 0..39 by `ricb_m` grid step (`k`); `case["published_rows"]`
is how many of those were already part of the published v1.2.0 sweep for
that composition. Rows with `k >= published_rows` are the ones v1.2.0
never reached -- summing `len(rows) - published_rows` over all 37 cases
gives the 892 total.

"Failure-mode split" among the 39 admissible rows buckets each admissible
row by its CASE's published failure-mode tag (`crash_stderr` / `detJ0` /
`newton_maxit`, the string embedded in `case["published_class"]`, e.g.
"genova/S+Si_0.05/crash_stderr/10m") -- this describes how the published
v1.2.0 run for that composition died, not the admissible row's own status
(which is always "ok" by construction of `is_admissible`).
"""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from pielib import is_admissible

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "reference" / "v1_2_0_sweeps" / "v130_measure36.json"
)

EXPECTED_TOTAL_CASES = 37
EXPECTED_BEYOND_STOP_RADII = 892
EXPECTED_CONVERGED = 218
EXPECTED_ADMISSIBLE = 39
EXPECTED_CASES_WITH_ADMISSIBLE = 16
EXPECTED_PER_COMPOSITION = {
    ("margot", "S", None): 1,
    ("margot", "S+Si", 0.05): 17,
    ("margot", "S+Si", 0.10): 5,
    ("genova", "S", None): 4,
    ("genova", "Si", None): 3,
    ("genova", "S+Si", 0.05): 5,
    ("genova", "S+Si", 0.10): 4,
    # margot/Si is present in the 37-case fixture but contributes zero
    # admissible rows; included explicitly so the breakdown below is
    # exhaustive over every composition in the data, not just the
    # nonzero ones the doc's hand-rolled table happened to list.
    ("margot", "Si", None): 0,
}
EXPECTED_FAILURE_MODE_SPLIT = {
    "newton_maxit": 29,
    "crash_stderr": 9,
    "detJ0": 1,
}


def _load_cases():
    with open(FIXTURE) as f:
        data = json.load(f)
    return data["cases"]


def _composition_key(meta):
    chi_si = meta.get("chi_Si_icb")
    light = meta["light"]
    # chi_Si_icb is 0.0 for single-light-element cases (S, Si); only S+Si
    # cases carry a meaningful 0.05/0.10 split.
    return (meta["moi"], light, chi_si if light == "S+Si" else None)


def _row_is_admissible(row, meta):
    """Adapt one raw sweep row + its case metadata into the shape
    conftest.is_admissible expects, without touching its formula."""
    if row.get("status") != "ok" or "chi_li_icb" not in row:
        return False
    result = {
        "scalars": {
            "chi_li_icb": row["chi_li_icb"],
            "chi_li_eut_icb": row.get("chi_max"),
        },
        "max_Si": row.get("chi_max"),
        "light_element": meta["light"],
        "err_flag": row.get("err_flag", False),
    }
    return is_admissible(result)


def _published_failure_mode(meta):
    pc = meta["published_class"]
    tags = [t for t in ("crash_stderr", "detJ0", "newton_maxit") if t in pc]
    assert len(tags) == 1, (
        f"published_class {pc!r} must tag exactly one of "
        f"crash_stderr/detJ0/newton_maxit, found {tags}"
    )
    return tags[0]


def test_measure36_counts_match_audited_totals():
    cases = _load_cases()
    assert len(cases) == EXPECTED_TOTAL_CASES, (
        f"expected {EXPECTED_TOTAL_CASES} cases in {FIXTURE}, found {len(cases)} "
        "-- the case list itself changed, re-derive the audited counts before "
        "updating this test's expectations"
    )

    total_beyond_stop = 0
    total_converged = 0
    total_admissible = 0
    cases_with_admissible = 0
    per_composition = {}
    failure_mode_split = {"newton_maxit": 0, "crash_stderr": 0, "detJ0": 0}

    for case in cases.values():
        meta = case["case"]
        rows = case["rows"]
        published_rows = meta["published_rows"]
        beyond_stop_rows = [r for r in rows if r["k"] >= published_rows]
        total_beyond_stop += len(beyond_stop_rows)

        case_admissible_count = 0
        for row in beyond_stop_rows:
            if row.get("status") == "ok":
                total_converged += 1
            if _row_is_admissible(row, meta):
                total_admissible += 1
                case_admissible_count += 1
                failure_mode_split[_published_failure_mode(meta)] += 1

        if case_admissible_count >= 1:
            cases_with_admissible += 1

        key = _composition_key(meta)
        per_composition[key] = per_composition.get(key, 0) + case_admissible_count

    assert total_beyond_stop == EXPECTED_BEYOND_STOP_RADII, (
        f"sum(len(rows) - published_rows) over all cases = {total_beyond_stop}, "
        f"expected {EXPECTED_BEYOND_STOP_RADII}"
    )
    assert total_converged == EXPECTED_CONVERGED, (
        f"converged (status == 'ok') among beyond-stop radii = {total_converged}, "
        f"expected {EXPECTED_CONVERGED}"
    )
    assert total_admissible == EXPECTED_ADMISSIBLE, (
        f"admissible (is_admissible) among beyond-stop radii = {total_admissible}, "
        f"expected {EXPECTED_ADMISSIBLE}"
    )
    assert cases_with_admissible == EXPECTED_CASES_WITH_ADMISSIBLE, (
        f"cases with >=1 admissible beyond-stop row = {cases_with_admissible}, "
        f"expected {EXPECTED_CASES_WITH_ADMISSIBLE}"
    )
    assert per_composition == EXPECTED_PER_COMPOSITION, (
        f"per-composition admissible-row breakdown = {per_composition}, "
        f"expected {EXPECTED_PER_COMPOSITION} (this is the exact table a "
        "2026-10-02 audit found one case undercounted in by hand)"
    )
    assert sum(per_composition.values()) == EXPECTED_ADMISSIBLE
    assert failure_mode_split == EXPECTED_FAILURE_MODE_SPLIT, (
        f"failure-mode split among admissible rows = {failure_mode_split}, "
        f"expected {EXPECTED_FAILURE_MODE_SPLIT}"
    )
    assert sum(failure_mode_split.values()) == EXPECTED_ADMISSIBLE
