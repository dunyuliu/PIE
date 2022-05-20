#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 29 16:05:03 2019
@author: gregor
Modifed by dliu since 03/25/2022.
"""
# change log:
# 03/25/2022: add comments for variables and functions.
"""
% Constructs interior model of mercury.
% Here, not only we constrain models to satisfy mean density,
% we also constrain the models to satisfy specific values of 
% Cm/C and C/Mr^2
%
% Here we impose that Tm = Ticb, with snow scenario
"""
import numpy as np
import libCore_evolution as lc
import visualization_evolution as vis
import coreEos as eos
from scipy.constants import G
import glob
import os
import pandas as pd
from globalvar import *

fccFe=eos.eosAndersonGrueneisen(M0=MFe,p0=1.e-5,T0=298,V0=6.82,
                            alpha0=7.e-5,KT0=163.4,KTP0=5.38,
                            deltaT=5.5,kappa=1.4,GibbsE=eos.GibbsfccFe)   
liquidFe=eos.eosAndersonGrueneisen(M0=MFe,p0=1E-5,T0=298,V0=6.88,
                               alpha0=9E-5,KT0=148,KTP0=5.8,deltaT=5.1,
                               kappa=0.56,GibbsE=eos.GibbsLiquidFe)
liquidFeS=eos.eosAndersonGrueneisen(M0=MFeS,p0=1E-5,T0=1650,
                                V0=22.956500240757844,alpha0=11.9e-5,
                                KT0=17.01901122392699,
                                KTP0=5.92217679116356,
                                deltaT=5.92217679116356,kappa=1.4,
                                gamma0=1.3,q=0)
liquidFeSi=eos.eosAndersonGrueneisen(M0=MFeSi,p0=1E-5,T0=1723,
                                 V0=16.5839,alpha0=17.6525e-5,KT0=69.0074,
                                 KTP0=7.76007,deltaT=4.07505,kappa=0.56,
                                 gamma0=1.61986,q=0)

# Updated parameters
param = {'rm':2439360.0,
         'GM':22031.86E+9,
         'c22':0.804151E-05,
         'CmC':0.148/0.346,
         'CMR2':0.346,
         'MFe':MFe,
         'MS':32.065,
         'MSi':28.08,
         'MFeS':MFeS,
         'MFeSi':(55.845+28.08),
         'lFe':liquidFe,
         'lFeS':liquidFeS,
         'lFeSi':liquidFeSi,
         'fccFe':fccFe,
         'li_el':'S+Si',
         'name':'replace_me'}
    
M = param['GM']/G
rm_s = 2439360.0
rhomean_s = 3*M/(4*np.pi*rm_s**3)

# scales
scale = {'a':2439360.0,
         'rmean':rhomean_s,
         'ga':M*G/2439360**2,
         'P':rhomean_s*rm_s*M*G/rm_s**2,
         'T':1800}

# build model from shooting method, using multi-directional Newton method 
# for each iteration
xtol=1.e-5
ftol=1.e-5
maxit=15

pday_models = glob.glob(path_to_present_day_models + "*.h5")

# crustal density and thickness
rhocr=2974
hcr0=26e3
md=0

print(pday_models)
for model in pday_models:
    k=0
    print('model',model)
    params = pd.read_hdf(model, key='misc') # key misc is a big list of scalar quantities.
    chi_li_infix = params['chi_liin'].values[0] #params['chiSin'].values[0] # initial sulfur
    chi_li_icb = params['chi_li_icb'].values[0]  # sulfur at inner core boundary
    
    ricb0 = params['ricb'].values[0] # inner core boundary radius
    rcmb0 = params['rcmb'].values[0] # core-mantle boundary radius
    rhom = params['rhom'].values[0] # what mantle density?
    core_mass = params['core_mass'].values[0] # the mass of core?
    Tctr0 = pd.read_hdf(model, key='T')[0] # Temperature profile at center? 
    Tmantle_old = pd.read_hdf(model, key='T').values[-1] # temperature at mantle surface?
    Pctr = pd.read_hdf(model, key='P')[0] # pressure profile at center? 
    #chiS0 = pd.read_hdf(model, key='chiS')[0] # no chiS key now
    chi_li0 = pd.read_hdf(model, key='chi_li')[0]   

    mantle_mass = lc.get_mass_mantle(rcmb0,rm_s-hcr0,rhom) # get mantle mass
    

    # Initial Guess vector
    # 1) P(r=0) 2) ricb 3) rcmb 4) rm 5) chiSicb
    v0=[Pctr/scale['P'],1,rcmb0/rm_s,1,chi_li_icb,1]
    Gyr = 0

    # create folder for output data. If not exist, create one and run the models.
    directory = path_to_output + str(round(ricb0/1000,1))
    print(directory, os.path.exists(directory))
    if not os.path.exists(directory):
        os.makedirs(directory)
          
        for ricb_evo in range(0,int(ricb0/1000)+50000,20):
            ricb = (ricb0-ricb_evo*1E+3)/rm_s
            """
            print('ricb:',ricb*rm_s/1000)
            print('Pcenter:',Pctr/1E+9)
            print('ChiS:',chiSinfix)
            print('ricb evo:',ricb_evo)
            print('Core Mass:',core_mass)
            """
            
            if ricb>0:
                print('ricb>0 : running model WITH inner core')
                v = lc.mynewtonSys('J_mercmodel',v0,
                            [ricb,rhocr,rhom,chi_li_infix,core_mass,mantle_mass,param,scale],
                            xtol=xtol, ftol=ftol, maxit=maxit, verbose=True)
            
                v0=v.tolist() # % initial guess for next is taken as previous solution.
          
                # final solution
                [f,r,yy,fout,ricb,rhomean,rm,hcr] = lc.shoot_mercmodel(v,ricb,rhocr,rhom,
                                                                   chi_li_infix,core_mass,mantle_mass,
                                                                   param,scale)
    
            else:
                print('ricb<=0 : running model WITHOUT inner core')
                Tsrpls = abs(ricb0-ricb_evo*1E+3)/1000
                v = lc.mynewtonSys('J_mercmodel_nosic',v0,
                            [Tsrpls,rhocr,rhom,chi_li_infix,core_mass,mantle_mass,param,scale],
                            xtol=xtol, ftol=ftol, maxit=maxit, verbose=True)
                
                [f,r,yy,fout,ricb,rhomean,rm,hcr] = lc.shoot_mercmodel_nosic(v,Tsrpls,rhocr,rhom,chi_li_infix,core_mass,mantle_mass,param,scale)
                v0=np.insert(v,1,0).tolist()
                    
            nr=len(r) # r is all the radius points array for this specific rs. yy is a 6-element array.
        
            # re-scale
            r=scale['a']*r
            P1=scale['P']*yy[0]
            g1=scale['ga']*yy[1]
            T1=scale['T']*yy[2]
            Tctr=T1[0]
            Tad=scale['T']*yy[3]
            rho1=rhomean*yy[4]
            chi_li=yy[5] # the light element wt profile inverted
    
            """
            plt.plot(r/1000,T1)
            plt.show()    
            plt.plot(r/1000,P1/1E+9)
            plt.show()  
            plt.plot(r/1000,chiS)
            plt.show()
            """
            
            #rhom[k]=v[3]*rhomean # different from PresentDay model, this is inverted now.
            chi_li_icb=v[4]
            chi_li_cmb=chi_li[-1]
            rcmb=r[-1]
        
            rhd=(rm-hcr)
            r_2=np.append(r,[rhd,rm])    
            rho1_2=np.append(rho1,[rhom,rhocr])
            moi = lc.get_moi(r_2,rho1_2,rhomean)
            ccc = lc.get_ccc(r_2,rho1_2,rhomean)
            cmc = 1-ccc/moi
            #mass = lc.get_mass_norm(r_2,rho1_2,rhomean)
            #print(mass,moi,ccc,cmc)
            #plt.plot(r/1000,rho1)
            #plt.show()
        
            Picb=fout[0]
            Tcmb=fout[1]
            isnow=fout[2]
            isnowcmb=fout[3]
            chi_li_in=fout[4]
    
            Tmantle = T1[-1]
            Tdiff = Tmantle-Tmantle_old
            Tmantle_old = Tmantle
            Gyr = Gyr-Tdiff/60
            
            #print('rhom:',rhom[k])
            vis.plot_isnow(ricb,r,rhd,rm,T1,P1,chi_li,rho1,
                           chi_li_in,moi,cmc,1,Gyr,k,directory,param)
                
        
            #print('rs:',rs[k]/1000)
            #print('isnow:',fout[2])
            #print('isnow cmb:',fout[3])
            #print('DeltaS:',chiS[-1],v[4])    
            Pcmb=P1[-1]
            Pctr=P1[0]
            chi_li_euticb=0.11 +0.187*np.exp(-0.065*Picb*1e-9)
            chi_li_eutcmb=0.11 +0.187*np.exp(-0.065*Pcmb*1e-9)
            k+=1
            
            print('FINAL MANTLE TEMPERATURE:',Tmantle)
            print()
            if Gyr<-4.5: break
        
            zones=np.zeros(len(P1))
            Tms=[]
            for i in range(len(r)):
                #Tm = lc.getmelt_anzellini(chiS[i],P1[i],param,0)
                Tm = lc.getCoreLiquidus(chi_li[i],chi_Si_icb,P1[i],param,0)
                Tms.append(Tm)
                if abs(T1[i]-Tm)<1e-8:
                    zones[i]=1  
                    
            if os.path.isdir(outputpath):
                print(outputpath)
            else:
                os.mkdir(outputpath)
                
            name = outputpath + str(round(ricb0/1000,1))+'_{:03d}'.format(k)+'.txt'
            output = np.dstack((r/1e3,rho1,P1/1e9,T1,chi_li,zones))[0]
            np.savetxt(name,output,fmt='%.3f %.3f %.3f %.3f %.3f %i',
                header = 'Time: '+str(round(Gyr,2))+' Gyr \n Radius [km] # Density [kg/m3] # Pressure [GPa] # Temperature [K] # Light Element Content [wt.%] # Snow Zone')        
        vis.gif_writer(directory+'/')
    print()
    print('--------------------------')
    print()
print('done')

