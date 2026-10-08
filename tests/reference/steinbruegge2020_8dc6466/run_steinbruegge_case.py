#!/usr/bin/env python3
"""Subprocess-only runner for the vendored Steinbruegge et al. (2020)
reference code (coreEos.py/libcore.py, pinned commit
8dc64663c574bc9dc1b3ecbb74252fbb3b1a2383 -- see README.txt).

MUST be invoked as its own interpreter process (never imported into a
process that has also imported PIE's src/): this package's module is
named coreEos, identical to src/coreEos.py's module name, so a
same-process import after PIE's own would silently reuse whichever
module Python's import cache saw first --
test_steinbruegge_anchor.py runs this via subprocess.run with a cwd
restricted to this directory so this dir's coreEos.py/libcore.py
resolve first on sys.path, and PIE's src/ is never on that
subprocess's sys.path.

Reproduces run_models.py's single-radius solve for one (li_el,
ricb_m) case and dumps every quantity the anchor test compares, in
RAW SI UNITS (radius m, pressure Pa, temperature K, density kg/m3) --
NOT libcore.py's internal non-dimensional form.

Usage:
    /usr/bin/python3 run_steinbruegge_case.py li_el ricb_m out.json
"""
import json
import sys

import numpy as np
from scipy.constants import G

import coreEos as eos
import libcore as lc


def build_param(li_el):
    MFeS = (55.845 + 32.065)
    MFeSi = (55.845 + 28.08)
    MFe = 55.845

    fccFe = eos.eosAndersonGrueneisen(
        M0=MFe, p0=1.e-5, T0=298, V0=6.82, alpha0=7.e-5, KT0=163.4,
        KTP0=5.38, deltaT=5.5, kappa=1.4, GibbsE=eos.GibbsfccFe)

    liquidFe = eos.eosAndersonGrueneisen(
        M0=MFe, p0=1E-5, T0=298, V0=6.88, alpha0=9E-5, KT0=148,
        KTP0=5.8, deltaT=5.1, kappa=0.56, GibbsE=eos.GibbsLiquidFe)

    liquidFeS = eos.eosAndersonGrueneisen(
        M0=MFeS, p0=1E-5, T0=1650, V0=22.956500240757844, alpha0=11.9e-5,
        KT0=17.01901122392699, KTP0=5.92217679116356,
        deltaT=5.92217679116356, kappa=1.4, gamma0=1.3, q=0)

    liquidFeSi = eos.eosAndersonGrueneisen(
        M0=MFeSi, p0=1E-5, T0=1723, V0=16.5839, alpha0=17.6525e-5,
        KT0=69.0074, KTP0=7.76007, deltaT=4.07505, kappa=0.56,
        gamma0=1.61986, q=0)

    param = dict(
        rm=2439360.0,
        GM=22031.86E+9,
        c22=0.804151E-05,
        CmC=0.148 / 0.333,
        CMR2=0.333,
        MFe=MFe, MS=32.065, MSi=28.08,
        MFeS=MFeS, MFeSi=MFeSi,
        lFe=liquidFe, lFeS=liquidFeS, lFeSi=liquidFeSi,
        fccFe=fccFe,
        li_el=li_el,
        name='testsys_anchor',
    )
    return param


def solve_one_case(li_el, ricb_m):
    """Solve a single (li_el, ricb_m) case; return raw-SI-unit scalars
    and fluid-core-node profiles as a JSON-able dict.

    xtol=ftol=1e-5, maxit=6 and v0=[0.8,1,0.8,0.7,0.05] are
    run_models.py's own published values (not loosened/tightened here)
    -- see docs/dev/notes/steinbruegge_anchor_2026-09-30.md Newton line.
    """
    param = build_param(li_el)
    M = param['GM'] / G
    rm = param['rm']
    rhomean = 3 * M / (4 * np.pi * rm ** 3)
    scale = dict(
        a=rm,
        ga=M * G / rm ** 2,
        P=rhomean * rm * M * G / rm ** 2,
        T=1800,
    )

    rhocr = 2974
    hcr = 26e3
    rh = (rm - hcr) / scale['a']
    v0 = [0.8, 1.0, 0.8, 0.7, 0.05]
    ricb_nd = ricb_m / scale['a']

    v = lc.mynewtonSys(
        'J_mercmodel', v0, [ricb_nd, rhocr, rh, param, scale],
        xtol=1e-5, ftol=1e-5, maxit=6, verbose=False,
    )
    if v is None:
        raise RuntimeError(
            "STB Newton solve did not converge: li_el=%s ricb_m=%s" %
            (li_el, ricb_m))

    f, r, yy, fout = lc.shoot_mercmodel(v, ricb_nd, rhocr, rh, param, scale)

    r_phys = scale['a'] * r
    P_phys = scale['P'] * yy[0]
    g_phys = scale['ga'] * yy[1]
    T_phys = scale['T'] * yy[2]
    rho_phys = rhomean * yy[4]
    chi = yy[5]

    rcmb = v[2] * scale['a']
    rhom = v[3] * rhomean
    chi_li_icb = v[4]
    Picb, Tcmb, isnow, isnowcmb, chi_li_in, gradTa = fout
    Pcmb = float(P_phys[-1])

    # Fluid-core nodes only (last 51 = the fixed-step RK4 grid) -- the
    # solid inner-core segment is an adaptive-step LSODA grid whose
    # node PLACEMENT can differ between scipy versions/codebases even
    # when the underlying solution agrees to solver tolerance, so
    # comparing it point-by-point is a resampling artifact, not a
    # physics difference (anchor note: "Interp-based profile
    # comparison ... is a comparison artifact"). nc=51 is libcore.py's
    # own hard-coded fluid-core node count.
    nc = 51
    profile = dict(
        r=r_phys[-nc:].tolist(),
        rho=rho_phys[-nc:].tolist(),
        P=P_phys[-nc:].tolist(),
        T=T_phys[-nc:].tolist(),
        g=g_phys[-nc:].tolist(),
        chi_li=chi[-nc:].tolist(),
    )

    scalars = dict(
        rcmb=float(rcmb), rhom=float(rhom),
        Pcmb=float(Pcmb), Picb=float(Picb),
        Tcmb=float(Tcmb), chi_li_icb=float(chi_li_icb),
        chi_li_in=float(chi_li_in), isnow=float(isnow),
        isnowcmb=float(isnowcmb),
    )

    return dict(
        li_el=li_el, ricb_m=ricb_m,
        scalars=scalars,
        profiles=profile,
    )


def main(argv):
    if len(argv) != 4:
        raise SystemExit(
            "usage: run_steinbruegge_case.py li_el ricb_m out.json")
    li_el, ricb_m_s, out_path = argv[1], argv[2], argv[3]
    if li_el not in ('S', 'Si'):
        raise SystemExit("li_el must be S or Si, got %r" % (li_el,))
    ricb_m = float(ricb_m_s)
    result = solve_one_case(li_el, ricb_m)
    with open(out_path, 'w') as fh:
        json.dump(result, fh)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
