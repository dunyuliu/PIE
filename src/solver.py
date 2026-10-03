# solver.py is part of the software Mercury_present_evolution.
# It contains numerical functions used to solve the system.

# Function list:
# - mynewtonSys:

# - odeRK4_snow: 
#		ode solver for our system of equations.  
# - rhs_PTrhog_solid_snow: 
#		Right-hand sides of coupled ODEs for interior model equations.
# - rhs_fluid_snow: 
#		Right-hand sides of coupled ODEs for interior model equations
# - simpsonDat: 
#		Integration by Composite Simpson's rule
# - rhs_Pgz:  
#		Right-hand sides of coupled ODEs for hydrostatic pressure

import numpy as np
from scipy.constants import G
from scipy.constants import R as RGas
import coreEos as eos
from libCore import getchi_li_grun
import sys
	
def odeRK4_snow(diffeq,ricb,rcmb,h,y0,chi_li_icb,scale,param):
    """
    
     odeRK4_snow: ode solver for our system of equations  
     modified from NMM, odeRK4sysv.  Customization is such that it is possible
     to track changes of chi_li vs radius as well as integration of other
     variables.
    
    
     odeRK4sysv  Fourth order Runge-Kutta method for systems of first order ODEs
                 Vectorized version with pass-through parameters.
    
     Input:     diffeq = (string) name of the m-file that evaluates the right
                          hand side of the ODE system written in standard
                          form.
                ricb,rcmb = icb,cmb radius
                h       = stepsize for advancing the independent variable
                y0      = vector of the dependent variable values at icb
                chi_li_icb = chi_li('S'/'S+Si') or chi_lii('Si') at icb
    
     Output:    r = vector of independent variable values:  r(j) = ricb + j*h
                y = matrix of dependent variables values, one column for each
                    state variable.  Each row is from a different time step.
                rhof = density at each radius
                chi_li = Sulfur concentartion at each radius
    """

    r = np.arange(ricb,rcmb+h/2,h)#  Column vector of elements with spacing h
    nt = len(r)                             #  number of steps (+1 for the initial conditions)
    neq = len(y0)                           #  number of equations simultaneously advanced
    y = np.zeros((nt,neq))                  #  Preallocate y for speed
    y[0,:] = y0                             #  Assign IC. y0(:) is column, y0(:)' is row vector
    rhof=np.zeros(nt)
    chi_li=np.zeros(nt)
    
    #  Avoid repeated evaluation of constants    
    h2 = h/2
    h3 = h/3
    h6 = h/6   
    k1 = np.zeros(neq)
    k2 = k1
    # Preallocate memory for the Runge-Kutta
    k3 = k1  
    k4 = k1
    # coefficients and a temporary vector
    ytemp = k1  
    
    # Outer loop for all steps:  j = time step index;  k = equation number index
    # Note use of transpose on definition of yold, and in formula for y(j,:) 
    err2 = np.zeros(nt)
    err = [False, False, False, False, False]
    res = getchi_li_grun(y0[2],y0[0],chi_li_icb,scale,param)
    chi_li[0],rhof[0] = res[0:2]
    
    for j in range(1,nt): 
        rold = r[j-1]        
        yold = y[j-1,:]
        chi_li_old=chi_li[j-1]       #  Temp variables
        chi_li_temp,rhoftemp,grun,KS, err[0]=getchi_li_grun(yold[2],yold[0],chi_li_old,scale,param)
        k1 = eval(diffeq + '(rold,yold,ricb,rcmb,rhoftemp,grun,KS,scale)') #  Slopes at the start
        k1 = np.array(k1)
        ytemp = yold + h2*k1
        
        chi_li_temp,rhoftemp,grun,KS, err[1] =getchi_li_grun(ytemp[2],ytemp[0],chi_li_old,scale,param)
        k2 = eval(diffeq + '(rold+h2,ytemp,ricb,rcmb,rhoftemp,grun,KS,scale)') # 1st slope at midpoint
        k2 = np.array(k2)
        
        ytemp = yold + h2*k2
        chi_li_temp,rhoftemp,grun,KS, err[2] =getchi_li_grun(ytemp[2],ytemp[0],chi_li_old,scale,param)
        k3 = eval(diffeq + '(rold+h2,ytemp,ricb,rcmb,rhoftemp,grun,KS,scale)') #  2nd slope at midpoint
        k3 = np.array(k3)
        
        ytemp = yold + h*k3
        chi_li_temp,rhoftemp,grun,KS, err[3] =getchi_li_grun(ytemp[2],ytemp[0],chi_li_old,scale,param)
        k4 = eval(diffeq + '(rold+h,ytemp,ricb,rcmb,rhoftemp,grun,KS,scale)')  #  Slope at endpoint
        k4 = np.array(k4)
        
        y[j,:] = ( yold + h6*(k1+k4) + h3*(k2+k3) )  #  Advance all equations
        res = getchi_li_grun(y[j,2],y[j,0],chi_li_old,scale,param)
        chi_li[j],rhof[j] = res[0:2]
        err[4]            = res[4]
        
        if any(err)==True:
            err2[j] = 1
          
    return r,y,rhof,chi_li, err2
	
