"""Regression test for PATHWAY_FORWARD.md item 23(a): `testsys/conftest.py`'s
`solve_full_model` used to hard-code `"error_code": 0.0` in the scalars
dict it returns, regardless of what the solve itself actually did -- a
tautology that could never fire a non-zero `error_code` regression,
however badly `src/driverp.py`'s own error-code classification (item 16's
`ErrorCode` table) broke. Fixed in this same change: `solve_full_model`
now derives `error_code` from the solve's OWN returned status (the `err`
flag `shoot_mercmodel` returns, the solved `rcmb` vs the requested ricb,
and the sign of the converged `chi_li` profile), in the exact order
`src/driverp.py`'s own per-radius sweep applies them (see that file,
and `solve_full_model`'s new comment in `testsys/conftest.py`).

This file proves the fixture CAN now fail: `MARGOT_S_10M_CASE` below is a
real, deterministic single-radius solve (CMR2/CMC drawn from
`docs/notes/solver_v1.3.0_measurement/cases36.json`'s
`margot_S_000_crash_stderr_10m` case) that CONVERGES (the Newton solve
finds a root) but at a physically inadmissible root: `chi_li_icb`
(sulfur wt fraction at the inner-core boundary) comes out negative,
~-0.036 -- exactly the class `src/driverp.py` tags
`ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX` (4), 21.8% of the published
converged rows per `testsys/conftest.py::is_admissible`'s own docstring.
Measured directly on this box, 2026-10-01 (deterministic, no RNG, no
sweep/warm-start history -- a single cold-start solve at ricb=10 m):
chi_li_icb=-0.0360, err_flag=True, derived error_code=4.0. Under the OLD
(hard-coded) fixture this case silently read error_code=0.0 -- a false
"converged, admissible" signal for a solve that is neither.
"""
import pytest

pytestmark = pytest.mark.integration

from pielib import solve_full_model

# docs/notes/solver_v1.3.0_measurement/cases36.json:
# "margot_S_000_crash_stderr_10m" (role: measure, published_class
# margot/S_0.00/crash_stderr/10m -- a composition published with ZERO
# converged rows that v1.3.0's line-search Newton recovers at ricb=10 m,
# but into an inadmissible root; see this file's module docstring).
MARGOT_S_10M_CASE = dict(
    CMR2=0.3135814520279367, CMC=0.4700405558006939,
    light_element="S", liquidus_eq="Edmund", ricb_m=10.0,
)

# A known-good, fully admissible case (Margot CMR2/CMC fit, mid-radius --
# same case family testsys/integration/test_truth_anchor_margot_fit.py
# anchors) -- proves the fixture does NOT now ALWAYS return non-zero,
# only when the solve itself is actually inadmissible.
MARGOT_S_ADMISSIBLE_CASE = dict(
    CMR2=0.346, CMC=0.424,
    light_element="S", liquidus_eq="Edmund", ricb_m=500_010.0,
)


def test_inadmissible_converged_solve_gets_nonzero_error_code():
    """The known-inadmissible case above must produce error_code == 4
    (CHI_OUTSIDE_ADMISSIBLE_BOX) THROUGH solve_full_model's own scalars
    dict -- not asserted by re-deriving it from err_flag/chi_li_icb
    independently, which would just be re-checking the test's own setup,
    not the fixture path PATHWAY_FORWARD.md item 23(a) names."""
    result = solve_full_model(**MARGOT_S_10M_CASE)
    assert result["err_flag"] is True, (
        "fixture setup assumption broken: this case no longer converges "
        "to an inadmissible (negative chi_li_icb) root -- re-probe "
        "docs/notes/solver_v1.3.0_measurement/cases36.json for a fresh "
        "known-inadmissible case before trusting this test again"
    )
    assert result["scalars"]["chi_li_icb"] < 0.0, (
        f"fixture setup assumption broken: chi_li_icb="
        f"{result['scalars']['chi_li_icb']!r} is no longer negative"
    )
    error_code = result["scalars"]["error_code"]
    assert error_code != 0.0, (
        "solve_full_model's scalars['error_code'] is 0.0 for a solve "
        "that converged to chi_li_icb < 0 (err_flag=True) -- this is "
        "exactly the hard-coded-0.0 tautology PATHWAY_FORWARD.md item "
        "23(a) requires fixed: a real non-zero error_code regression "
        "could never be caught through this field"
    )
    assert error_code == 4.0, (
        f"expected ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX (4), got "
        f"{error_code!r} -- src/driverp.py's own classification for "
        f"err_flag=True with no RICB_GE_RCMB override"
    )


def test_admissible_converged_solve_still_gets_zero_error_code():
    """Negative control: a genuinely admissible, physically valid
    converged solve must still read error_code == 0 -- the fix must not
    have turned the field into "always non-zero" or otherwise broken
    the common (admissible) case every other integration/e2e test's
    parity comparisons depend on."""
    result = solve_full_model(**MARGOT_S_ADMISSIBLE_CASE)
    assert result["err_flag"] is False, "case assumption broken: no longer admissible"
    assert result["scalars"]["chi_li_icb"] >= 0.0
    assert result["scalars"]["error_code"] == 0.0, (
        f"expected ErrorCode.CONVERGED (0) for an admissible solve, got "
        f"{result['scalars']['error_code']!r}"
    )
