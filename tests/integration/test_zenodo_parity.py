"""Parity tier (integration subtest): current src/ vs published-paper
output for the SAME code.

Oracle: Dunnigan et al. (2026), JGR Planets, doi:10.1029/2025JE009368,
whose Zenodo code record (10.5281/zenodo.16929504) is byte-identical to
this repo's src/ (verified: `diff -rq` finds only src/VERSION differed; removed in v1.1.0 --
see tests/reference/zenodo_v1.0.5/PROVENANCE.md). Because the code is
identical, this is a REGRESSION ANCHOR (proves reproducibility across
machine/library-version, catches a real behavioural divergence), not an
independent correctness oracle (a bug present when the paper was run
would reproduce here too) -- see PROVENANCE.md/README.md for that
distinction.

This is the ONE tier that guards against cross-environment drift
(different scipy/BLAS/numpy than whatever produced the published
files), so profile-array comparison here uses `interpolate=True`
(resample the reference onto the computed run's own radius grid) even
though, empirically, both sides currently land on the same 71-point
grid for these cases.

Gates ALL 19 `presentday_columns` scalars (previously moi/cmc/
chi_li_eut_icb/chi_li_eut_cmb were skipped here -- moi and cmc are the
model's OWN FIT TARGETS, the last things that should go unguarded) and
the full h5 radial profiles (r, rho, P, T, Tad, chi_li -- not just the
scalar 'misc' summary), per tests/conftest.py's shared
solve_full_model/assert_scalars_match/assert_profiles_match.

Tolerance: rtol=1e-4 (scalars) / rtol=1e-3,atol=1e-6 (profiles).
Measured deviation between a fresh solve and the published value
(chi_li_icb, core_mass, moi, cmc) is ~1e-7..1e-9 relative -- i.e. at or
below the Newton solver's own xtol=ftol=1e-6 (globalvar.py), not a
platform artifact. These bounds are one to two orders of magnitude
above that measured worst case.
"""
import pathlib

import pandas as pd
import pytest

from pielib import solve_full_model, assert_scalars_match, assert_profiles_match

pytestmark = [pytest.mark.integration, pytest.mark.parity]

REF_ROOT = pathlib.Path(__file__).resolve().parent.parent / "reference" / "zenodo_v1.0.5"


def _reference_from_h5(h5_path):
    scalars_df = pd.read_hdf(h5_path, key="misc")
    scalars = {k: float(scalars_df[k].iloc[0]) for k in scalars_df.columns}
    profiles = {k: pd.read_hdf(h5_path, key=k).to_numpy()
                for k in ("r", "rho", "P", "T", "Tad", "g", "chi_li")}
    return scalars, profiles


@pytest.mark.parametrize("case,h5_name,CMR2,CMC,chi_si,ricb_m", [
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "DataSi%wt0.01_R0500.0.h5",
     0.346, 0.426, 0.01, 500_010.0),
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "DataSi%wt0.06_R0550.0.h5",
     0.346, 0.426, 0.06, 550_010.0),
    ("CMR2_0.333_CMC_0.443_S+Si_Edmund", "DataSi%wt0.01_R0500.0.h5",
     0.333, 0.443, 0.01, 500_010.0),
])
def test_matches_published_s_plus_si_case(case, h5_name, CMR2, CMC, chi_si, ricb_m):
    h5_path = REF_ROOT / case / h5_name
    reference_scalars, reference_profiles = _reference_from_h5(h5_path)

    computed = solve_full_model(CMR2, CMC, "S+Si", "Edmund", ricb_m, chi_Si_icb=chi_si)

    # check_error_code=False: reference_scalars comes from the published
    # Zenodo h5 (predates PATHWAY_FORWARD.md item 16's error-code table)
    # -- see test_mc_wide_parity.py's identical carve-out for the reason.
    assert_scalars_match(computed["scalars"], reference_scalars, rtol=1e-4,
                          context=f"{case}/{h5_name}: ", check_error_code=False)
    assert_profiles_match(computed["profiles"], reference_profiles,
                           rtol=1e-3, atol=1e-6, interpolate=True,
                           context=f"{case}/{h5_name}: ")
