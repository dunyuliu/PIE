"""PATHWAY_FORWARD.md item 23(d): no hydrostatic-residual test existed.
This is a physics sanity check independent of any reference data
(PROJECT_RULES.md rule 2's "independent closed-form check") -- it
derives its own expectation from the ODE the solver itself integrates,
not from a committed golden file.

`src/solver.py::rhs_fluid_snow`'s first equation (read directly from
source, non-dimensional form):

    dy[0]/dr = -(a*ga/P) * rho * y[1]

where y[0]=P/P_scale, y[1]=g/ga, r is non-dimensional radius. Converting
to physical units (P_phys = P_scale*y[0], r_phys = a*r, g_phys = ga*y[1]):

    dP_phys/dr_phys = -rho_phys * g_phys

-- exactly hydrostatic equilibrium, dP/dr + rho*g = 0. This file checks
that identity holds POINTWISE on the solver's OWN converged output
profile (a numerical, central-difference dP/dr compared against
-rho*g), not a re-derivation of the physics from scratch -- a sign
error in rho/g/P scaling, or a units mismatch (Mars-Climate-Orbiter
class bug), would show up here as a large residual.

Checked on the FLUID-core segment only (the fixed-step, nc=51 RK4 grid,
same NC_FLUID convention as test_steinbruegge_anchor.py) -- central
differences need a known, uniform grid spacing to be accurate; the
solid inner-core segment uses scipy's adaptive LSODA stepping (non-
uniform spacing), where a naive central difference would conflate
discretisation error from the uneven grid with any real hydrostatic
violation, which is not what this test is designed to isolate.

Tolerance: 1e-3 relative, interior points only (excluding the first and
last fluid-grid point, where a one-sided finite difference is lower-
order and expectedly noisier). Measured directly on this box,
2026-10-01 (Margot CMR2=0.346/CMC=0.424, S-only, ricb=500 km): worst
INTERIOR relative residual 3.5e-4; the two boundary points are 1-2
orders of magnitude worse purely from the one-sided-difference
truncation error (worst 1.75e-2), which is why they are excluded rather
than loosening the interior bound to cover them. The 1e-3 bound is
~3x the measured interior worst case, not an assumed noise floor.
"""
import numpy as np
import pytest

pytestmark = pytest.mark.integration

from conftest import solve_full_model

NC_FLUID = 51  # src/shootp.py's own hard-coded fluid-core RK4 node count

CASES = [
    (0.346, 0.424, "S", "Edmund", 500_010.0),
    (0.333, 0.443, "Si", "Edmund", 400_010.0),
    (0.346, 0.424, "S+Si", "Edmund", 500_010.0),
]


@pytest.mark.parametrize("CMR2,CMC,light,liquidus,ricb_m", CASES,
                          ids=["margot_S", "genova_Si", "margot_SpSi_001"])
def test_hydrostatic_equilibrium_holds_pointwise(CMR2, CMC, light, liquidus, ricb_m):
    """dP/dr + rho*g ~= 0 pointwise on the converged fluid-core profile,
    an independent closed-form check derived from the ODE src/solver.py
    itself integrates (see module docstring) -- not committed-golden
    comparison."""
    chi_si = 0.01 if light == "S+Si" else None
    result = solve_full_model(CMR2, CMC, light, liquidus, ricb_m, chi_Si_icb=chi_si)
    r = np.asarray(result["profiles"]["r"][-NC_FLUID:])
    rho = np.asarray(result["profiles"]["rho"][-NC_FLUID:])
    P = np.asarray(result["profiles"]["P"][-NC_FLUID:])
    g = np.asarray(result["profiles"]["g"][-NC_FLUID:])

    dPdr = np.gradient(P, r)
    residual = dPdr + rho * g
    denom = np.abs(rho * g)
    rel = np.abs(residual) / denom

    # Interior points only (exclude the two boundary points -- see
    # module docstring on why their one-sided finite difference is
    # expectedly noisier, not a real hydrostatic violation).
    worst_rel = float(np.max(rel[1:-1]))
    worst_idx = int(np.argmax(rel[1:-1])) + 1
    assert not (worst_rel > 1e-3), (
        f"CMR2={CMR2} CMC={CMC} light={light} liquidus={liquidus} "
        f"ricb_m={ricb_m}: worst interior hydrostatic residual "
        f"|dP/dr + rho*g| / |rho*g| = {worst_rel!r} at fluid-node index "
        f"{worst_idx} exceeds 1e-3 -- a real hydrostatic-equilibrium "
        f"violation (units/sign/scaling bug), not finite-difference noise"
    )
