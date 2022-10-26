# libCore.py is part of the software Mercury_present_evolution.
# It contains common functions used by the presentDay and evolution model.
import numpy as np
import time
import scipy
import coreEos as eos
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import inv
from scipy.constants import G
from scipy.constants import R as RGas
from globalvar import *
from planet_input import *

# Added by Tilio. 20220614.
TmFeS=eos.meltingDataFromFile("TmFeSmelt.dat")
def TmFeSSi(xS,xSi,p):
    p1=p*1e-9 
    TmFe= 495.4969600595926*(22.19 + p1)**0.42016806722689076   # Fe liquidus Anzellini et al. 2013
    deltaTS=TmFeS(0,p1)-TmFeS(xS,p1)
    TSiEut=1538*(1.+0.040551*p1)**0.4608294930875576 # Fe-rich eutectic melting T of Fe-Si Edmund et al 2022
    xSiEut=max_Si_Edmund2022 # assumed constant for p range of Mercury, Edmund et al 2022
    deltaTSi=(TmFe-TSiEut)*xSi/xSiEut
    return TmFe-deltaTS-deltaTSi

def TmFeSSi_Steinbruegge2020(xS,xSi,P):
    # Fe-FeS-FeSi melting temperature
    # xS and xSi in wt and P in Pa, returns liquidus temperature in K.
    P1    = P*1e-9  
    TmFe  = 495.4969600595926*(22.19+P1)**0.42016806722689076   # Fe melting T from Anzellini et al. (2013), 
    # also in Dumberry and Rivoldini (2015) eq 29.

    # coefficients to calculate the eutectic melting T for FeS from Dumberry and Rivoldini (2015) eq 27.
    if P1 < 14:
        Te0 = 1265.4
        b1  = -11.15
        Pe0 = 3
    elif P1 < 21:   
        Te0 = 1142.7
        b1  = 29
        Pe0 = 14
    else:    
        Te0 = 1345.72
        b1  = 12.9975
        Pe0 = 21

    TSEut  = Te0+b1*(P1-Pe0) # eutectic melting Te(P) of FeS from Dumberry and Rivoldini (2015) eq 27.
    xSEut  = 0.11+0.187*np.exp(-0.065*P1)  # eutectic S fraction xi_e(P) from Dumberry and Rivoldini (2015) eq 28.

    #TSiEut=1538*(1.+0.040551*P1)**0.4608294930875576 # Fe-rich eutectic melting T of Fe-Si Edmund et al 2022
    Tm15   = 1478 *(P1/10+1)**(1/3) # parameterization for Anzellini; used in Steinbruegge et al. (2020).
    xSiEut = max_Si_Steinbruegge2020

    deltaTSi = (TmFe-Tm15)*xSi/xSiEut
    deltaTS  = (TmFe-TSEut)*xS/xSEut # the delta term in eq 26 of DR2015.
    return TmFe-deltaTS-deltaTSi # return the melting temperature Tm(P,xi_S) in eq 26 of DR2015.

def reorder_el(v,chi_Si_constant,param):
    # input v and chi_Si_constant, which are the inverted wt and constant wt from chi_Si_icb.
    el = param['li_el']
    if el == 'S':
        tmp = {'Si':0, 'S':v}
    elif el == 'Si':
        tmp = {'Si':v, 'S':0}
    elif el == 'S+Si':
        tmp = {'Si':chi_Si_icb, 'S':v}
    return tmp

def getCoreLiquidus(el1,el2,P,param,To):
	# getCoreLuquidus calculates the melting temperature of the core
	# 	given the wt% of light elements and pressure. 
	# It calls for function eos.liquidusFeSSi.
	
    # AR: new compact formulation old one not correct
    # el1 is wt of S and el2 is wt of Si, P in Pa
    # why fo we need To
    # this is ultra ugli! for all cases el1 shoud be S and el2 Si
    # or use a dictionary
	
    # What's To? Since To is mostly zero, the return for 'S'/'Si' is simply Tm.
    # The function simply calculates the melting temperature given P and wt% of light elements.
    
    # el1 and el2 are wt% of S and Si, respectively.
	
    el = param['li_el']
    if el == 'S':
        xS = el1
        xSi = 0
    elif el == 'Si':
        xS = 0
        xSi = el2
    elif el == 'S+Si':
        xS = el1
        xSi = el2
		
    #Tm=eos.liquidusFeSSi(xS,xSi,P)
    Tm=param['liquidus'](xS,xSi,P)
    return Tm-To

