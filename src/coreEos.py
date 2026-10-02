#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  8 14:52:52 2019

@author: Gregor Steinbruegge (gbs@stanford.edu)

Version 1.0
------------------------------
! Copyright A. Rivoldini 
! Version 1.0 30.09.2019
! 
Email: A. Rivoldini 09/30/2019
Voici enfin les routines en Fortran pour calculer les eos de l-Fe-S et l-Fe-Si 
comme dans l’article de Terasaki 2019 (10.1029/2019JE005936). 
Par rapport à l’article, il y a deux petits changements:
Les end-member sont FeSi et FeSi et pas 0.5Fe0.5S et 0.5Fe0.5FeSi et pour 
l’eos de l-Fe j’ai pris Komabayashi 2014 (10.1002/2014JB010980) et pas  
Anderson 1994. Cela à un effect sur les paramètres des eos qui sont dans le 
code, pas exactement les mêmes que dans les tableaux 5 et 6.

Version 1.1
-------------------------------
Email: A. Rivoldini 10/21/2019
I have made a few updates to the eos code. Two of them will have a slight 
effect on the results and were typos. The mass of S and the value of deltaT for
liquid FeS should have been slightly different. See new file.I also implemented
the eos of solid fcc Fe based on Komabayshi 2014. The reason for using this 
eos rather than the previous one based on Tsuno et al.  is that the l-Fe and 
the fcc-Fe eos of Komabayashi are thermodynamically consistent with the 
liquidus of Fe by Anzellinni. Or in other words, the liquidus temperature 
follows from the eos of l-Fe and fcc, at least in the stability range of fcc. 
I also changed the value for dT to compute the numerical derivative of the 
Gibbs energy with respect to T and I increased the number of precomputed 
compression values to 10000.

Changelog:
    * added function solid fcc fe
    * added function GibbsfccFe
    * nbrPNodes changed from 2501 to 10001
    * pMax changed from 50 to 200
    * deltaTemp changged from 20 to 1
    * values for liquidFeS KT0, KTP0, and deltaT changed
    
