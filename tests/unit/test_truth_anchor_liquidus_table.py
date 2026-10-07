"""Truth anchor (PROJECT_RULES.md rule 5): self-consistency of the
Fe-S liquidus DATA SOURCE `src/coreEos.py` uses, not a fit or a
regression comparison.

`src/coreEos.py`'s `meltingDataFromFile` builds a bicubic interpolating
spline (`RectBivariateSpline(..., s=0)`, an EXACT interpolant, not a
smoothed fit) over the (S wt fraction, pressure) grid tabulated in
`src/TmFeSmelt.dat` -- itself the digitised Fe-S liquidus curve this
codebase inherited from its predecessor (`coreEos.py`'s own file header
credits Gregor Steinbruegge, whose `MercuryInterior` repo is the
Steinbruegge et al. (2020, doi:10.1029/2020GL089895) reference
implementation this project's `liquidus_eq='Steinbruegge'` option is
named for).

`tests/unit/test_coreEos.py::test_melting_data_from_file_loads_and_is_finite`
already checks the loader doesn't crash and returns a finite, positive
number -- it does NOT check the returned value is the TABULATED one.
This file closes that gap: at grid nodes (the exact (x, p) pairs
`TmFeSmelt.dat` lists), the spline must reproduce the file's own T
value, because `s=0` in `RectBivariateSpline` requests EXACT
interpolation (zero smoothing), not a least-squares fit that is merely
close. If a future edit accidentally switches to `s>0` smoothing, or
transposes the (x, p) axes, or reads the wrong column out of the file,
the interpolant would stop passing through its own input data and this
test would catch it -- a case `test_melting_data_from_file_loads_and_is_finite`
structurally cannot, since a transposed-but-still-finite value passes
that check.

Points below were extracted directly from `src/TmFeSmelt.dat` (header:
`0 12 49 0 40 401` -> 49 x-nodes in [0, 12] wt%, 401 p-nodes in
[0, 40] GPa) at grid indices (i, j) = (0,0), (10,50), (24,200),
(48,400) -- two corners, the domain centre, and one more interior point
-- via `awk 'NR>3{print NR-4,$0}' src/TmFeSmelt.dat | awk
'{idx=$1;i=int(idx/401);j=idx%401; ...}'`, not retyped by hand.

Measured: a fresh solve on this box reproduces all four to
~1e-16 relative (float64 round-off) -- `RectBivariateSpline(s=0)` is
a genuine interpolant, so exact reproduction at nodes is not a
coincidence needing a loose tolerance; rtol=1e-8 here is already a
generous ~1e8x margin over the measured round-off.
"""
import pytest

pytestmark = pytest.mark.unit

from pie import coreEos as eos

# (x wt fraction, p GPa, T Kelvin) -- verbatim from src/TmFeSmelt.dat
GRID_NODES = [
    (0.0, 0.0, 1801.6248087566335),      # (i, j) = (0, 0): corner
    (0.025, 5.0, 1904.0952069441332),    # (i, j) = (10, 50): interior
    (0.06, 20.0, 2110.8685205268002),    # (i, j) = (24, 200): domain centre
    (0.12, 40.0, 1623.3690472706148),    # (i, j) = (48, 400): opposite corner
]


@pytest.fixture(scope="module")
def melt_table():
    return eos.meltingDataFromFile("TmFeSmelt.dat")


@pytest.mark.parametrize("x_wt,p_gpa,t_tabulated", GRID_NODES)
def test_melting_spline_reproduces_tabulated_node_exactly(melt_table, x_wt, p_gpa, t_tabulated):
    t_interp = float(melt_table(x_wt, p_gpa))
    diff = abs(t_interp - t_tabulated)
    bound = 1e-8 * abs(t_tabulated)
    assert not (diff > bound), (
        f"meltingDataFromFile({x_wt}, {p_gpa}) = {t_interp!r}, tabulated "
        f"src/TmFeSmelt.dat value = {t_tabulated!r}, diff={diff!r} exceeds "
        f"rtol=1e-8 -- an s=0 interpolating spline should reproduce its own "
        f"input data at the exact grid nodes to float round-off, not merely "
        f"approximate it"
    )
