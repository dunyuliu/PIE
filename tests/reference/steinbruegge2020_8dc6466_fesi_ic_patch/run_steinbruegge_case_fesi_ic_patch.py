#!/usr/bin/env python3
"""Subprocess-only runner for the FeSi-inner-core-PATCHED copy of the
vendored Steinbruegge et al. (2020) reference code (see README.md in
this directory for exactly what is patched and why -- item 23(c)).

MUST be invoked as its own interpreter process, same reasoning as
tests/reference/steinbruegge2020_8dc6466/run_steinbruegge_case.py:
this directory's module is also named coreEos (and libcore), clashing
with PIE's src/coreEos.py AND with the unpatched reference dir's own
coreEos.py/libcore.py -- a same-process import after either of those
would silently reuse whichever module Python's import cache saw
first. tests/integration/test_steinbruegge_fesi_inner_core_patch.py
runs this via subprocess.run with cwd restricted to this directory.

Usage:
    /usr/bin/python3 run_steinbruegge_case_fesi_ic_patch.py li_el ricb_m out.json
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
        name='testsys_anchor_fesi_ic_patch',
    )
    return param


def solve_one_case(li_el, ricb_m):
    """Identical to the unpatched runner's solve_one_case -- see that
    file's docstring. Only the imported coreEos/libcore modules (this
    directory's patched copies) differ."""
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
            "STB(patched) Newton solve did not converge: li_el=%s "
            "ricb_m=%s" % (li_el, ricb_m))

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
            "usage: run_steinbruegge_case_fesi_ic_patch.py li_el ricb_m "
            "out.json")
    li_el, ricb_m_s, out_path = argv[1], argv[2], argv[3]
    if li_el != 'Si':
        raise SystemExit(
            "this patched runner only differs from the unpatched one for "
            "li_el='Si' (got %r); use the unpatched runner for li_el='S'" %
            (li_el,))
    ricb_m = float(ricb_m_s)
    result = solve_one_case(li_el, ricb_m)
    with open(out_path, 'w') as fh:
        json.dump(result, fh)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