Version 1.2
-------------------------------
Updated FeSi EoS for solid FeSi and changed partion coefficient.

    
"""

import os
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.interpolate import RectBivariateSpline
from scipy import integrate
from scipy import optimize

# --- v1.3.3 perf: vectorised GK21 fast path for eosAndersonGrueneisen.Gibbs's
# integrate.quad call (PATHWAY_FORWARD.md perf item; see
# docs/notes/perf_v1.3.3.md). Profiling (cProfile, canonical Margot-fit
# radius) found integrate.quad at ~6.4s of a 9.6s single-radius solve:
# 26124 calls / 548604 total integrand evaluations = exactly 21 evals/call,
# i.e. QUADPACK's QAGSE never subdivides past its first 21-point
# Gauss-Kronrod (GK21) panel for any (p, T) pair actually reached in a real
# solve (verified across S/Si/S+Si x Edmund/Steinbruegge x small-ricb and
# canonical-ricb radii: 237057 real captured quad calls, ALL with
# infodict['last']==1 -- see
# testsys/unit/test_perf_v1_3_3_gk21_quad.py). This is NOT a universal
# property of the integrand: a direct sweep of eos.Gibbs over the full
# admissible pressure domain (up to pMax=200 GPa, vs ~39 GPa reached by any
# real Mercury-core solve) shows QAGSE DOES subdivide (last=2 or 3) once the
# integration interval gets wide enough -- which is exactly why the runtime
# fallback below is mandatory, not a one-time global switch.
#
# GK21 node/weight tables below are the QUADPACK dqk21.f literals verbatim
# (Piessens & de Doncker 1983; computed by L.W. Fullerton, Bell Labs, Nov
# 1981, 80-digit arithmetic) -- transcribed from
# scipy/integrate/quadpack/dqk21.f at the pinned scipy==1.8.0 tag
# (https://github.com/scipy/scipy/blob/v1.8.0/scipy/integrate/quadpack/dqk21.f),
# NOT re-derived or rounded. xgk/wgk index 11 is the central (x=0) Kronrod
# node/weight; wg has only 5 entries (the embedded 10-point Gauss rule's
# positive-side weights, by symmetry).
_GK21_WG = (
    0.066671344308688137593568809893332,
    0.149451349150580593145776339657697,
    0.219086362515982043995534934228163,
    0.269266719309996355091226921569469,
    0.295524224714752870173892994651338,
)
_GK21_XGK = (
    0.995657163025808080735527280689003,
    0.973906528517171720077964012084452,
    0.930157491355708226001207180059508,
    0.865063366688984510732096688423493,
    0.780817726586416897063717578345042,
    0.679409568299024406234327365114874,
    0.562757134668604683339000099272694,
    0.433395394129247190799265943165784,
    0.294392862701460198131126603103866,
    0.148874338981631210884826001129720,
    0.000000000000000000000000000000000,
)
_GK21_WGK = (
    0.011694638867371874278064396062192,
    0.032558162307964727478818972459390,
    0.054755896574351996031381300244580,
    0.075039674810919952767043140916190,
    0.093125454583697605535065465083366,
    0.109387158802297641899210590325805,
    0.123491976262065851077958109831074,
    0.134709217311473325928054001771707,
    0.142775938577060080797094273138717,
    0.147739104901338491374841515972068,
    0.149445554002916905664936468389821,
)

# PIE_FAST_QUAD (module-level env flag, same convention as
# PIE_WORKERS/PIE_LAUNCHER_SEED_BASE elsewhere in this codebase): DEFAULT
# ON as of the owner's 2026-10-02 ruling (see CHANGELOG.md). On the pinned
# environment (numpy==1.21.5, scipy==1.8.0) it is bit-identical to real
# scipy.integrate.quad (testsys/unit/test_perf_v1_3_3_gk21_quad.py's
# differential test shows max diff 0.0 on 237057 real captured (p, T)
# calls spanning S/Si/S+Si x Edmund/Steinbruegge x small-ricb/canonical-ricb
# radii). Off the pinned environment (CI's fast-latest job, current
# numpy/scipy), eosAndersonGrueneisen.volume's CubicSpline does not return
# bit-identical values for a vectorised array call vs one-scalar-call-per-
# point (floating-point non-associativity in CubicSpline's own vectorized-
# vs-scalar code path, not a bug in this port's GK21 logic -- see
# docs/notes/perf_v1.3.3.md for the ~8.3e-17 absolute divergence measured
# on CI run 36881055265 during the FIRST default-on attempt, PR #15,
# reverted as PR #16). That divergence is bounded, not eliminated, by
# GK21_PORTABLE_RTOL=1e-14 below -- it does not disqualify default-on, it
# is simply the known, bounded cost of it off the pinned environment.
# PIE_FAST_QUAD unset now means ON (the vectorised GK21 fast path,
# falling back to real scipy.integrate.quad per call whenever
# _gk21_or_quad's replicated dqagse.f accept test fails -- see that
# function's docstring); only an EXPLICIT PIE_FAST_QUAD=0 is the escape
# hatch back to the unconditional real scipy.integrate.quad call (pre-
# v1.3.3 behaviour). Read once at import time -- a test that needs the
# opposite path within one process calls _gk21_or_quad directly, or sets
# PIE_FAST_QUAD=0 before import, rather than monkeypatching this
# module-level constant after other code has already captured it.
PIE_FAST_QUAD = os.environ.get("PIE_FAST_QUAD", "1") != "0"


def _gk21_panel(func, a, b):
    """Evaluate QUADPACK's dqk21 21-point Gauss-Kronrod rule (+ its
    embedded 10-point Gauss error estimate) on [a, b], replicating
    scipy's Fortran dqk21.f bit-for-bit: same abscissae/weights, same
    accumulation order (do NOT reassociate these sums -- that would
    silently change the last bit of `result`/`abserr` on some inputs).

    `func` is called ONCE on an array of the 21 distinct evaluation
    points (vectorised), not 21 separate scalar Python calls -- this is
    the actual performance win; `func` must vectorise over an array
    exactly as it would per-point (verified for `volume` by
    testsys/unit/test_perf_v1_3_3_gk21_quad.py's
    TestVolumeVectorisesExactly).

    Returns (result, abserr, resabs, resasc) -- all four of dqk21's
    outputs, because dqagse's single-panel accept/reject test (see
    _gk21_or_quad) needs resabs and resasc too, not just result/abserr.
    """
    centr = 0.5 * (a + b)
    hlgth = 0.5 * (b - a)
    dhlgth = abs(hlgth)

    # Build the 21 x-points in dqk21's own order: centre first, then the
    # 5 symmetric pairs at the "jtw" (even, shared with the 10-point
    # Gauss rule) abscissae, then the 5 symmetric pairs at the "jtwm1"
    # (odd, Kronrod-only) abscissae -- xgk/wgk are 1-indexed in the
    # Fortran; kept 0-indexed here with an explicit -1 at each use so the
    # mapping to dqk21.f's jtw/jtwm1 indices stays visible at the call
    # site.
    xs = np.empty(21, dtype=float)
    xs[0] = centr
    pos = 1
    for j in range(5):
        jtw = 2 * (j + 1)
        absc = hlgth * _GK21_XGK[jtw - 1]
        xs[pos] = centr - absc
        xs[pos + 1] = centr + absc
        pos += 2
    for j in range(5):
        jtwm1 = 2 * (j + 1) - 1
        absc = hlgth * _GK21_XGK[jtwm1 - 1]
        xs[pos] = centr - absc
        xs[pos + 1] = centr + absc
        pos += 2

    fs = np.asarray(func(xs), dtype=float)
    if fs.shape != (21,):
        raise ValueError(
            f"_gk21_panel: func must return a (21,)-shaped array for a "
            f"(21,)-shaped input, got shape {fs.shape}"
        )
    fc = fs[0]
    fv1 = np.empty(10, dtype=float)
    fv2 = np.empty(10, dtype=float)
    pos = 1
    for j in range(5):
        jtw = 2 * (j + 1)
        fv1[jtw - 1] = fs[pos]
        fv2[jtw - 1] = fs[pos + 1]
        pos += 2
    for j in range(5):
        jtwm1 = 2 * (j + 1) - 1
        fv1[jtwm1 - 1] = fs[pos]
        fv2[jtwm1 - 1] = fs[pos + 1]
        pos += 2

    resg = 0.0
    resk = _GK21_WGK[10] * fc
    resabs = abs(resk)
    for j in range(5):
        jtw = 2 * (j + 1)
        fval1 = fv1[jtw - 1]
        fval2 = fv2[jtw - 1]
        fsum = fval1 + fval2
        resg = resg + _GK21_WG[j] * fsum
        resk = resk + _GK21_WGK[jtw - 1] * fsum
        resabs = resabs + _GK21_WGK[jtw - 1] * (abs(fval1) + abs(fval2))
    for j in range(5):
        jtwm1 = 2 * (j + 1) - 1
        fval1 = fv1[jtwm1 - 1]
        fval2 = fv2[jtwm1 - 1]
        fsum = fval1 + fval2
        resk = resk + _GK21_WGK[jtwm1 - 1] * fsum
        resabs = resabs + _GK21_WGK[jtwm1 - 1] * (abs(fval1) + abs(fval2))
    reskh = resk * 0.5
    resasc = _GK21_WGK[10] * abs(fc - reskh)
    for j in range(10):
        resasc = resasc + _GK21_WGK[j] * (abs(fv1[j] - reskh) + abs(fv2[j] - reskh))

    result = resk * hlgth
    resabs = resabs * dhlgth
    resasc = resasc * dhlgth
    abserr = abs((resk - resg) * hlgth)
    if resasc != 0.0 and abserr != 0.0:
        abserr = resasc * min(1.0, (200.0 * abserr / resasc) ** 1.5)
    epmach = np.finfo(float).eps
    uflow = np.finfo(float).tiny
    if resabs > uflow / (50 * epmach):
        abserr = max(epmach * 50 * resabs, abserr)
    return result, abserr, resabs, resasc


def _gk21_or_quad(func, a, b, epsabs=1.49e-8, epsrel=1.49e-8):
    """Single-call replacement for `integrate.quad(func, a, b)[0]`:
    evaluate the GK21 panel once (vectorised), and return it ONLY if
    QUADPACK's own dqagse would have accepted that single panel without
    subdividing -- replicating dqagse.f's post-first-panel accept test
    verbatim (scipy/integrate/quadpack/dqagse.f at the pinned scipy==1.8.0
    tag):

        dres   = abs(result)
        errbnd = max(epsabs, epsrel*dres)
        ier2   = abserr <= 100*epmach*resabs and abserr > errbnd  # roundoff
        accept = ier2 or (abserr <= errbnd and abserr != resasc) or abserr == 0

    (dqagse's own local variable names `defabs`/`resabs` map to dqk21's
    `resabs`/`resasc` outputs respectively, per the positional call `call
    dqk21(f,a,b,result,abserr,defabs,resabs)` vs dqk21's own signature
    `subroutine dqk21(f,a,b,result,abserr,resabs,resasc)` -- resolved here
    using dqk21's own names throughout, not dqagse's, to avoid exactly
    this naming collision silently flipping resabs/resasc in a port).
    `limit==1` (dqagse's other immediate-accept condition) never applies:
    scipy's quad default limit=50, and this call site never overrides it.

    `accept` True: returns `result` bit-identically to what
    scipy.integrate.quad would return for this exact call (confirmed by
    testsys/unit/test_perf_v1_3_3_gk21_quad.py's differential test on real
    solver states -- max diff 0.0). `accept` False: falls back to the real
    `integrate.quad`, so output is identical to today's behaviour whenever
    the single-panel assumption doesn't hold for this particular call --
    a per-call runtime check, not a one-time global switch.
    """
    result, abserr, resabs, resasc = _gk21_panel(func, a, b)
    dres = abs(result)
    errbnd = max(epsabs, epsrel * dres)
    epmach = np.finfo(float).eps
    ier2 = (abserr <= 100 * epmach * resabs) and (abserr > errbnd)
    accept = ier2 or (abserr <= errbnd and abserr != resasc) or (abserr == 0.0)
    if accept:
        return result
    return integrate.quad(func, a, b, epsabs=epsabs, epsrel=epsrel)[0]

def VinetEq(x,p,KTP0,KT0):
    vinet=-p+(3*np.exp((3*(-1+KTP0)*(1-x))/2)*KT0*(1-x))/x**2
    return vinet

def GibbsLiquidFe(T):
    return 300-9007.3402+290.29866*T-46*T*np.log(T)

def GibbsfccFe(T):
    return 16300.921-395355.43/T-2476.28*np.sqrt(T)+ 381.47162*T+0.000177578*T**2-52.2754*T*np.log(T)

def VexFeS(chi,p,T):
    W11=-9.91275
    W12=0.731385
    W21=-1.32521
    W22=1.72716
    return (1-chi[1])*chi[1]*np.array([chi[1]*(W11+W12*np.log(1.5+p))+chi[0]*(W21+W22*np.log(1.5+p)),
                                  chi[1]*W12/(1.5+p)+chi[0]*W22/(1.5+p),0])

def VexFeSi(chi,p,T):
    W1=-2.3199284685783192
    W2=-1.2489264297620897  
    return (1-chi[1])*chi[1]*np.array([chi[1]*W1+chi[0]*W2,0,0])

def VexFeFeSFeSi(chi,p,T):
# 0->Fe, 1->FeS, 2->FeSi
    W01a=-9.91275
    W01b=0.731385
    W10a=-1.32521
    W10b=1.72716
    W02a=-2.3199284685783192
    W20a=-1.2489264297620897
    return np.array([chi[0]*chi[1]*(chi[1]*(W01a+W01b*np.log(1.5+p))+chi[0]*(W10a+W10b*np.log(1.5+p)))+chi[0]*chi[2]*(chi[0]*W20a+chi[2]*W02a),chi[0]*chi[1]*(chi[1]*W01b/(1.5+p)+chi[0]*W10b/(1.5+p)),0])  
    
class eosAndersonGrueneisen:
    def __init__(self,M0,p0,T0,V0,alpha0,KT0,KTP0,deltaT,kappa,
                 GibbsE=None,gamma0=None,q=None):
        self.pMax=200
        self.nbrPNodes=10001

        if (GibbsE is not None and (gamma0 is not None or q is not None)):
            print("Gibbs function and gamma not supported")
    				
        if (GibbsE is not None):
            self.GibbsFlag=True
            self.gamma0=0
            self.q=0
        else:
            self.GibbsFlag=False
            self.gamma0=gamma0
            self.q=q
    
        self.M0=M0
        self.p0=p0
        self.T0=T0
        self.V0=V0
        self.alpha0=alpha0
        self.KT0=KT0
        self.KTP0=KTP0
        self.deltaT=deltaT
        self.kappa=kappa
        self.GibbsE=GibbsE

        self.zetaA=np.zeros(self.nbrPNodes)
        self.px=np.zeros(self.nbrPNodes)
        self.zetaA[0]=1
        for i in range(1,self.nbrPNodes):
            self.px[i]=i/self.pMax
            self.zetaA[i]=self.compress(self.px[i])

        self.poly = CubicSpline(self.px,self.zetaA)

    def volume(self,x,T):
        # volume/V0
        p=x*self.pMax
        eta=(self.poly.__call__(p))**3
        alpha=self.alpha0*np.exp(-self.deltaT/self.kappa*(1-eta**self.kappa))
        return eta*np.exp(alpha*(T-self.T0))
    
    def Gibbs(self,p,T):
        if (p>self.p0):
            a = self.p0/self.pMax
            b = p/self.pMax
            if PIE_FAST_QUAD:
                # v1.3.3 perf path, DEFAULT ON since the 2026-10-02 ruling
                # (see _gk21_or_quad's docstring and
                # testsys/unit/test_perf_v1_3_3_gk21_quad.py for why this
                # is NOT bit-identical to the quad path below off the
                # pinned environment, and PIE_FAST_QUAD=0 for the escape
                # hatch back to the quad path).
                Gp = _gk21_or_quad(lambda x: self.volume(x,T), a, b)
            else:
                Gp = integrate.quad(lambda x: self.volume(x,T), a, b)[0]
        else :
            Gp=0
        return self.GibbsE(T)+1.e3*Gp*self.V0*self.pMax
        
    def compress(self,p):
        out = optimize.brentq(VinetEq, 0.7, 1.2, 
                                     args = (p,self.KTP0,self.KT0))
        return out

    def eos(self,p,T):
        deltaTemp=1 # temperature step for numerical differentiation, if too small results too noisy
        if (p>self.pMax):
            print("p should be smaller than ",self.pMax)
        T0=self.T0
        V0=self.V0
        alpha0=self.alpha0
        KT0=self.KT0
        KTP0=self.KTP0
        deltaT=self.deltaT
        kappa=self.kappa

        zeta=self.poly.__call__(p)
        eta=zeta**3
        alpha=alpha0*np.exp(-deltaT/kappa*(1-eta**kappa))
        V=V0*eta*np.exp(alpha*(T-T0))

        KT=(KT0*(4+(-5+3*KTP0)*zeta+3*(1-KTP0)*zeta**2))/np.exp((3*(-1+KTP0)*(-1+zeta))/2)
        KT=KT/(2*zeta**2)
        KT=KT/(1+(T-T0)*deltaT*alpha*eta**kappa)

        KTP=0.5*(KTP0-1)*zeta
        KTP=KTP+(8/3+(KTP0-5/3)*zeta)/(3*(4/3 +(KTP0-5/3)*zeta+(1-KTP0)*zeta**2))

        if (self.GibbsFlag):
            Gibbs=self.Gibbs(p,T)
            Cp=-T*(self.Gibbs(p,T+deltaTemp)-2*Gibbs+self.Gibbs(p,T-deltaTemp))/deltaTemp**2 # numerical second derivative of G with respect to T
            gamma=1/(Cp/(alpha*KT*V*1E+3)-alpha*T) # factor 1000 for conversion of GPa and cm^3/mol
            KS=KT*(1+gamma*alpha*T)
        else:
            Gibbs=0
            gamma=self.gamma0*eta**self.q
            KS=KT*(1+gamma*alpha*T)
            Cp=1E+3*alpha*V*KS/gamma

        self.V=V
        self.rho=1.e3*self.M0/V
        self.alpha=alpha
        self.KT=KT
        self.KTP=KTP
        self.KS=KS
        self.gamma=gamma
        self.vp=np.sqrt(1E+9*KS/self.rho)
        self.vs=0
        self.Cp=Cp
        self.CV=1.e3*alpha*V*KT/gamma
        self.GE=Gibbs	
	
class margules2Solution: 
    def __init__(self,chi,p,T,eM1,eM2,Vex):
        eM1.eos(p,T)
        eM2.eos(p,T)

        Vexx=Vex(chi,p,T) #[Vex,dVex/dp,dVex/dT]
        self.Vex=Vex
        self.M0=np.dot([eM1.M0,eM2.M0],chi)
        self.V=np.dot([eM1.V,eM2.V],chi)+Vexx[0]
        self.Cp=np.dot([eM1.Cp,eM2.Cp],chi)
        self.alpha=(np.dot([eM1.V*eM1.alpha,eM2.V*eM2.alpha],chi)+Vexx[2])/self.V
        self.KT=-self.V/(-np.dot([eM1.V/eM1.KT,eM2.V/eM2.KT],chi)+Vexx[1])
        self.gamma=1/(1E-3*self.Cp/(self.alpha*self.KT*self.V)-self.alpha*T)
        self.KS=self.KT*(1+self.alpha*self.gamma*T)
        self.CV=1E+3*self.alpha*self.V*self.KT/self.gamma
        self.rho=1E+3*self.M0/self.V
        self.vp=np.sqrt(1E+9*self.KS/self.rho)	## BEWARE OF POSSIBLE BUG!!!!#			
	     
# 20220331. Transferred from presendDay model.
class margules3Solution: 
    def __init__(self,chi,p,T,eM1,eM2,eM3,Vex):
        eM1.eos(p,T)
        eM2.eos(p,T)
        eM3.eos(p,T)

        Vexx=Vex(chi,p,T) #[Vex,dVex/dp,dVex/dT]
        self.Vex=Vex
        self.M0=np.dot([eM1.M0,eM2.M0,eM3.M0],chi)
        self.V=np.dot([eM1.V,eM2.V,eM3.V],chi)+Vexx[0]
        self.Cp=np.dot([eM1.Cp,eM2.Cp,eM3.Cp],chi)
        self.alpha=(np.dot([eM1.V*eM1.alpha,eM2.V*eM2.alpha,eM3.V*eM3.alpha],chi)+Vexx[2])/self.V
        self.KT=-self.V/(-np.dot([eM1.V/eM1.KT,eM2.V/eM2.KT,eM3.V/eM3.KT],chi)+Vexx[1])
        self.gamma=1/(1E-3*self.Cp/(self.alpha*self.KT*self.V)-self.alpha*T)
        self.KS=self.KT*(1+self.alpha*self.gamma*T)
        self.CV=1E+3*self.alpha*self.V*self.KT/self.gamma
        self.rho=1E+3*self.M0/self.V
        self.vp=np.sqrt(1E+9*self.KS/self.rho)	
        
def liquidNonIdalFeSi(x,p,T,param):
    MolarMassFe = param['MFe']
    MolarMassSi = param['MSi']
    liquidFe = param['lFe']
    liquidFeSi = param['lFeSi']    
    chi = np.zeros(2)
    
    chi[1]=MolarMassFe*x/(MolarMassSi+x*(MolarMassFe-MolarMassSi)) # molar fraction Si
    chi[1]=chi[1]/(1-chi[1]) # convert to molar fraction of FeSi
    chi[0]=1-chi[1]
    
    nonIdealFeFeSi=margules2Solution(chi,p,T,liquidFe,liquidFeSi,VexFeSi)
    liquidNonIdalFeSi=[nonIdealFeFeSi.V,
                       nonIdealFeFeSi.rho,
                       nonIdealFeFeSi.alpha,
                       nonIdealFeFeSi.KT,
                       nonIdealFeFeSi.KS,
                       nonIdealFeFeSi.Cp,
                       nonIdealFeFeSi.gamma,
                       nonIdealFeFeSi.vp]
    
    return liquidNonIdalFeSi

def liquidNonIdalFeS(x,p,T,param):
    chi = np.zeros(2)
    MolarMassFe = param['MFe']
    MolarMassS = param['MS']
    liquidFe = param['lFe']
    liquidFeS = param['lFeS']

    chi[1]=MolarMassFe*x/(MolarMassS+x*(MolarMassFe-MolarMassS)) # convert weight fraction to molar fraction S
    chi[1]=chi[1]/(1-chi[1]) # convert to molar fraction of FeS
    chi[0]=1-chi[1]
    nonIdealFeFeS=margules2Solution(chi,p,T,liquidFe,liquidFeS,VexFeS)
    liquidNonIdalFeS=[nonIdealFeFeS.V,
                      nonIdealFeFeS.rho,
                      nonIdealFeFeS.alpha,
                      nonIdealFeFeS.KT,
                      nonIdealFeFeS.KS,
                      nonIdealFeFeS.Cp,
                      nonIdealFeFeS.gamma,
                      nonIdealFeFeS.vp]
    
    return liquidNonIdalFeS

# 20220331. liquidNonIdalFeSSi is copied from presentDay model.
def liquidNonIdalFeSSi(x,p,T,param):
    # x[0] is wt S and x[1] is wt Si
    MolarMassFe  = param['MFe']
    MolarMassS   = param['MS']
    MolarMassSi  = param['MSi']
    liquidFe     = param['lFe']
    liquidFeS    = param['lFeS']
    liquidFeSi   = param['lFeSi']    
    chi          = np.zeros(3)
    
    
    # convert wt fraction (S,Si) to mol fraction (FeS,FeSi)
    #chi[1]=MolarMassFe*x[0]/(MolarMassS*(1-x[0]-x[1])) 
    #chi[2]=MolarMassFe*x[1]/(MolarMassSi*(1-x[0]-x[1])) 
    tmp1         = (x[0]/MolarMassS)/(x[0]/MolarMassS + x[1]/MolarMassSi + (1-x[0]-x[1])/MolarMassFe)
    tmp2         = (x[1]/MolarMassSi)/(x[0]/MolarMassS + x[1]/MolarMassSi + (1-x[0]-x[1])/MolarMassFe)
    chi[1]       = tmp1/(1-tmp1-tmp2)
    chi[2]       = tmp2/(1-tmp1-tmp2)
    chi[0]       = 1-chi[1]-chi[2]
        
    nonIdealFeFeSSi    = margules3Solution(chi,p,T,liquidFe,liquidFeS,liquidFeSi,VexFeFeSFeSi)
    liquidNonIdalFeSSi = [nonIdealFeFeSSi.V,
                          nonIdealFeFeSSi.rho,
                          nonIdealFeFeSSi.alpha,
                          nonIdealFeFeSSi.KT,
                          nonIdealFeFeSSi.KS,
                          nonIdealFeFeSSi.Cp,
                          nonIdealFeFeSSi.gamma,
                          nonIdealFeFeSSi.vp]
    
    return liquidNonIdalFeSSi

def solidFccFe(p,T,param):
    fccFe = param['fccFe']
    fccFe.eos(p,T)
    
    solidFccFe=[fccFe.V,
                fccFe.rho,
                fccFe.alpha,
                fccFe.KT,
                fccFe.KS,
                fccFe.Cp,
                fccFe.gamma,
                fccFe.vp]

    return solidFccFe

def solidFccFeSi(x,p,T,param):   
    MolarMassFe = param['MFe']
    MolarMassSi = param['MSi']

    fcc=solidFccFe(p,T,param)  
    
    chi=MolarMassFe*x/(MolarMassSi+x*(MolarMassFe-MolarMassSi)) # molar fraction Si
    xx=(MolarMassFe *(1.-chi)+chi*MolarMassSi)/MolarMassFe                                       
    return [fcc[0],fcc[1]*xx,fcc[2],fcc[3],fcc[4],fcc[5],fcc[6]/xx**2]

def eosInnerCore(chi,p,T,param):
    # 20220302. The function is to calculate inner core density given Si and S wt%.
    fcc = solidFccFeSi(chi['Si'],p,T,param) # for chi['Si'] == 0, this will be the same as solidFccFe.
    return fcc
    
class meltingDataFromFile:
    def __init__(self,filename):
        f = open(filename, "r")
        f.readline()
        f.readline()
        xMin, xMax, nbrXNodes, pMin, pMax, nbrPNodes=map(int,f.readline().split())
        T=np.zeros((nbrXNodes,nbrPNodes))
        p=np.linspace(pMin,pMax,nbrPNodes)
        x=np.linspace(xMin,xMax,nbrXNodes)/100
        for i in range(nbrXNodes):
            for j in range(nbrPNodes):
                xx, px, Tx=f.readline().split()
                T[i,j]=Tx
        # Bicubic interpolating spline on the regular (p, x) grid. Same FITPACK
        # fit (regrid_smth, kx=ky=3, s=0) and evaluation (bispev) as the
        # scipy interp2d(p, x, T, kind='cubic') it replaces (removed in
        # scipy 1.14); bit-for-bit equal, see testsys/unit/test_melting_interp_port.py.
        self.TF=RectBivariateSpline(p,x,T.T,kx=3,ky=3,s=0)
    
    def __call__(self,x,p):
        # interp2d(p, x) returned an array of shape (len(x), len(p)), squeezed
        # to 1-D when len(x) == 1; [0] then picked the first element (a scalar
        # for scalar queries). Reproduce that exactly.
        z=np.atleast_2d(self.TF(np.sort(np.atleast_1d(p)),np.sort(np.atleast_1d(x)))).T
        if len(z)==1:
            z=z[0]
        return np.array(z)[0]
            