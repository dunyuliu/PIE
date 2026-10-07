"""PATHWAY_FORWARD.md item 23(b): the Steinbruegge-liquidus x S+Si cell
had only a self-golden test (`tests/integration/test_wide_self_consistency.py`,
same-code comparison against a committed JSON this repo itself
generated) -- no comparison against anything this repo did not produce.

What this file is, stated per PROJECT_RULES.md rule 5 (name the
comparison class explicitly): an INTERNAL-IDENTITY (same-code,
regression-class, NOT independent) check -- `chi_Si_icb=0` is an exact,
always-available degenerate-limit identity of the S+Si model itself
(same argument as `test_truth_anchor_s_si_limits.py`'s Edmund-liquidus
version of this test), so S+Si(chi_Si_icb=0, Steinbruegge) must be
bit-for-bit the S-only(Steinbruegge) branch. This identity is NOT an
independent anchor for genuine (non-zero-Si) S+Si -- but it INHERITS
the existing independent Fe-S Steinbruegge anchor transitively, at the
Si=0 slice only: `test_steinbruegge_anchor.py::test_fe_s_matches_
steinbruegge_2020` already proves S-only(Steinbruegge) agrees with the
INDEPENDENT vendored Steinbruegge et al. (2020) code to <1e-7 relative.
Chaining `S+Si(Si=0) == S-only` (this file) with `S-only == vendored
Steinbruegge code` (test_steinbruegge_anchor.py) gives: the S+Si branch
with Steinbruegge liquidus is independently verified ONLY at its Si=0
edge -- genuinely non-zero Si with Steinbruegge liquidus has NO better
anchor available. Per `docs/dev/notes/steinbruegge_anchor_2026-09-30.md`'s
own "Cannot anchor" list: the vendored Steinbruegge et al. (2020) code
has no S+Si (3-component) support at all -- it is Fe-S/Fe-Si only (see
that note's "Physics diff" item 2) -- so a direct independent anchor
for non-zero-Si S+Si-with-Steinbruegge-liquidus is NOT achievable with
any data available to this repo. State this explicitly; do not
manufacture a false independent check in its place.
"""
import pytest

pytestmark = pytest.mark.integration

from pielib import solve_full_model

# Same (CMR2, CMC) as test_steinbruegge_anchor.py's independently-anchored
# Fe-S Steinbruegge case, so the Si=0 slice checked here inherits that
# anchor directly (not a different, unrelated composition).
CMR2 = 0.333
CMC = 0.148 / 0.333
RICB_M = 500_000.0

# Same COMMON_FIELDS set as test_truth_anchor_s_si_limits.py's Edmund
# version (chi_S_bulk excluded: S-only has no such diagnostic).
COMMON_FIELDS = [
    "rhom", "mass", "moi", "cmc", "Picb", "Tcmb", "isnow", "isnowcmb",
    "chi_li_in", "Pcmb", "chi_li_eut_icb", "chi_li_eut_cmb", "rcmb",
    "core_mass", "chi_li_icb",
]


def test_s_plus_si_steinbruegge_with_zero_si_reduces_to_s_only():
    """Internal identity (regression class, see module docstring): the
    S+Si code path with the Steinbruegge liquidus, given literally zero
    Si, must degenerate to the S-only Steinbruegge code path -- both
    solve the identical Newton system once Si contributes zero
    mass/volume. rtol=1e-6, the same margin test_truth_anchor_s_si_
    limits.py's Edmund-liquidus analogue uses and justifies (measured
    <1e-9 relative there for the same identity, different liquidus
    branch only)."""
    s_only = solve_full_model(CMR2, CMC, "S", "Steinbruegge", RICB_M)
    s_plus_si_zero = solve_full_model(CMR2, CMC, "S+Si", "Steinbruegge",
                                       RICB_M, chi_Si_icb=0.0)

    for field in COMMON_FIELDS:
        a, b = s_only["scalars"][field], s_plus_si_zero["scalars"][field]
        diff = abs(b - a)
        bound = 1e-6 * max(abs(a), 1e-12)
        assert not (diff > bound), (
            f"S-only(Steinbruegge) vs S+Si(Steinbruegge, chi_Si_icb=0), "
            f"field '{field}': S-only={a!r} S+Si={b!r} diff={diff!r} "
            f"exceeds rtol=1e-6 -- these two code paths should be "
            f"mathematically identical at chi_Si_icb=0"
        )