def getchi_li_grun(yT,yP,chi_li_old,scale,param):
    # The function solves the eos of the outer core. 
    # scales
    P      = scale['P']
    T      = scale['T']  
    el     = param['li_el']
    
    # get dimensional P and T
    T1     = T*yT
    P1     = P*yP

    # chi_li_old, inverted light element xi from the smaller radii on the integration path.
    chi_icb = reorder_el(chi_li_old, chi_Si_icb, param)
    Tm      = getCoreLiquidus(chi_icb['S'], chi_icb['Si'], P1,param,0) # obtain the melting T given S and Si concentration.
    
    # See P257 of Dumberry and Rivoldini (2015).
    if T1  > Tm: 
        # If the adiabat temperature T1 is larger than liquidus Tm,
        # assume xi_icb(chi_li) on basis of previous radius integration point.         
        chi_li=chi_li_old # chi_li_old is the light element concentration from a smaller radii point in the integration path. 
    else:
        # If the adiabat temperature T1 falls below the liquidus Tm, 
        # compute the xi - light element concentration implied by this value of T at the local pressure. This computed xi is used to calculate T and Tm for points at larger radii on the integration point. 
        if el == 'S' or el == 'S+Si':
            chi_li_eut  = 0.11+0.187*np.exp(-0.065*P1*1e-9) # The maximum light element concentration allowed. This equation is good for Fe-FeS based on eq 28 in DR2015.
            sol         = scipy.optimize.root(lambda x: getCoreLiquidus(x, chi_icb['Si'], P1, param, T1), chi_icb['S'], tol=1e-6) 
        elif el == 'Si':
            # ATTENTION! the eq above for chi_li_eut is not good for Fe-Si or Fe-S-Si.
            if liquidus_eq == 'Steinbruegge':
                chi_li_eut  = max_Si_Steinbruegge2020 # Set as constant, depending on liquidus_mode
            elif liquidus_eq == 'Edmund':
                chi_li_eut  = max_Si_Edmund2022
            sol         = scipy.optimize.root(lambda x: getCoreLiquidus(chi_icb['S'], x, P1, param, T1), chi_icb['Si'], tol=1e-6) 
            
        chi_li = min(sol.x[0],chi_li_eut)    
        print(chi_li, chi_li_eut)
    chi_icb = reorder_el(chi_li, chi_Si_icb, param)
    out     = eos.liquidNonIdalFeSSi([chi_icb['S'], chi_icb['Si']],P1/1E+9,T1,param)
    #print(out,chi_li_old)
    rho     = out[1]
    KS      = out[4]*1E+9
    grun    = out[6]
    return chi_li, rho, grun, KS
	
def getpotvsr(nr,bigGnd,rnd,rhond,gnd):
    # This function calculates the total potential vs radius in core

    l=2 # %spherical harmonic degree

    # build matrix A (sparse) element by element
    # specifying row, column and numerical value of all non-zero

    ndim=2*nr-1
    k=0
  
    row = np.zeros(3191, dtype=int)
    col = np.zeros(3191, dtype=int)
    s = np.zeros(3191)
    
    kk=0
    row[kk]=k
    col[kk]=k
    s[kk]=rnd[0]**(2*l+1)
  
    kk=kk+1
    row[kk]=k
    col[kk]=k+1
    s[kk]=-1
    
    kk=kk+1
    row[kk]=k
    col[kk]=k+2
    s[kk]=-rnd[0]**(2*l+1)

    alpha = 4.0*np.pi*bigGnd*rnd[0]*(rhond[0]-rhond[1])/gnd[0]

    kk=kk+1
    row[kk]=k+1
    col[kk]=k
    s[kk]=(l - alpha)*rnd[0]**(2*l+1)

    kk=kk+1
    row[kk]=k+1
    col[kk]=k+1
    s[kk]=l+1

    kk=kk+1
    row[kk]=k+1
    col[kk]=k+2
    s[kk]=-l*rnd[0]**(2*l+1)

    for j in range(1,nr-1):
    
        k=2*(j+1)-2
        
        kk=kk+1
        row[kk]=k
        col[kk]=k
        s[kk]=rnd[j]**(2*l+1)

        kk=kk+1
        row[kk]=k
        col[kk]=k-1
        s[kk]=1

        kk=kk+1
        row[kk]=k
        col[kk]=k+1
        s[kk]=-1
    
        kk=kk+1
        row[kk]=k
        col[kk]=k+2
        s[kk]=-rnd[j]**(2*l+1)
        
        alpha = 4.0*np.pi*bigGnd*rnd[j]*(rhond[j]-rhond[j+1])/gnd[j]

        kk=kk+1
        row[kk]=k+1
        col[kk]=k-1
        s[kk]=-(l+1 + alpha)
    
        kk=kk+1
        row[kk]=k+1
        col[kk]=k
        s[kk]=(l - alpha)*rnd[j]**(2*l+1)
    
        kk=kk+1
        row[kk]=k+1
        col[kk]=k+1
        s[kk]=l+1
    
        kk=kk+1
        row[kk]=k+1
        col[kk]=k+2
        s[kk]=-l*rnd[j]**(2*l+1)

    k=2*nr-2
    kk=kk+1
    row[kk]=k
    col[kk]=k
    s[kk]=rnd[nr-1]**l

    # build sparse matrix A
    A=np.zeros([ndim, ndim])
    A[row,col] = s

    #A = np.array(row,col,s,ndim,ndim)

    rhs=np.zeros(2*nr-1)
    rhs[2*nr-2]=1.0

    A = csc_matrix(A)
    #print(A)
    b = inv(A)*rhs

    # solution
    pot = np.empty(nr)
    pot[0]=b[0]*rnd[0]**l
    
    for k in range(1,nr):
        kk=2*(k+1)-2
        pot[k]=b[kk]*rnd[k]**l + b[kk-1]*rnd[k]**(-l-1)

    return pot

