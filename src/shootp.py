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
from globalvar import *
from libCore import *
from solver import *

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

def mynewtonSys(Jfun,x0,varargin,
                xtol=5e-5,ftol=5e-5,maxit=15,verbose=False,
                log_path=None,log_context=None):
    """
     newtonSys  Newton's method for systems of nonlinear equations.
    
     Synopsis:  x = newtonSys(Jfun,x0)
                x = newtonSys(Jfun,x0,xtol)
                x = newtonSys(Jfun,x0,xtol,ftol)
                x = newtonSys(Jfun,x0,xtol,ftol,maxit,verbose)
                x = newtonSys(Jfun,x0,xtol,ftol,maxit,verbose,arg1,arg2,...)
    
     Input:  Jfun = (string) name of mfile that returns matrix J and vector f
             x0   = initial guess at solution vector, x
             xtol = (optional) tolerance on norm(dx).  Default: xtol=5e-5
             ftol = (optional) tolerance on norm(f).   Default: ftol=5e-5
    
             verbose = (optional) flag.  Default: verbose=0, no printing.
             arg1,arg2,... = (optional) optional arguments that are passed                   
             through to the mfile defined by the 'Jfun' argument
    
     Note:  Use [] to request default value of an optional input.  For example,
            x = newtonSys('JFun',x0,[],[],[],arg1,arg2) passes arg1 and arg2 to
            'JFun', while using the default values for xtol, ftol, and verbose
    
     Output:  x = solution vector;  x is returned after k iterations if
                  tolerances are met, or after maxit iterations if
                  tolerances are not met.

    Failure handling (PATHWAY_FORWARD.md items 15/16): a singular
    Jacobian (exact det(J)==0, or numerically singular in np.linalg.inv)
    or hitting maxit without meeting xtol/ftol used to call sys .exit(),
    killing the whole process (docs/audits/AUDIT_2026-09-29_buglist.md
    B1). Both now raise SolverError (a SystemExit subclass, so an
    uncaught call still stops as loudly as before) carrying an
    ErrorCode and the full per-iteration history (v, |f|, |dx|,
    det(J)); src/driverp.py catches it per radius instead of letting it
    reach the interpreter. This only changes what happens AFTER a
    failure is detected -- the Newton step itself (dx = J^-1 f, x = x -
    dx) is unchanged (that is item 17's scope, not this one's).

    log_path/log_context: when log_path is given, one JSON record
    (iterate history + final status) is appended to it via
    libCore.write_solver_log -- see src/globalvar.py's
    pSolverLogFileName and item 15. log_context is merged into that
    record as-is (e.g. {'ricb': ..., 'k_radius': ...} from the caller)
    so a log line can be tied back to which radius produced it. Both
    default to None (no logging), so every existing call site
    (testsys/unit/test_solver.py's toy Jacobians, the integration
    fixtures) is unaffected.
    """

    xeps = xtol
    feps = ftol #   %  Smallest tols are 5*eps

    if verbose:
        print('\nNewton iterations\n  k     norm(f)      norm(dx)    time(s)\n')

    if Jfun == 'J_mercmodel_nosic': x0.pop(1)
    x = x0
    k = 0        #  Initial guess and current number of iterations
    history = []

    def _flush_log(status):
        if log_path is None:
            return
        record = {'kind': 'newton_solve', 'Jfun': Jfun,
                  'status': int(status), 'status_name': ErrorCode(status).name,
                  'n_iterations': k, 'history': history}
        if log_context:
            record.update(log_context)
        write_solver_log(log_path, record)

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
      detJ = np.linalg.det(J)
      if detJ == 0:
        print('Zero Determinant of J. Exit ... ...')
        history.append({'k': k, 'v': np.asarray(x).tolist(),
                         'normf': float(np.linalg.norm(f)), 'normdx': None,
                         'detJ': float(detJ)})
        _flush_log(ErrorCode.SINGULAR_JACOBIAN)
        raise SolverError(ErrorCode.SINGULAR_JACOBIAN,
                           'Zero determinant of J at Newton iteration %d' % k,
                           context={'k': k, 'v': np.asarray(x).tolist(),
                                    'detJ': float(detJ), 'newton_history': history})
      try:
          dx = np.dot(np.linalg.inv(J),f)
      except np.linalg.LinAlgError as e:
        history.append({'k': k, 'v': np.asarray(x).tolist(),
                         'normf': float(np.linalg.norm(f)), 'normdx': None,
                         'detJ': float(detJ)})
        _flush_log(ErrorCode.SINGULAR_JACOBIAN)
        raise SolverError(ErrorCode.SINGULAR_JACOBIAN,
                           'Numerically singular J at Newton iteration %d (%r)' % (k, e),
                           context={'k': k, 'v': np.asarray(x).tolist(),
                                    'detJ': float(detJ), 'newton_history': history}) from e
      x = x - dx
      history.append({'k': k, 'v': np.asarray(x).tolist(),
                       'normf': float(np.linalg.norm(f)), 'normdx': float(np.linalg.norm(dx)),
                       'detJ': float(detJ)})
      if verbose:
          end = time.time()
          print(k,np.linalg.norm(f),np.linalg.norm(dx),end-start)
      if (np.linalg.norm(f) < feps) or (np.linalg.norm(dx) < xeps):
          _flush_log(ErrorCode.CONVERGED)
          return x

    print('Solution not found within tolerance after_',k,'_iterations\n')
    print('Exiting the code')
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
    
    r = np.empty(nr)
    rho = np.empty(nr)
    g = np.empty(nr)
    
    for k in range(nrs):
        r[k]=rs*(k+1)/nrs


    for k in range(nrf):
        r[k+nrs]=rs+(rf-rs)*k/nrf
    
    drf=(rf-rs)/nrf

    # Build density (rho) and gravitational acceleration (g)
    f4piG=4*np.pi*bigGnd/3

    #  in inner core
    avgr=0.5*r[0]
    rho[0]=np.polyval(rhos, avgr)
    g[0]=f4piG*rho[0]*r[0]
  
    for k in range(1,nrs):
        avgr=0.5*(r[k]+r[k-1])
        rho[k]=np.polyval(rhos, avgr)
        g[k]= f4piG*rho[k]*(r[k]**3-r[k-1]**3)/r[k]**2 +  g[k-1]*(r[k-1]/r[k])**2
    
    #  in fluid core
    avgr=r[nrs]+0.5*drf
    rho[1+nrs]=np.polyval(rhof, avgr)
    g[1+nrs]=f4piG*rho[1+nrs]*(r[1+nrs]**3-r[nrs]**3)/r[1+nrs]**2\
             +g[nrs]*(r[nrs]/r[1+nrs])**2
             
    for k in range(0,nrf):
        avgr=0.5*(r[k+nrs]+r[k+nrs-1])
        rho[k+nrs]=np.polyval(rhof, avgr)
        g[k+nrs]=f4piG*rho[k+nrs]*(r[k+nrs]**3-r[k+nrs-1]**3)/r[k+nrs]**2\
                 +g[k+nrs-1]*(r[k+nrs-1]/r[k+nrs])**2

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



