"""Truth anchor (PROJECT_RULES.md rule 5): S+Si is a mathematical
generalisation of the single-light-element (S-only / Si-only) models,
so its degenerate limits are an INTERNAL CONSISTENCY identity of the
model itself, independent of any external published number or prior
code version -- exactly the class `PATHWAY_FORWARD.md` item 3 and
`CLAUDE.md`'s "Known correctness caveats" both name as the one
correctness check available for S+Si (which otherwise has only a
same-code regression anchor, the Zenodo/Dunnigan dataset -- see
`testsys/integration/test_zenodo_parity.py`).

`chi_Si_icb` (Si wt fraction at the ICB) is S+Si's one FREE input; the
complementary S abundance (`chi_S_bulk`, a fit OUTPUT, not an input --
see `src/driverp.py` line ~97) is determined by the same (CMR2, CMC)
mass-balance constraint that drives the single-element models. So:

- `chi_Si_icb=0` is an EXACT, always-available input-level identity:
  the S+Si branch with zero Si should be bit-for-bit the S-only branch.
- The complementary `chi_S_bulk -> 0` limit has NO free input that
  forces it exactly (chi_S_bulk is a derived diagnostic); see the
  xfail below for what was actually tried.
"""
import pytest

pytestmark = pytest.mark.integration

from pielib import solve_full_model

CMR2, CMC, RICB_M = 0.346, 0.424, 500_010.0

# Every field solve_full_model computes that is comparable between S-only
# and S+Si(chi_Si_icb=0) -- chi_S_bulk is S+Si-only (S-only has no such
# diagnostic) so it is excluded, not silently skipped-and-ignored.
COMMON_FIELDS = [
    "rhom", "mass", "moi", "cmc", "Picb", "Tcmb", "isnow", "isnowcmb",
    "chi_li_in", "Pcmb", "chi_li_eut_icb", "chi_li_eut_cmb", "rcmb",
    "core_mass", "chi_li_icb",
]


def test_s_plus_si_with_zero_si_reduces_to_s_only():
    """chi_Si_icb=0 -- a truth check on the MODEL, not a fit: does the
    S+Si code path, given literally zero Si, actually degenerate to the
    S-only code path? Measured on this box: every COMMON_FIELDS value
    matches to <1e-9 relative (effectively exact -- both branches solve
    the identical Newton system once Si contributes zero mass/volume),
    so rtol=1e-6 here is a >=1000x margin over the measured worst case,
    not an assumed number."""
    s_only = solve_full_model(CMR2, CMC, "S", "Edmund", RICB_M)
    s_plus_si_zero = solve_full_model(CMR2, CMC, "S+Si", "Edmund", RICB_M, chi_Si_icb=0.0)

    for field in COMMON_FIELDS:
        a, b = s_only["scalars"][field], s_plus_si_zero["scalars"][field]
        diff = abs(b - a)
        bound = 1e-6 * max(abs(a), 1e-12)
        assert not (diff > bound), (
            f"S-only vs S+Si(chi_Si_icb=0), field '{field}': S-only={a!r} "
            f"S+Si={b!r} diff={diff!r} exceeds rtol=1e-6 -- these two "
            f"code paths should be mathematically identical at chi_Si_icb=0"
        )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "S_wt%->0 == Si-only has NO clean witness with the current solver: "
        "chi_S_bulk is a DERIVED output (not a free input), and at every "
        "(CMR2, CMC, ricb) combination probed on 2026-09-29 -- margot "
        "(0.346, 0.424) and genova (0.333, 0.148/0.333) presets, ricb in "
        "{10, 50010, 500010, 600010} m -- chi_Si_icb sweeps from 0 either "
        "(a) never bring chi_S_bulk to ~0 before the Newton solve fails "
        "with 'Factor is exactly singular' (chi_Si_icb>=0.08-0.10, "
        "depending on composition/radius), or (b) drive chi_S_bulk NEGATIVE "
        "(an unphysical bulk light-element fraction) before that failure "
        "point -- e.g. genova/50010m: chi_S_bulk=+0.0050 at "
        "chi_Si_icb=0.02, -0.0034 at chi_Si_icb=0.04, -0.011 at "
        "chi_Si_icb=0.06, singular at chi_Si_icb=0.08. There is no "
        "chi_Si_icb in this probed range where chi_S_bulk is both "
        "small AND physical, so 'Si-only reduces the S+Si model at "
        "chi_S_bulk->0' cannot be verified without either accepting an "
        "unphysical negative match or the solver singularity being fixed "
        "first (PATHWAY_FORWARD.md item 17, bounded-backtracking Newton). "
        "Not fabricated: this reason documents what was actually run, not "
        "an assumed cause -- fix scope is item 17, not this test file."
    ),
)
def test_s_plus_si_with_zero_s_reduces_to_si_only():
    CMR2_g, CMC_g = 0.333, 0.148 / 0.333
    ricb = 50_010.0
    si_only = solve_full_model(CMR2_g, CMC_g, "Si", "Edmund", ricb)
    # No chi_Si_icb value was found (see xfail reason) where chi_S_bulk is
    # both non-negative and small -- probing further chi_Si_icb values here
    # would just be re-deriving the xfail reason at runtime; the reason
    # string above already records exactly what was tried.
    s_plus_si = solve_full_model(CMR2_g, CMC_g, "S+Si", "Edmund", ricb, chi_Si_icb=0.03)
    assert s_plus_si["scalars"]["chi_S_bulk"] == pytest.approx(0.0, abs=1e-4)
    assert s_plus_si["scalars"]["chi_li_icb"] == pytest.approx(
        si_only["scalars"]["chi_li_icb"], rel=1e-6)