def rhs_PTrhog_solid_snow(chi_icb, r, y, ricb, scale, param):
    """
    rhs_PTrhog  Right-hand sides of coupled ODEs for interior model equations

    Input:    r      = radius, the independent variable 
              y      = vector (length 3) of dependent variables
              ricb   = ICB radius

    Output:   dydr   = column vector of dy(i)/dr values
    """

    # scales
    a       = scale['a']
    ga      = scale['ga']
    P       = scale['P']
    T       = scale['T']
    
    # get dimensional P and T
    T1      = T*y[2]
    P1      = P*y[0]

    #out = eos.solidFccFe(P1/1E+9,T1,param)
    out     = eos.eosInnerCore(chi_icb,P1/1E+9,T1,param)
    rho     = out[1]
    grun    = out[6]
    KS      = out[4]*1e+9
    # dydr: derivative of y to dr.
    dydr    = [-(a*ga/P)*rho*y[1],
                (a/ga)*4*np.pi*G*rho-2*y[1]/r,
                 -(a*ga)*grun*rho*y[1]*y[2]/KS]
    
    return dydr
	
def rhs_fluid_snow(r,y,ricb,rcmb,rho,grun,KS,scale):
    """
    # Right-hand sides of coupled ODEs for interior model equations
    # This version includes a stratified layer at CMB
    # Here, we also track the adiabatic Temperature
    # THIS VERSION to be used with odeRK4_snow.m
    
    # Input:    r      = radius, the independent variable 
    #           y      = vector (length 4) of dependent variables
    #           ricb   = ICB radius
    #           rcmb   = CMB radius
    #           rho    = density
    #           grun   = gruneisan
    #           KS     = adiabatic bulk modulus
    #
    # Output:   dydr = column vector of dy(i)/dr values
    """
    
    # scales
    a=scale['a']
    ga=scale['ga']
    P=scale['P']

    # Size of thermally stratifued layer
    # Default rst=ricb + (rcmb-ricb)/2
    rst = ricb + (rcmb-ricb)/2

    if r<rst: 
        dydr = [ -(a*ga/P)*rho*y[1],
                (a/ga)*4*np.pi*G*rho-2*y[1]/r,
                -(a*ga)*grun*rho*y[1]*y[2]/KS,
                -(a*ga)*grun*rho*y[1]*y[2]/KS]
    else:
        dydr = [-(a*ga/P)*rho*y[1],
                (a/ga)*4*np.pi*G*rho-2*y[1]/r,
                -(a*ga)*grun*rho*y[1]*y[2]*(1 -0.95*(r-rst)/(rcmb-rst))/KS,
                -(a*ga)*grun*rho*y[1]*y[2]/KS]
        
    return dydr
def simpsonDat(x,f):
    """
    simpsonDat  Integration by Composite Simpson's rule
                adapted from nmm package, here for a function f evaluated at
                equally spaced points x

    Synopsis:  I = simpson(fun,a,b,npanel)

    Input:     x = equally spaced points (number of points n must be odd)
               f = integrand at these x points
    Output:    I = approximate value of the integral from x(1) to x(n) of f(x)*dx
    
    """

    h=x[1]-x[0]
    I = (h/3)*(f[0]+4*np.sum(f[1::2]) + 2*np.sum((f[2::2])[0:-1]) + f[-1])
    return I

def rhs_Pgz(r, y, rho, scale):
    """
    rhs_Pgz  Right-hand sides of coupled ODEs for hydrostatic pressure


    Input:    z      = depth, the independent variable 
              y      = vector (length 2) of dependent variables
              rho    = density (=constant)

    Output:   dydr = column vector of dy(i)/dz values
    """
    # scales
    a=scale['a']
    ga=scale['ga']
    P=scale['P']

    dydr = [-(a*ga/P)*rho*y[1],
            (a/ga)*4*np.pi*G*rho-2*y[1]/r]
    
    return dydr