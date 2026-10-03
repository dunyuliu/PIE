#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Change logs:
-03/17/2022: Move CvC, debye3, cheval, Eth, gammaC, thetaC to misc.py.
-02/03/2022: Modified by dliu to include Fe-Si-S.

Created on Tue Sep  3 13:23:27 2019
@author: gregor
Modified by dliu since 03/31/2022.dliu.
"""

import numpy as np
import time
import scipy
import coreEos as eos
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import inv
#from scipy.constants import G
#from scipy.constants import R as RGas
from globalvar import (
    ErrorCode, chi_Si_icb, liquidus_eq,
    max_Si_Steinbruegge2020, max_Si_Edmund2022,
)
from libCore import (
    G, SolverError, write_solver_log, reorder_el,
    getCoreLiquidus, getpotvsr, get_mass_core,
    get_mass_norm, get_moi, get_ccc,
)
from solver import (
    odeRK4_snow, rhs_PTrhog_solid_snow, rhs_fluid_snow,
    simpsonDat, rhs_Pgz,
)

def shoot_mercmodel(v,ricb,rhocr,rh,param,scale):
    
    """ 
    THIS IS SIMILAR TO projects/mercury_interiormodels/shoot_mercmodel_snow.m
    except that we do not use ode45 solver.  Instead, solved by 4th order RK
    using an adaptation of odeRK4sysv (NMM).  This allows the freedom to also
    advance chi_li as a variable of the system.

    Shoots to find one solution from a set of initial conditions 
    specified in the vector v

    Here, the 5 unknowns are 
    1) P(r=0) 2) T(r=0) 3) rcmb  4) rhom 5) chi_li_icb

    The roots of the system are specified by 3 conditions:
        matching P, g at cmb, as well as the melting T at ICB.
        The success is measured in the 3-element vector f

    output: r= radial points of integration (non-dimensional)
         yy(:,1) = pressure vs radius (non-dimensional)
         yy(:,2) = g vs radius (non-dimensional)
         yy(:,3) = temperature vs radius (non-dimensional)
         yy(:,4) = adiabatic temperature vs radius (non-dimensional)
         yy(:,5) = density vs radius (non-dimensional)
         yy(:,6) = chi_li vs radius (non-dimensional)
         fout(1) = P at icb (dimensional)
         fout(2) = T at cmb (dimensional)
         fout(3) = Cm/C
         fout(4) = C/MR^2
         fout(5) = xi
         fout(6) = k2
         fout(7) = isnow  (0,1,2,3 = no, layers, deep snow, deep snow+layers)
         fout(8) = isnowcmb  (0,1 = snow at CMB (no,yes))
         fout(9) = chi_li_in (initial sulfur content in core)
         fout(10)= gradTa (adiabatic temp gradient at CMB)

     shoot from set of conditions at r=small
     """
    # Mercury parameters
    M         = param['GM']/G
    rm        = param['rm']
    rhomean   = 3*M/(4*np.pi*rm**3)

    # scales
    a         = scale['a']
    ga        = scale['ga']
    P         = scale['P']
    T         = scale['T']

    # limits of integration
    r0        = 0.0001/a
    rcmb      = v[2]
    rhom      = v[3]*rhomean

    # calculate Pcmb, gcmb
    rc        = rcmb*a
    rhd       = rh*a
    Pcmb,gcmb = getPgcmb_crust(rhom,rc,rhocr,rhd,param,scale)
    Pcmb      = Pcmb/P
    gcmb      = gcmb/ga
    CmC       = param['CmC']
    CMR2      = param['CMR2']

    # get gruneisan, bulk and density for P,T at r0 
    P1         = P*v[0]
    T1         = T*v[1]
    chi_li_icb = v[4]
    chi_icb    = reorder_el(v[4],chi_Si_icb,param)
    rho        = eos.eosInnerCore(chi_icb,P1/1E+9,T1,param)[1] # rho at inner core boundary?
    #boundary values at r0 for in://csegweb.cgd.ucar.edu/experiments/public/?ref=navtegration
    gr0        = 4*np.pi*G*rho*(r0*a)/(3*ga)
    # initial P, gr0, T to integrate from core to inner core boundary.
    y0         = [v[0], gr0, v[1]]

    #Shoot In solid inner core 
	# scipy.integrate.solve_ivp solves an initial value problem for a system of ODEs.
	# https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html.
	# It numerically integrates a system of ODEs given an initial value.
	# Integrate from center of the planet to icb. r0 is essentially zero.
	# Default solver is RK45. LSODA is Adams/BDF with automatic stiffness detection and switching.
	
	# Given light element concentrations at icb, chi_icb, and inner core boundary radius, ricb, and initial P, gr0, T at the core center, try to find solution dy/dr for each rs.
    sol       = scipy.integrate.solve_ivp(lambda t,y: rhs_PTrhog_solid_snow(chi_icb, t, y, ricb, scale, param),
                                            [r0, ricb], y0, method='LSODA',
                                            rtol=5e-5)
    # return radius array to rs.
    # return solution at each rs to ys.
    rs        = sol.t # I think the discretization of rs is automatically determined from solve_ivp.
    ys        = sol.y
    ns        = len(rs)
    #print('rs', rs)
    #print('ys', ys)
    #print('ns', ns)

    # calculate melting temperature at ICB
    P1        = P*ys[0,-1] # pressure at ICB, ys[0,last dim].
    Tmicb     = getCoreLiquidus(chi_icb['S'],chi_icb['Si'],P1,param,0)/T # changed first two variables from chi_li_icb and chi_Si_icb
    # boundary values for FOC integration: 
    # continuity of P, g, and T=Tm
    yicb      = [ys[0,-1],ys[1,-1],Tmicb,Tmicb]
    #print('Finish solving the solid inner core ... ...')

    # Shoot In Fluid core
    nc        = 51 # discretize the liquid core into nc grids. 
    h         = (rcmb-ricb)/(nc-1) # grid size
    
    rc,yc,rhof,chi_li, err = odeRK4_snow('rhs_fluid_snow',ricb,rcmb,h,yicb,v[4],scale,param)
    # Restore the err flag libCore.getchi_li_grun sets (chi_li went
    # negative mid-shoot) instead of discarding it into a hard-coded
    # err0=False (docs/audits/AUDIT_2026-09-29_buglist.md B3;
    # src/libCore.py:142-144 sets it, this used to throw it away).
    err0 = bool(np.any(err))
    
    # rc is radius array from ricb -> rcmb with grid size h.
    # Calculate moments of inertia:
    # First build polynomials of density
    rhos      = np.empty(ns)
    chi_icb   = reorder_el(chi_li[0],chi_Si_icb, param) # get light element concentration at inner core boundary.
    for i in range(0,ns):
        rhos[i]   = eos.eosInnerCore(chi_icb,P*ys[0,i]/1E+9, T*ys[2,i], param)[1]/rhomean
    sols      = np.polyfit(rs,rhos,3)

    for i in range(0,nc):
        rhof[i]   = rhof[i]/rhomean
    solf      = np.polyfit(rc,rhof,3)
    
    # ... then multiply by r4 and integrate
    rhor4       = np.convolve(sols,[1,0,0,0,0])
    bigIo       = np.polyval(np.polyint(rhor4),ricb)
    rhor4       = np.convolve(solf,[1,0,0,0,0])
    bigIo       = bigIo + np.polyval(np.polyint(rhor4),rcmb)\
                        -np.polyval(np.polyint(rhor4),ricb)

    bigCm       = 0.2*rhocr*(1-rh**5)/rhomean + 0.2*rhom*(rh**5-rcmb**5)/rhomean
    bigIo       = bigIo + bigCm   # To get dimensional moment of inertia, * 8pi/3*rhomean*a^5
    #CmC=bigCm/bigIo # Cm/C 
    #CMR2=2*bigIo # C/MR^2 
    CmCtry      = bigCm/bigIo #Cm/C 
    CMR2try     = 2*bigIo #C/MR^2 

    # calculate initial sulfur
    chisrc2     = chi_li*rc**2
    chi_li_in   = 3/(rcmb**3)*simpsonDat(rc,chisrc2) # light element inside the fluid outer core.
    #print('chi_li', chi_li)
    #print('chi_li_in', chi_li_in)
    #############################################
    # calculate volumetric average of sulfur
    chis_oc = 4*np.pi*chi_li*(rhof*rhomean)*(rc*a)**2
    chi_li_in_v = simpsonDat(rc*a,chis_oc) / ((4/3)*np.pi*((rcmb*a)**3))
    print('new volumetric average of S: '+str(chi_li_in_v))
    #############################################
    # calculate mass average of sulfur
    chisrf = 4*np.pi*(rhof*rhomean)*chi_li*(rc*a)**2
    chismass = simpsonDat(rc*a, chisrf)
    mass_core = get_mass_core(np.concatenate((rs*a,rc*a)),np.concatenate((rhos*rhomean,rhof*rhomean)))
    chisbulk=chismass/mass_core
    print(ricb*a,chi_Si_icb)
    print('Volumetric Average of S: '+str(chi_li_in))
    print('Bulk Average of S: '+str(chisbulk))
    print('Mass of Core: '+str(mass_core))

    # Compute snow state. 
    # 0: no iron snow.
    # 1: snow layers.
    # 2: deep snow.
    # 3: deep snow + layers.
    isnow = 0  # snow index: default is no snow
    if ((chi_li[-1]-chi_li_icb) > 1e-10):
        isnow   = 1
        # get dimensional P and T at second point in FOC
        # deep snow is defined when the adiabat temp follows the liquidus directly above ICB.
        # because the temp is always equal to melting temp at ICB, should change 
        # i from 0 to 1. Now, isnow = 1, 2, 3 are properly classified. 
        i       = 1 
        T1      = T*yc[i,2]
        P1      = P*yc[i,0]
        chi_icb = reorder_el(chi_li[i],chi_Si_icb, param)             
        Tm      = getCoreLiquidus(chi_icb['S'], chi_icb['Si'], P1,param,0)  # get Tliquidus
        if abs(T1-Tm)<1e-8: # if adiabat temperature = Liquidus 
            isnow = 2

    isnowcmb=0;  # snow at cmb index: default no
    if isnow==1 or isnow==2:
        i       = -1
        chi_icb = reorder_el(chi_li[i],chi_Si_icb,param)
        # get dimensional P and T
        T1      = T*yc[i,2]
        P1      = P*yc[i,0]
        Tm      = getCoreLiquidus(chi_icb['S'],chi_icb['Si'], P1,param,0)  # get Tliquidus

        if abs(T1-Tm)<1e-6:  #if adiabat temperature = Liquidus
            isnowcmb = 1

    # Calculate k2_h and xi_h
  
    # avg inner core, outer core densities
    #rhor2=np.convolve(sols,[1,0,0])
 
    # Calculate k2 and xi
    rhoml       = rhom/rhomean

    # getk2 can raise IndexError (ricb=10 m => nrs=0 makes its fluid
    # loop wrap k+nrs-1 to -1 at k=0, reading the CMB end / g[399],
    # docs/audits/AUDIT_2026-09-29_buglist.md B5 -- the index math
    # itself is item 17's scope, NOT fixed here) or propagate a
    # SolverError from getpotvsr's SuperLU singular-matrix guard
    # (libCore.py). Both used to crash the whole process uncaught
    # (item 16); caught here and turned into a recorded, per-radius
    # SolverError instead.
    try:
        k2,xi   = getk2(ricb,rcmb,rhoml,sols,solf,param,scale)
    except SolverError:
        raise
    except (IndexError, ValueError, RuntimeError) as e:
        raise SolverError(
            ErrorCode.NONFINITE_SHOOT,
            'getk2 failed: %r' % (e,),
            context={'exception': repr(e), 'ricb': ricb, 'rcmb': rcmb},
        ) from e
    if not (np.isfinite(k2) and np.isfinite(xi)):
        raise SolverError(
            ErrorCode.NONFINITE_SHOOT,
            'getk2 returned non-finite k2/xi',
            context={'k2': k2, 'xi': xi, 'ricb': ricb, 'rcmb': rcmb},
        )

        
    # adiabatic temp gradient at CMB
    gradTa      = T/a*(yc[nc-1,3]-yc[nc-2,3])/(rc[nc-1]-rc[nc-2])
    fout        = [P*ys[0,-1],T*yc[nc-1,2],isnow,isnowcmb,chi_li_in,gradTa,chisbulk]

    # include the (1+xi) factor on Cm/C
    CmCtry      = CmCtry*(1+xi)
    
    # function to minimize (roots)
    f           = [yc[-1,0]-Pcmb,  # match P at cmb
                   yc[-1,1]-gcmb,  # match g at cmb
                   ys[2,-1]-Tmicb, # match Tm at icb
                   CmCtry-CmC,
                   CMR2try-CMR2]

    # concatenate solution
    r           = np.concatenate((rs,rc))
    ytemp       = np.vstack((ys,ys[2]))
    y           = np.hstack((ytemp,np.transpose(yc)))
    rho         = np.concatenate((rhos,rhof))
    chi         = np.concatenate((np.zeros(ns),chi_li))
    if param['li_el']=='Si': 
        chi[0:ns] = chi_li[0]
    yy          = np.vstack((y[0],y[1],y[2],y[3],rho,chi))
    return f, r, yy, fout, err0

last_solve_info = {}   # summary of the most recent mynewtonSys call: status, n_iterations, normf_last
                       # (read by src/driverp.py for the csv columns newton_iters / resid_norm)
ALPHA_MIN   = 1.e-3    # line search: smallest step fraction tried before giving up (10 halvings)
GROWTH_MAX  = 100.0    # line search: reject a trial whose |f| grows by more than this factor
COND_MAX    = 1.e12    # robust singular-Jacobian test replacing the exact det(J)==0 float compare


def mercmodel_trial(x, args):
    """Residual and diagnostics at a trial iterate for the Mercury model:
    returns (f, fout) from shoot_mercmodel. Used by mynewtonSys's line
    search; a SolverError raised by the shoot is passed through to the
    caller (mynewtonSys treats it as a rejected trial unless it is the
    by-design SI_ABOVE_LIQUIDUS_MAX stop)."""
    ricb, rhocr, rh, param, scale = args
    f, r, yy, fout, err = shoot_mercmodel(x, ricb, rhocr, rh, param, scale)
    return f, fout


def mercmodel_box(x, f, fout, args):
    """Admissible-box test for a trial iterate of the Mercury model.

    Returns (ok, error_code, detail). A trial is rejected when
      * f (or fout) is non-finite                       -> NONFINITE_SHOOT
      * rcmb <= ricb                                      -> RICB_GE_RCMB
      * chi_li_icb above the eutectic at the trial's own P_icb (S, S+Si:
        Dumberry & Rivoldini 2015 eq. 28, the same bound libCore.
        getchi_li_grun clamps to) or above the liquidus table's Si max
        (Si)                                              -> CHI_OUTSIDE_ADMISSIBLE_BOX
      * chi_li_icb below CHI_MIN (disabled by default, see CHI_MIN)

    Why there is no lower bound at 0: 103,243 of the 474,075 converged rows
    in the published v1.0.5 dataset (21.8%) have a negative chi_li_icb
    (mostly -0.001 to -0.003, down to about -0.045 for Si-only at low
    CMR2; recorded as error_code 4 since v1.2.0) and the Newton paths that
    produced them shoot finitely. A lower bound would reject alpha=1 on
    those paths and break the v1.2.0 identity invariant
    (docs/notes/solver_v1.3.0.md). What actually killed the published
    sweeps was an overshoot to chi ~ -0.06 (S) or above the Si max (Si)
    that makes the fluid-core RK4 return NaN or zeroes a Jacobian column;
    the non-finite test and the upper bound catch those.
    """
    ricb, rhocr, rh, param, scale = args
    if not (np.all(np.isfinite(f)) and np.all(np.isfinite(fout))):
        return False, ErrorCode.NONFINITE_SHOOT, 'non-finite residual at trial iterate'
    rcmb = x[2]
    if rcmb <= ricb:
        return False, ErrorCode.RICB_GE_RCMB, 'trial rcmb=%g <= ricb=%g (nd)' % (rcmb, ricb)
    chi = x[4]
    if param['li_el'] == 'Si':
        chi_max = max_Si_Steinbruegge2020 if liquidus_eq == 'Steinbruegge' else max_Si_Edmund2022
    else:
        Picb = fout[0]                      # dimensional P at the ICB of the trial
        chi_max = 0.11 + 0.187*np.exp(-0.065*Picb*1e-9)
    if chi > chi_max:
        return False, ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX, 'trial chi_li_icb=%g > bound %g' % (chi, chi_max)
    if CHI_MIN is not None and chi < CHI_MIN:
        return False, ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX, 'trial chi_li_icb=%g < %g' % (chi, CHI_MIN)
    return True, None, ''


# Lower bound on chi_li_icb for a TRIAL iterate. None = no explicit lower
# bound (a trial with chi so negative that the fluid-core EOS/liquidus root
# returns NaN is still rejected by the non-finite test above). Measured
# reason (docs/notes/solver_v1.3.0.md sec. 1.1): v1.2.0 converged -- and the
# published v1.0.5 dataset contains -- rows with chi_li_icb down to about
# -0.045 (Si-only, low CMR2), and converging paths whose intermediate
# iterates dip below -0.01; a bound of -0.01 broke the v1.2.0 identity on
# 2 of 6 sampled converging sweeps and rejected 24 converged Si rows.
# Negative converged rows keep their error_code 4 (err flag /
# (chi_li<0).any() in driverp.py).
CHI_MIN = None


def mynewtonSys(Jfun,x0,varargin,
                xtol=5e-5,ftol=5e-5,maxit=15,verbose=False,
                log_path=None,log_context=None,
                line_search=True,trial_fun=None,box_fun=None,
                alpha_min=None,growth_max=None,cond_max=None):
    """
     newtonSys  Newton's method for systems of nonlinear equations.

     Synopsis:  x = newtonSys(Jfun,x0)
                x = newtonSys(Jfun,x0,xtol)
                x = newtonSys(Jfun,x0,xtol,ftol)
                x = newtonSys(Jfun,x0,xtol,ftol,maxit,verbose)

     Input:  Jfun = (string) name of the function that returns matrix J and vector f
             x0   = initial guess at solution vector, x
             xtol = (optional) tolerance on norm(dx).  Default: xtol=5e-5
             ftol = (optional) tolerance on norm(f).   Default: ftol=5e-5
             verbose = (optional) flag.  Default: verbose=0, no printing.
             varargin = arguments passed through to Jfun (and to the
                        Mercury trial/box functions)

     Output:  x = solution vector, returned after k iterations once the
                  tolerances are met. On failure a SolverError is raised
                  (never sys.exit; PATHWAY_FORWARD.md items 16/17).

    Newton step (v1.3.0, item 17): the direction is unchanged,
    dx = J^-1 f. The step length alpha starts at 1 and is halved until the
    trial x - alpha*dx is accepted:

      * accepted immediately, before any trial evaluation, if the v1.2.0
        convergence test (|f| < ftol or |dx| < xtol, evaluated at the
        current iterate exactly as before) is met -- so a converging final
        step is returned bit-identically to v1.2.0;
      * otherwise the trial is evaluated with trial_fun and rejected if
        box_fun says it is outside the admissible box (Mercury model:
        non-finite residual, rcmb <= ricb, chi_li_icb above the eutectic /
        Si max, see mercmodel_box), if trial_fun
        raised a SolverError, or if |f_trial| > growth_max * |f|.

    Invariant (enforced by testsys/integration/test_v1_2_0_invariant.py):
    on every path where v1.2.0 converged, alpha=1 passes on every
    iteration, so the iterates are bit-identical to v1.2.0. An Armijo
    sufficient-decrease test was measured and NOT adopted: on 1841
    v1.2.0-converged radii (108 published sweeps) 48 of 3553 steps
    (1.4%, on 32 radii) increase |f| -- by up to 18.6x -- and those paths
    converge anyway; Armijo would have altered them (docs/notes/
    solver_v1.3.0.md). growth_max=100 sits 5x above the largest growth
    observed on a converging path.

    line_search=False restores the v1.2.0 step exactly (x = x - dx, no
    trial evaluation). When Jfun == 'J_mercmodel' and trial_fun/box_fun
    are not given, mercmodel_trial/mercmodel_box are used; for any other
    Jfun without a trial_fun (the toy Jacobians in testsys/unit) no line
    search is possible and the step is the v1.2.0 one.

    Singular Jacobian: the exact float test det(J)==0 is replaced by
    cond(J) > cond_max (default COND_MAX=1e12; a zero FD column gives
    cond=inf) or a LinAlgError from the inverse -> SINGULAR_JACOBIAN.
    cond(J) on converging Mercury paths is <= ~1e7.

    When alpha falls below alpha_min (default ALPHA_MIN=1e-3, i.e. 10
    halvings) the solve fails with the error code of the last rejection
    (CHI_OUTSIDE_ADMISSIBLE_BOX, RICB_GE_RCMB or NONFINITE_SHOOT). A
    by-design SI_ABOVE_LIQUIDUS_MAX raised inside a trial is re-raised
    as-is.

    log_path/log_context: when log_path is given, one JSON record
    (iterate history incl. alpha and cond(J), final status) is appended
    via libCore.write_solver_log -- see src/globalvar.py's
    pSolverLogFileName and item 15.
    """

    xeps = xtol
    feps = ftol #   %  Smallest tols are 5*eps
    alpha_min  = ALPHA_MIN  if alpha_min  is None else alpha_min
    growth_max = GROWTH_MAX if growth_max is None else growth_max
    cond_max   = COND_MAX   if cond_max   is None else cond_max

    if verbose:
        print('\nNewton iterations\n  k     norm(f)      norm(dx)    alpha    time(s)\n')

    if Jfun == 'J_mercmodel_nosic': x0.pop(1)
    if Jfun == 'J_mercmodel' and trial_fun is None and box_fun is None:
        trial_fun = lambda x: mercmodel_trial(x, varargin)
        box_fun   = lambda x, f, fout: mercmodel_box(x, f, fout, varargin)
    do_ls = bool(line_search) and trial_fun is not None
    x = x0
    k = 0        #  Initial guess and current number of iterations
    history = []

    def _flush_log(status):
        last_solve_info.clear()
        last_solve_info.update({'status': int(status), 'n_iterations': k,
                                'normf_last': history[-1]['normf'] if history else float('nan'),
                                'normdx_last': (history[-1]['normdx'] if history and history[-1]['normdx'] is not None else float('nan'))})
        if log_path is None:
            return
        record = {'kind': 'newton_solve', 'Jfun': Jfun,
                  'status': int(status), 'status_name': ErrorCode(status).name,
                  'n_iterations': k, 'history': history,
                  'line_search': do_ls}
        if log_context:
            record.update(log_context)
        write_solver_log(log_path, record)

    def _fail(code, msg, **ctx):
        _flush_log(code)
        ctx.update({'k': k, 'v': np.asarray(x).tolist(), 'newton_history': history})
        raise SolverError(code, msg, context=ctx)

    while k <= maxit:
      start = time.time()
      k = k + 1
      try:
          J,f = eval(Jfun)(x,varargin)   #   Returns Jacobian matrix and f vector
      except SolverError as e:
          e.context.setdefault('newton_history', history)
          e.context.setdefault('newton_iterations', k)
          _flush_log(e.error_code)
          raise
      J = np.asarray(J, dtype=float); f = np.asarray(f, dtype=float)
      normf = float(np.linalg.norm(f))
      if not np.all(np.isfinite(J)):
          condJ = float('inf'); detJ = float('nan')
      else:
          condJ = float(np.linalg.cond(J)); detJ = float(np.linalg.det(J))   # detJ kept for the log schema
      if not np.isfinite(condJ) or condJ > cond_max:
          history.append({'k': k, 'v': np.asarray(x).tolist(), 'normf': normf,
                          'normdx': None, 'detJ': detJ, 'condJ': condJ, 'alpha': None})
          _fail(ErrorCode.SINGULAR_JACOBIAN,
                'Singular Jacobian at Newton iteration %d (cond(J)=%g > %g)' % (k, condJ, cond_max),
                condJ=condJ)
      try:
          # v1.3.2 perf fix (docs/notes/perf_v1.3.2.md): same anti-pattern
          # as getpotvsr's old inv(A)*rhs -- inv(J)@f formed J's full
          # inverse just to multiply it once by f. np.linalg.solve(J, f)
          # solves J dx = f directly, same dx to roundoff, J unchanged.
          dx = np.linalg.solve(J,f)
      except np.linalg.LinAlgError as e:
          history.append({'k': k, 'v': np.asarray(x).tolist(), 'normf': normf,
                          'normdx': None, 'detJ': detJ, 'condJ': condJ, 'alpha': None})
          _fail(ErrorCode.SINGULAR_JACOBIAN,
                'Numerically singular J at Newton iteration %d (%r)' % (k, e), condJ=condJ)
      normdx = float(np.linalg.norm(dx))
      converged_now = (normf < feps) or (normdx < xeps)

      alpha = 1.0
      n_rejected = 0
      rejections = []      # (alpha, error name, detail, trial iterate) for every rejected trial
      if do_ls and not converged_now:
          while True:
              xt = x - alpha*dx
              ok, code, detail = True, None, ''
              try:
                  ft, fout_t = trial_fun(xt)
                  ft = np.asarray(ft, dtype=float)
                  ok, code, detail = box_fun(xt, ft, fout_t)
                  if ok and np.linalg.norm(ft) > growth_max*normf:
                      ok, code, detail = False, ErrorCode.NONFINITE_SHOOT, \
                          '|f| grew %gx > growth_max=%g' % (np.linalg.norm(ft)/normf if normf else float('inf'), growth_max)
              except SolverError as e:
                  if e.error_code == ErrorCode.SI_ABOVE_LIQUIDUS_MAX:
                      _flush_log(e.error_code)
                      raise
                  ok, code, detail = False, e.error_code, 'trial shoot raised %r' % (e,)
              if ok:
                  break
              n_rejected += 1
              rejections.append({'alpha': alpha, 'code': (ErrorCode(code).name if code is not None else None),
                                 'detail': detail, 'x_trial': np.asarray(xt).tolist()})
              alpha *= 0.5
              if alpha < alpha_min:
                  history.append({'k': k, 'v': np.asarray(x).tolist(), 'normf': normf,
                                  'normdx': normdx, 'detJ': detJ, 'condJ': condJ, 'alpha': alpha,
                                  'n_rejected': n_rejected, 'rejections': rejections})
                  _fail(code if code is not None else ErrorCode.NONFINITE_SHOOT,
                        'Line search failed at Newton iteration %d: no admissible step down to alpha=%g (%s)'
                        % (k, alpha, detail), alpha=alpha, n_rejected=n_rejected,
                        rejections=rejections, x_trial_last=np.asarray(xt).tolist())
      x = x - alpha*dx
      history.append({'k': k, 'v': np.asarray(x).tolist(), 'normf': normf,
                      'normdx': normdx, 'detJ': detJ, 'condJ': condJ, 'alpha': alpha,
                      'n_rejected': n_rejected, 'rejections': rejections})
      if verbose:
          end = time.time()
          print(k,normf,normdx,alpha,end-start)
      if converged_now:
          _flush_log(ErrorCode.CONVERGED)
          return x

    print('Solution not found within tolerance after_',k,'_iterations\n')
    _flush_log(ErrorCode.NEWTON_MAXIT)
    raise SolverError(ErrorCode.NEWTON_MAXIT,
                       'Newton solver did not converge within maxit=%d iterations' % maxit,
                       context={'maxit': maxit, 'newton_history': history})

def J_mercmodel(v,args):
    """
      computes the Jacobian and function evaluation for our 
      interior model system
    
     input vinit = variable vinit (5 element vector)
    
     output f = function evaluation (5 function)
            J = Jacobian matrix of derivatives
    """

    #initialize
    ricb,rhocr,rh,param,scale = args
    n=len(v)
    f = np.zeros(n) # f must be defined as a column vector
    f2 = np.zeros(n) # f must be defined as a column vector
    J = np.zeros((n,n))  
    
    # compute the function f, 
    f=shoot_mercmodel(v,ricb,rhocr,rh,param,scale)[0]

    eps=1.e-6
    for j in range(n):
        temp=v[j]
        h=eps*abs(temp)
        if (h==0):
            h=eps
        v[j]=temp+h
        h=v[j]-temp
        f2=shoot_mercmodel(v,ricb,rhocr,rh,param,scale)[0]
        v[j]=temp
        for i in range(n):
            J[i,j]=(f2[i]-f[i])/h

    return J,f

def getPgcmb_crust(rhom,rc,rhocr,rh,param,scale):
    """
    determines the Pressure and grav acc at cmb for a given choice of 
    mantle density (rhom), cmb radius (rcmb)
    crustal density (rhocr), crust-mantle boundary radius (rh)
    """
    # Mercury parameters
    GM=param['GM']
    M=GM/G
    rm = param['rm']

    # scales
    a=scale['a']
    P=scale['P']

    # mass of crust
    Mh=4*np.pi*rhocr*(rm**3-rh**3)/3
    # mass of mantle
    Mm=4*np.pi*rhom*(rh**3-rc**3)/3
    # mass of core
    Mcore=M-Mm-Mh
    # grav acc at CMB
    gcmb=Mcore*G/rc**2

    # Pressure at CMB: Shoot In crust + mantle 
    y0 = [0,1]
    sol = scipy.integrate.solve_ivp(lambda t,y: rhs_Pgz(t,y,rhocr,scale), [1,rh/a],
                                    y0, method='RK45')

    yh = sol.y[:,-1]

    sol = scipy.integrate.solve_ivp(lambda t,y: rhs_Pgz(t,y,rhom,scale), 
                                    [rh/a,rc/a],
                                    yh, method='RK45')

    Pcmb=P*sol.y[0,-1] # dimensional

    return Pcmb,gcmb





	



#### The k2 stuff ####
    
def getk2(rs,rf,rhoml,rhos,rhof,param,scale):
    """
    %
    % Calculates k2, xi = [(Bs-As) - (Bs'-As')]/ (Bmf -Amf)
    % for given density structure of mercury and c22
    %
    %
    """
    # Mercury parameters
    M=param['GM']/G
    rm = param['rm']
    rhomean = 3*M/(4*np.pi*rm**3)
    c22=param['c22']

    # scales
    a=scale['a']
    ga=scale['ga']

    bigGscale=ga/(rhomean*a)
    bigGnd=G/bigGscale

    # Define radial grid points
    nr=400
    nrs=int(round(nr*(rs/rf)))
    nrf=nr-nrs
    if nrs >= nr or rs >= rf:
        # ricb/rcmb >= 0.99875 puts the whole grid in the inner core (or the
        # inner core outside the core): the IndexError this used to raise in
        # the loops below is the RICB_GE_RCMB physical limit.
        raise SolverError(ErrorCode.RICB_GE_RCMB,
                          'getk2: ricb=%g >= rcmb=%g (nd) or grid fully inside the inner core (nrs=%d)' % (rs, rf, nrs),
                          context={'nrs': int(nrs), 'ricb': float(rs), 'rcmb': float(rf)})
    
    # np.zeros, not np.empty: every entry is assigned below, but with
    # nrs=0 the old code read g[-1] before it was set (see the k=0 branch
    # in the fluid loop) -- zeros make any remaining gap a deterministic
    # value that the finiteness check below can judge, never heap garbage.
    r = np.zeros(nr)
    rho = np.zeros(nr)
    g = np.zeros(nr)
    
    for k in range(nrs):
        r[k]=rs*(k+1)/nrs


    for k in range(nrf):
        r[k+nrs]=rs+(rf-rs)*k/nrf
    
    drf=(rf-rs)/nrf

    # Build density (rho) and gravitational acceleration (g)
    f4piG=4*np.pi*bigGnd/3

    #  in inner core (skipped entirely when nrs == 0: the core is then
    #  treated as fully fluid from the centre, see the k == 0 branch below)
    if nrs > 0:
        avgr=0.5*r[0]
        rho[0]=np.polyval(rhos, avgr)
        g[0]=f4piG*rho[0]*r[0]

    for k in range(1,nrs):
        avgr=0.5*(r[k]+r[k-1])
        rho[k]=np.polyval(rhos, avgr)
        g[k]= f4piG*rho[k]*(r[k]**3-r[k-1]**3)/r[k]**2 +  g[k-1]*(r[k-1]/r[k])**2
    
    #  in fluid core (this first-shell value is recomputed by the k=1 pass
    #  of the loop below; kept as in v1.0.5 so nrs >= 1 stays bit-identical)
    if nrs > 0:
        avgr=r[nrs]+0.5*drf
        rho[1+nrs]=np.polyval(rhof, avgr)
        g[1+nrs]=f4piG*rho[1+nrs]*(r[1+nrs]**3-r[nrs]**3)/r[1+nrs]**2\
                 +g[nrs]*(r[nrs]/r[1+nrs])**2

    for k in range(0,nrf):
        if k+nrs == 0:
            # nrs == 0: ricb is below the 400-point grid's resolution (the
            # 10-m first radius: round(400*ricb/rcmb) = 0), so the first
            # shell is [0, r[0]] and has no inner neighbour. The old code
            # indexed k+nrs-1 = -1 here, wrapping to the CMB end (r[399],
            # and the not-yet-set g[399]) -- bug B5 / PATHWAY_FORWARD.md
            # item 17. Use the centre as the inner boundary: r=0, g=0,
            # i.e. a fully fluid core from the centre with g(0) = 0 and no
            # inner-core term (owner decision 2026-09-30); BsAs below sums
            # over range(nrs) = nothing, so xi = 0 exactly.
            avgr=0.5*r[0]
            rho[0]=np.polyval(rhof, avgr)
            g[0]=f4piG*rho[0]*r[0]
            continue
        avgr=0.5*(r[k+nrs]+r[k+nrs-1])
        rho[k+nrs]=np.polyval(rhof, avgr)
        g[k+nrs]=f4piG*rho[k+nrs]*(r[k+nrs]**3-r[k+nrs-1]**3)/r[k+nrs]**2\
                 +g[k+nrs-1]*(r[k+nrs-1]/r[k+nrs])**2

    if not (np.all(np.isfinite(rho)) and np.all(np.isfinite(g)) and np.all(g[1:] > 0)):
        raise SolverError(ErrorCode.NONFINITE_SHOOT,
                          'getk2: non-finite or non-positive rho/g on the k2 grid',
                          context={'nonfinite_rho_count': int(np.sum(~np.isfinite(rho))),
                                   'nonfinite_g_count': int(np.sum(~np.isfinite(g))),
                                   'nonpositive_g_count': int(np.sum(g[1:] <= 0)),
                                   'nrs': int(nrs), 'ricb': float(rs), 'rcmb': float(rf)})

    # solution
    pot = getpotvsr(nr,bigGnd,r,rho,g)
    k2 = pot[-1]-1;
    
    # get ellipticity
    fell=1.0
    drhocmb = rho[-1]-rhoml
    ell = c22*10.0/ (rhoml*(1 + k2*rf**5)+ fell*(1+k2)*drhocmb*rf**5)
    # calculate Bs-As
    factrho=rhoml+fell*drhocmb
    BsAs=0

    for k in range(nrs):
        BsAs=BsAs+(4*np.pi/5)*bigGnd*rf*rf*(rho[k]-rho[k+1])*(r[k]**4)*pot[k]/g[k]

    BsAs=BsAs*(8*np.pi/15)*ell*factrho

    # calculate Bmf-Amf
    sum3=0
    for k in range(nrs,nr-1):
        sum3=sum3+(4*np.pi/5)*bigGnd*rf*rf*(rho[k]-rho[k+1])*(r[k]**4)*pot[k]/g[k]

    ffrho=rhoml + fell*drhocmb*rf**5
    BmAm=(8*np.pi/15)*ell*(ffrho+sum3*factrho)

    # calculate xi
    xi=BsAs/BmAm

    return k2,xi



