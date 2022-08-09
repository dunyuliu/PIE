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
         fout(7) = isnow  (0,1,2 = no, layer, deep snow)
         fout(8) = isnowcmb  (0,1 = snow at CMB (no,yes))
         fout(9) = chi_li_in (initial sulfur content in core)
         fout(10)= gradTa (adiabatic temp gradient at CMB)

     shoot from set of conditions at r=small
     """
    # Mercury parameters
    M=param['GM']/G
    rm = param['rm']
    rhomean = 3*M/(4*np.pi*rm**3)

    # scales
    a=scale['a']
    ga=scale['ga']
    P=scale['P']
    T=scale['T']

    # limits of integration
    r0=0.0001/a
    rcmb=v[2]
    rhom=v[3]*rhomean

    # calculate Pcmb, gcmb
    rc=rcmb*a
    rhd=rh*a
    Pcmb,gcmb=getPgcmb_crust(rhom,rc,rhocr,rhd,param,scale)
    Pcmb=Pcmb/P
    gcmb=gcmb/ga
    CmC=param['CmC']
    CMR2=param['CMR2']

    # get gruneisan, bulk and density for P,T at r0 
    P1=P*v[0]
    T1=T*v[1]
    # if param['li_el'] == 'S', chi_li_icb = S
    # if param['li_el'] == 'Si', chi_li_icb = Si
    # if param['li_el'] == 'S+Si', chi_li_icb = S
    chi_li_icb=v[4] # retrieve chi_li_icb, whose initial is 0.05.
    
    # 20220302. Replace the following lines with the new function eosInnerCore.
    #if param['li_el'] =='S':
    #    rho = eos.solidFccFe(P1/1E+9,T1,param)[1]
    #elif param['li_el'] == 'Si':
    #    rho = eos.solidFccFeSi(chi_li_icb, P1/1E+9, T1, param)[1]
    #elif param['li_el'] == 'S+Si':
    #    rho = eos.solidFccFeSi(chi_Si_icb, P1/1E+9, T1, param)[1]
    #if param['li_el'] == 'Si':
    #    chi_icb = {'Si':v[4], 'S':0}
    #elif param['li_el'] == 'S':
    #    chi_icb = {'Si':0, 'S':v[4]}
    #elif param['li_el'] == 'S+Si':
    #    chi_icb = {'Si':chi_Si_icb, 'S':v[4]}
    chi_icb = reorder_el(v[4],chi_Si_icb,param)
    rho = eos.eosInnerCore(chi_icb,P1/1E+9,T1,param)[1]

    #boundary values at r0 for in://csegweb.cgd.ucar.edu/experiments/public/?ref=navtegration
    gr0=4*np.pi*G*rho*(r0*a)/(3*ga)
    # initial P, gr0, T to integrate from core to inner core boundary.
    y0 = [v[0], gr0, v[1]]

    #Shoot In solid inner core 
	# scipy.integrate.solve_ivp solves an initial value problem for a system of ODEs.
	# https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html.
	# It numerically integrates a system of ODEs given an initial value.
	# Integrate from center of the planet to icb. r0 is essentially zero.
	# Default solver is RK45. LSODA is Adams/BDF with automatic stiffness detection and switching.
    sol = scipy.integrate.solve_ivp(lambda t,y: rhs_PTrhog_solid_snow(chi_icb, t,y,ricb,scale,param),
                                    [r0, ricb], y0, method='LSODA',
                                    rtol=5e-5)
    # return radius array to rs.
    # return solution at each rs to ys.
    rs = sol.t # I think the discretization of rs is automatically determined from solve_ivp.
    ys = sol.y
    ns=len(rs)
    # calculate melting temperature at ICB
    
    P1=P*ys[0,-1]

    # Use the new getCoreLiquidus function.
    Tmicb = getCoreLiquidus(chi_icb['S'],chi_icb['Si'],P1,param,0)/T # changed first two variables from chi_li_icb and chi_Si_icb
    # boundary values for FOC integration: 
    # continuity of P, g, and T=Tm
    yicb = [ys[0,-1],ys[1,-1],Tmicb,Tmicb]

    # Shoot In Fluid core
    nc=51 # discretize the liquid core into nc grids. 
    h=(rcmb-ricb)/(nc-1) # grid size
    rc,yc,rhof,chi_li = odeRK4_snow('rhs_fluid_snow',ricb,rcmb,h,yicb,chi_li_icb,scale,param)
	# rc is radius array from ricb -> rcmb with grid size h.
	
    # Calculate moments of inertia:
    # First build polynomials of density
    rhos = np.empty(ns)
    # 20220302. Replace the following lines with the new function eosInnerCore.
    #if param['li_el'] == 'S':
    #    for i in range(0,ns):
    #        rhos[i]=eos.solidFccFe(P*ys[0,i]/1E+9,T*ys[2,i],param)[1]/rhomean
    #elif param['li_el'] == 'Si':
    #    for i in range(0,ns):
    #        rhos[i]=eos.solidFccFeSi(chi_li[0],P*ys[0,i]/1E+9,T*ys[2,i],param)[1]/rhomean
    #elif param['li_el'] == 'S+Si':
     #    for i in range(0,ns):
    #        rhos[i]=eos.solidFccFeSi(chi_Si_icb, P*ys[0,i]/1E+9, T*ys[2,i], param)[1]/rhomean
    #if param['li_el'] == 'Si':
    #    chi_icb = {'Si':chi_li[0], 'S':0}
    #elif param['li_el'] == 'S':
    #    chi_icb = {'Si':0, 'S':chi_li[0]}
    #elif param['li_el'] == 'S+Si':
    #    chi_icb = {'Si':chi_Si_icb, 'S':chi_li[0]}
    chi_icb = reorder_el(chi_li[0],chi_Si_icb, param)    
    for i in range(0,ns):
        rhos[i]=eos.eosInnerCore(chi_icb,P*ys[0,i]/1E+9, T*ys[2,i], param)[1]/rhomean
        
    sols=np.polyfit(rs,rhos,3)

    for i in range(0,nc):
        rhof[i]=rhof[i]/rhomean

    solf=np.polyfit(rc,rhof,3)
    
    # ... then multiply by r4 and integrate
    rhor4=np.convolve(sols,[1,0,0,0,0])
    bigIo=np.polyval(np.polyint(rhor4),ricb)
    rhor4=np.convolve(solf,[1,0,0,0,0])
    bigIo=bigIo + np.polyval(np.polyint(rhor4),rcmb)\
          -np.polyval(np.polyint(rhor4),ricb)


    bigCm = 0.2*rhocr*(1-rh**5)/rhomean + 0.2*rhom*(rh**5-rcmb**5)/rhomean
    bigIo = bigIo + bigCm   # To get dimensional moment of inertia, * 8pi/3*rhomean*a^5
    #CmC=bigCm/bigIo # Cm/C 
    #CMR2=2*bigIo # C/MR^2 
    CmCtry=bigCm/bigIo #Cm/C 
    CMR2try=2*bigIo #C/MR^2 

    # calculate initial sulfur
    chisrc2=chi_li*rc**2
    chi_li_in = 3/(rcmb**3)*simpsonDat(rc,chisrc2) # initial sulfur in inner core
    
    # snow state
    isnow=0  # snow index: default is no snow

         
    if ((chi_li[-1]-chi_li_icb) > 1e-10):
        isnow=1
        # get dimensional P and T at second point in FOC
        i=0
        T1=T*yc[i,2]
        P1=P*yc[i,0]

        # establish S and Si concentrations -- added 7/15/2022
        #if param['li_el'] == 'Si':
        #    chi_icb = {'Si':chi_li[i], 'S':0}
        #elif param['li_el'] == 'S':
        #    chi_icb = {'Si':0, 'S':chi_li[i]}
        #elif param['li_el'] == 'S+Si':
        #    chi_icb = {'Si':chi_Si_icb, 'S':chi_li[i]}
        chi_icb = reorder_el(chi_li[i],chi_Si_icb, param)             
        Tm=getCoreLiquidus(chi_icb['S'], chi_icb['Si'], P1,param,0)  # get Tliquidus

        if abs(T1-Tm)<1e-8: # if adiabat temperature = Liquidus 
            isnow=2    
        
    isnowcmb=0;  # snow at cmb index: default no
    if isnow==1 or isnow==2:
        i=-1

        # establish S and Si concentrations -- added 7/15/2022
        #if param['li_el'] == 'Si':
        #    chi_icb = {'Si':chi_li[i], 'S':0}
        #elif param['li_el'] == 'S':
        #    chi_icb = {'Si':0, 'S':chi_li[i]}
        #elif param['li_el'] == 'S+Si':
        #    chi_icb = {'Si':chi_Si_icb, 'S':chi_li[i]}
        chi_icb = reorder_el(chi_li[i],chi_Si_icb,param)
        # get dimensional P and T
        T1=T*yc[i,2]
        P1=P*yc[i,0]
        Tm=getCoreLiquidus(chi_icb['S'],chi_icb['Si'], P1,param,0)  # get Tliquidus

        if abs(T1-Tm)<1e-6:  #if adiabat temperature = Liquidus
            isnowcmb=1
    
    # Calculate k2_h and xi_h
  
    # avg inner core, outer core densities
    #rhor2=np.convolve(sols,[1,0,0])
 
    # Calculate k2 and xi
    rhoml=rhom/rhomean

    k2,xi=getk2(ricb,rcmb,rhoml,sols,solf,param,scale)

        
    # adiabatic temp gradient at CMB
    gradTa=T/a*(yc[nc-1,3]-yc[nc-2,3])/(rc[nc-1]-rc[nc-2])
    fout=[P*ys[0,-1],T*yc[nc-1,2],isnow,isnowcmb,chi_li_in,gradTa]

    # include the (1+xi) factor on Cm/C
    CmCtry = CmCtry*(1+xi)
    
    # function to minimize (roots)
    f=[yc[-1,0]-Pcmb,  # match P at cmb
       yc[-1,1]-gcmb,  # match g at cmb
       ys[2,-1]-Tmicb, # match Tm at icb
       CmCtry-CmC,
       CMR2try-CMR2]

    # concatenate solution
    r=np.concatenate((rs,rc))
    ytemp=np.vstack((ys,ys[2]))
    y = np.hstack((ytemp,np.transpose(yc)))
    rho = np.concatenate((rhos,rhof))
    chi = np.concatenate((np.zeros(ns),chi_li))
    if param['li_el']=='Si': 
        chi[0:ns] = chi_li[0]
    yy=np.vstack((y[0],y[1],y[2],y[3],rho,chi))
    
    return f,r,yy,fout

def mynewtonSys(Jfun,x0,varargin,
                xtol=5e-5,ftol=5e-5,maxit=15,verbose=False):
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
    """

    
    xeps = xtol
    feps = ftol #   %  Smallest tols are 5*eps

    if verbose:
        print('\nNewton iterations\n  k     norm(f)      norm(dx)    time(s)\n')

    if Jfun == 'J_mercmodel_nosic': x0.pop(1)
    x = x0
    k = 0        #  Initial guess and current number of iterations
    
    
    while k <= maxit:
      start = time.time()
      k = k + 1
      J,f = eval(Jfun)(x,varargin)   #   Returns Jacobian matrix and f vector
      dx = np.dot(np.linalg.inv(J),f)
      x = x - dx
      if verbose:     
          end = time.time()
          print(k,np.linalg.norm(f),np.linalg.norm(dx),end-start)
      if (np.linalg.norm(f) < feps) or (np.linalg.norm(dx) < xeps):
          return x

    print('Solution not found within tolerance after_',k,'_iterations\n')
    print('Exiting the code')
    sys. exit()
	
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



