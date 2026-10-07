"""Regression anchor (PROJECT_RULES.md rule 5): current HEAD vs v1.0.3
(2022-10-21), the oldest still-runnable predecessor named on the board
(`PATHWAY_FORWARD.md` item 2). This is PARITY WITH UNTESTED LEGACY CODE,
not evidence of correctness -- v1.0.3 predates the `bb37b0a` fix to
`get_mass_core`'s missing `(4/3)*pi` volume prefactor (confirmed
directly in the v1.0.3 snapshot's own `libCore.py`, same bug as the
v1.0.4 anchor in `tests/integration/test_v1_0_4_regression_history.py`)
-- see `tests/reference/v1.0.3_20221021/PROVENANCE.md` for the full
generation/attribution trail, including why the Si-only anchor uses the
'genova' preset rather than 'margot' (margot Si-only does not converge
in v1.0.3 itself, confirmed by rerun, not by inspection).

v1.0.3 identifies compositions by NAMED PRESET ('margot'/'genova'), not
numeric (CMR2, CMC) -- 'margot' -> CMR2=0.346, CmC=0.148/0.346;
'genova' -> CMR2=0.333, CmC=0.148/0.333 (v1.0.3 planet_input.py). This
test uses those exact preset-derived numbers as the numeric (CMR2, CMC)
arguments to current HEAD's `solve_full_model`, at the same ricb_m grid
v1.0.3's own present-day sweep used (radius column `ricb` in the
committed CSVs) -- an apples-to-apples comparison, NOT the CMR2=0.346/
CMC=0.424 pair used by this repo's OTHER Margot-fit fixtures (a later,
different convention -- see `tests/integration/test_truth_anchor_margot_fit.py`
for that one, a truth anchor, not this regression anchor).

`core_mass` is gated to the KNOWN, documented ratio (exactly
`(4/3)*pi`), not equality -- a DIFFERENT ratio would mean a new,
unattributed divergence. Every other field is gated to rtol=1e-6
(equality): measured deltas (see PROVENANCE.md) are ~1e-9-1e-12 for
every case, so 1e-6 has a >=1000x margin over the worst measured value
while still catching a real regression.
"""
import csv
import math
import pathlib

import pytest

from pielib import solve_full_model

pytestmark = [pytest.mark.integration, pytest.mark.parity]

REF_ROOT = pathlib.Path(__file__).resolve().parent.parent / "reference" / "v1.0.3_20221021"
CORE_MASS_PREFACTOR_RATIO = (4.0 / 3.0) * math.pi

UNTOUCHED_FIELDS = [
    "rhom", "mass", "moi", "cmc", "Picb", "Tcmb", "chi_li_in", "Pcmb",
    "rcmb", "chi_li_icb",
]


def _rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


CASES = [
    ("margot_S_Edmund/csvfiles/present_day_margot_0.0.csv", 0.346, 0.148 / 0.346, "S"),
    ("genova_Si_Edmund/csvfiles/present_day_genova_0.0.csv", 0.333, 0.148 / 0.333, "Si"),
]


@pytest.mark.parametrize("csv_rel,CMR2,CMC,light_element", CASES)
def test_matches_v1_0_3_preset(csv_rel, CMR2, CMC, light_element):
    rows = _rows(REF_ROOT / csv_rel)
    assert len(rows) == 13, (
        f"{csv_rel}: expected 13 v1.0.3 rows (see PROVENANCE.md), got "
        f"{len(rows)} -- if this fixture was regenerated with a different "
        f"convergence cutoff, update this count deliberately, don't drift"
    )
    # Two representative radii (first past ricb=10 m, and the last row
    # both v1.0.3 files share) rather than all 13 -- each solve is
    # ~15-20s (conftest.solve_full_model docstring); 13 live solves per
    # composition would push this well past "integration: seconds each".
    for row in (rows[1], rows[-1]):
        ricb_m = float(row["ricb"])
        computed = solve_full_model(CMR2, CMC, light_element, "Edmund", ricb_m)
        context = f"{csv_rel} ricb={ricb_m}: "

        for field in UNTOUCHED_FIELDS:
            v103, cur = float(row[field]), computed["scalars"][field]
            diff = abs(cur - v103)
            bound = 1e-6 * max(abs(v103), 1e-12)
            assert not (diff > bound), (
                f"{context}field '{field}': v1.0.3={v103!r} current={cur!r} "
                f"diff={diff!r} exceeds rtol=1e-6"
            )

        isnow_v103, isnow_cur = float(row["isnow"]), computed["scalars"]["isnow"]
        assert isnow_cur == pytest.approx(isnow_v103, abs=1e-9), (
            f"{context}isnow classification changed: v1.0.3={isnow_v103!r} "
            f"current={isnow_cur!r} -- NOT a documented delta for this "
            f"pair (unlike the v1.0.4 anchor's isnow reclassification), "
            f"worth investigating"
        )

        ratio = computed["scalars"]["core_mass"] / float(row["core_mass"])
        assert ratio == pytest.approx(CORE_MASS_PREFACTOR_RATIO, rel=1e-6), (
            f"{context}core_mass ratio (current/v1.0.3)={ratio!r}, expected "
            f"exactly (4/3)*pi={CORE_MASS_PREFACTOR_RATIO!r} (the known "
            f"get_mass_core volume-prefactor fix) -- a DIFFERENT ratio "
            f"means a NEW, unattributed divergence"
        )
