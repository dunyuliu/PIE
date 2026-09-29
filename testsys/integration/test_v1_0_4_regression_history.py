"""Secondary regression-history check: current HEAD vs a stored v1.0.4
(2023-01-27) run, same (CMR2, CMC, light_element, liquidus_eq) as this
repo's own e2e self-golden. See testsys/reference/v1.0.4_20230127/
PROVENANCE.md for the full delta table and attribution.

Not a hard equality gate on every field -- 2 of 19 columns are KNOWN to
have changed intentionally (core_mass's volume prefactor; isnow's
classification logic) and are checked against their KNOWN, documented
delta instead of gated to zero. Every other (untouched) field IS gated
to equality (rtol=1e-6): if one of those starts drifting, that is a
real, unattributed divergence this test is designed to catch.

No solve here (both files are pre-computed CSVs), so this runs in
milliseconds despite comparing 17 full model rows.
"""
import csv
import math
import pathlib

import pytest

pytestmark = pytest.mark.integration

REF_ROOT = pathlib.Path(__file__).resolve().parent.parent / "reference"
V104_CSV = (REF_ROOT / "v1.0.4_20230127" / "CMR2_0.346_CMC_0.424_S_Edmund"
            / "present_day_0.346_0.424_0.0.csv")
V105_CSV = (REF_ROOT / "self_v1.0.5" / "CMR2_0.346_CMC_0.424_S_Edmund"
            / "pMetaData_0.00.csv")

UNTOUCHED_FIELDS = [
    "rhom", "mass", "moi", "cmc", "Picb", "Tcmb", "chi_li_in", "Pcmb",
    "chi_li_eut_icb", "chi_li_eut_cmb", "rcmb", "chi_li_icb",
]
CORE_MASS_PREFACTOR_RATIO = (4.0 / 3.0) * math.pi  # v1.0.4 lacked BOTH 4/3 and pi


def _rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def paired_rows():
    old_rows = _rows(V104_CSV)
    new_rows = _rows(V105_CSV)
    assert len(old_rows) == len(new_rows) == 17, (
        f"expected 17 comparable rows in both files, got "
        f"{len(old_rows)} (v1.0.4) and {len(new_rows)} (v1.0.5) -- if the "
        f"self-golden was regenerated with a different convergence cutoff, "
        f"this pairing needs re-establishing, not silently truncating"
    )
    for o, n in zip(old_rows, new_rows):
        assert o["ricb"] == n["ricb"], "rows are not on the same ricb grid"
    return list(zip(old_rows, new_rows))


@pytest.mark.parametrize("field", UNTOUCHED_FIELDS)
def test_untouched_field_matches_v1_0_4_exactly(paired_rows, field):
    for i, (o, n) in enumerate(paired_rows):
        ov, nv = float(o[field]), float(n[field])
        diff = abs(nv - ov)
        bound = 1e-6 * max(abs(ov), 1e-12)
        assert not (diff > bound), (
            f"row {i} (ricb={o['ricb']}) field '{field}': v1.0.4={ov!r} "
            f"current={nv!r} diff={diff!r} exceeds rtol=1e-6 -- this field "
            f"was NOT supposed to have changed since v1.0.4 (2023-01-27); "
            f"see testsys/reference/v1.0.4_20230127/PROVENANCE.md"
        )


def test_core_mass_delta_matches_known_volume_prefactor_fix(paired_rows):
    for i, (o, n) in enumerate(paired_rows):
        ratio = float(n["core_mass"]) / float(o["core_mass"])
        assert ratio == pytest.approx(CORE_MASS_PREFACTOR_RATIO, rel=1e-6), (
            f"row {i}: core_mass ratio (current/v1.0.4)={ratio!r}, expected "
            f"exactly (4/3)*pi={CORE_MASS_PREFACTOR_RATIO!r} (the known "
            f"get_mass_core volume-prefactor fix) -- a DIFFERENT ratio here "
            f"means a NEW, unattributed divergence in core_mass, not the "
            f"documented one"
        )


def test_isnow_deltas_are_within_the_documented_reclassification_count(paired_rows):
    # Not gated to equality (isnow classification is KNOWN to have changed,
    # 2a9d576) -- but a change in HOW MANY rows disagree, or a value
    # outside the documented {1,2,3} classification set, is worth knowing
    # about rather than silently absorbing.
    differing = 0
    for o, n in paired_rows:
        ov, nv = float(o["isnow"]), float(n["isnow"])
        assert ov in (0.0, 1.0, 2.0, 3.0) and nv in (0.0, 1.0, 2.0, 3.0), (
            f"isnow value outside the documented {{0,1,2,3}} classification: "
            f"v1.0.4={ov!r} current={nv!r}"
        )
        if ov != nv:
            differing += 1
    assert differing == 10, (
        f"{differing}/17 rows have a different isnow classification than "
        f"v1.0.4 (documented count: 10 -- see PROVENANCE.md); a DIFFERENT "
        f"count means the classification logic changed again since this "
        f"delta was documented, worth a fresh look even though it isn't a "
        f"hard failure"
    )