def get_mass_norm(r,rho,rho_mean):
    ssum = rho[0]/rho_mean*r[0]**3/r[-1]**3
    for i in range(1,len(r)):
        ssum = ssum + rho[i]/rho_mean*(r[i]**3/r[-1]**3-r[i-1]**3/r[-1]**3)
    return ssum

def get_mass_core(r,rho):
    ssum = rho[0]*r[0]**3/r[-1]**3
    for i in range(1,len(r)):
        ssum = ssum + rho[i]*(r[i]**3-r[i-1]**3)
    return ssum
    
def get_moi(r,rho,rho_mean):   
	# calculate moment of inertia given radius and density profiles.
    ssum = rho[0]/rho_mean*r[0]**5/r[-1]**5
    for i in range(1,len(r)):
        ssum = ssum + rho[i]/rho_mean*(r[i]**5/r[-1]**5-r[i-1]**5/r[-1]**5)

    return 2/5*ssum

def get_ccc(r,rho,rho_mean):
    ssum = rho[0]/rho_mean*r[0]**5/r[-1]**5
    for i in range(1,len(r)-2):
        ssum = ssum + rho[i]/rho_mean*(r[i]**5/r[-1]**5-r[i-1]**5/r[-1]**5)
    return 2/5*ssum

# Osolete
def getmelt_anzellini(chis,P,param,To):
    """
    Determines melting temperature of FeS mixture as a function 
    of chis and P.  
    Here, the melting point of pure Fe is determined according to Anzellini,
    Science 2013
    
    From Eq 2 of Anzellini et al 2013
    but reformulated as a 3rd order polynomial
    """

    el = param['li_el']
    
    if el == 'S':
        P1=P*1e-9;  
        # parametrization for Anzellini
        TmFe= 495.4969600595926*(22.19 + P1)**0.42016806722689076
        
        if P1 < 14:
            Te0=1265.4
            b1=-11.15
            Pe0=3
        elif P1 < 21:   
            Te0=1142.7
            b1=29
            Pe0=14
        else:    
            Te0=1345.72
            b1=12.9975
            Pe0=21
            
        Te=Te0+b1*(P1-Pe0)
        chiSeut=0.11+0.187*np.exp(-0.065*P1)
        
        Tm = TmFe -(TmFe - Te)*chis/chiSeut
        
        return Tm-To
    
    else:
        #a = 10
        #c = 3
        #P=P*1e-9
        #T0 = 1678 - 1000*chis
        #Tm = T0*(P/a+1)**(1/c)
        #return Tm-To   

        # Simon Glatzel Fit to Anzellini 
        #a = 22.19
        #c = 2.38
        #P=P*1e-9
        #T0 = 1822 - 1000*chis
        #Tm = T0*(P/a+1)**(1/c)
        #return Tm-To   
        
        P1=P*1e-9;  
        # parametrization for Anzellini
        TmFe= 495.4969600595926*(22.19 + P1)**0.42016806722689076
        Tm15 = 1478 *(P1/10+1)**(1/3)        
        Tm =(chis/0.15)*Tm15+(1-chis/0.15)*TmFe
        return Tm-To

# Osolete
def getmelt_anzellini_mix(el1, el2, P,To):
    """
    Determines melting temperature of FeS mixture as a function 
    of chis and P.  
    Here, the melting point of pure Fe is determined according to Anzellini,
    Science 2013
    
    From Eq 2 of Anzellini et al 2013
    but reformulated as a 3rd order polynomial
    """

    chis1 = el1/(1-el2)
    chis2 = el2/(1-el1)
    w1 = el1/(el1+el2)
    w2 = el2/(el1+el2)
    
    print(el1,chis1,el2,chis2)
    P1=P*1e-9 
    # parametrization for Anzellini
    TmFe= 495.4969600595926*(22.19 + P1)**0.42016806722689076
    
    if P1 < 14:
        Te0=1265.4
        b1=-11.15
        Pe0=3
    elif P1 < 21:   
        Te0=1142.7
        b1=29
        Pe0=14
    else:    
        Te0=1345.72
        b1=12.9975
        Pe0=21
        
    Te=Te0+b1*(P1-Pe0)
    chiSeut=0.11+0.187*np.exp(-0.065*P1)
    
    Tm1 = TmFe -(TmFe - Te)*chis1/chiSeut

    
    # parametrization for Anzellini
    TmFe= 495.4969600595926*(22.19 + P1)**0.42016806722689076
    Tm15 = 1478 *(P1/10+1)**(1/3)        
    Tm2 =(chis2/0.15)*Tm15+(1-chis2/0.15)*TmFe
    return (w1*Tm1+w2*Tm2)
