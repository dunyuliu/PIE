#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug 29 16:05:03 2019
@author: gregor
Modified by dliu since 20220203.

presentDay.py is the main code that calls
    - globalMercury.py, for global variables,  
    - libCore.py,
    - coreEos.py,
    - model_evaluate.py,
    - visualization.py,
    - and misc.py (not used functions). 
"""
"""
% Constructs interior model of mercury.
% Here, not only we constrain models to satisfy mean density,
% we also constrain the models to satisfy specific values of 
% Cm/C and C/Mr^2
%
% Here we impose that Tm = Ticb, with snow scenario
"""
import numpy as np
import libCore_present as lc
import visualization_present as vis
import matplotlib.pyplot as plt
import coreEos as eos
from scipy.constants import G
import pandas as pd
import matplotlib.patches as mpatches
import matplotlib
import glob,os,sys
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
                                deltaT=5.9221767911635,kappa=1.4,
                                gamma0=1.3,q=0)

liquidFeSi=eos.eosAndersonGrueneisen(M0=MFeSi,p0=1E-5,T0=1723,
                                 V0=16.5839,alpha0=17.6525e-5,KT0=69.0074,
                                 KTP0=7.76007,deltaT=4.07505,kappa=0.56,
                                 gamma0=1.61986,q=0)


model_generic = {'rm':2439360.0,
         'GM':22031.86E+9,
         'c22':0.804151E-05,
         'CmC':0,
         'CMR2':0,
         'MFe':MFe,
         'MS':32.065,
         'MSi':28.08,
         'MFeS':MFeS,
         'MFeSi':(55.845+28.08),
         'lFe':liquidFe,
         'lFeS':liquidFeS,
         'lFeSi':liquidFeSi,
         'fccFe':fccFe,
         'li_el':'None',
         'name':'replace_me'}


# Margot Fe-S-Si models
margot_fessi = model_generic.copy()
margot_fessi['CMR2'] = 0.346
margot_fessi['CmC'] = 0.148/margot_fessi['CMR2']
margot_fessi['li_el'] = 'S+Si'
margot_fessi['name'] = 'margot/Fe-S-Si'
# Margot  +1 sigma
margot_fessi_p1sigma = margot_fessi.copy()
margot_fessi_p1sigma['name'] = 'margot/Fe-S-Si+1sigma'
margot_fessi_p1sigma['CMR2'] = 0.346+0.014
margot_fessi_p1sigma['CmC'] = 0.148/(0.346+0.014)
# Margot  -1 sigma
margot_fessi_m1sigma = margot_fessi.copy()
margot_fessi_m1sigma['name'] = 'margot/Fe-S-Si-1sigma'
margot_fessi_m1sigma['CMR2'] = 0.346-0.014
margot_fessi_m1sigma['CmC'] = 0.148/(0.346-0.014)


model_cases = [margot_fessi]

for param in model_cases: 
    M = param['GM']/G
    rm = param['rm']
    #Average density
    rhomean = 3*M/(4*np.pi*rm**3)
    # scales
    scale = {'a':rm,
             'ga':M*G/rm**2,
             'P':rhomean*rm*M*G/rm**2,
             'T':1800}
    
    # build model from shooting method, using multi-directional Newton method 
    # for each iteration
    xtol=1.e-5
    ftol=1.e-5
    maxit=6
    
    # crustal density and thickness
    rhocr=2974
    hcr=26e3
    #rhocr=2500.0
    #hcr=100e3
    
    rh=(rm-hcr)/scale['a'] # radius of crust-mantle boundary
    
   
    # variables to solve for:
    # 1) P at r=0
    # 2) T at r=0
    # 3) cmb radius
    # 4) rhom
    # 5) chi_li
    
    
    v0=[0.8,1.0,0.8,0.7,0.05] # initial guesses
    
    # Parameterize by inner core radius
    rs=np.arange(1e1, 2e6, dr)    # value for C/MR2=0.346
    #rs=np.array([1180e3])
    ricb=rs/scale['a']  #non-dimensional
    
    cmb_radius = np.zeros(len(rs))
    cmb_temperature = np.zeros(len(rs))
    core_sulfur = np.zeros(len(rs))
    icb_sulfur = np.zeros(len(rs))
    mantle_density = np.zeros(len(rs))
 
    #mois = np.linspace(0.330,0.335,10)
    #cmb_radius_moi = np.zeros(len(mois))   
    
    for k in range(len(rs)):
        #param['CMR2'] = mois[moi_index]
        #k = 0
        #try:
        # for a certain inner core radius, normalized, ricb[k] in rs, rhocr (crust thickness), rh (radius of crust-mantle boundary),
        # and initial guesses v0, try to solve for v.
        # The Newton method calls J_mercmodel, which calculates the Jacobian and f of the system given initial v0 guesses.
        # J_mercmodel calls shoot_mercmodel to build J and f. 
        
        v = lc.mynewtonSys('J_mercmodel',v0,
                           [ricb[k],rhocr,rh,param,scale],
                           xtol=xtol, ftol=ftol, maxit=maxit, verbose=True)
        #except:
        #    print('Aborted Newton run')
        #    v = None
    
        if v is None: break
        v0=v # initial guess for next is taken as previous solution.
      
        # final solution
        [f,r,yy,fout] = lc.shoot_mercmodel(v,ricb[k],rhocr,rh,param,scale)
        nr=len(r)
        
        # re-scale
        r=scale['a']*r
        P1=scale['P']*yy[0]
        g1=scale['ga']*yy[1]
        T1=scale['T']*yy[2]
        Tad=scale['T']*yy[3]
        rho1=rhomean*yy[4]
        chi_li=yy[5]
        
        #if chi_li<0: break # if light element is negative, say sulfer, break the code.

        rhom=v[3]*rhomean
        chi_li_icb=v[4]
        chi_licmb=chi_li[-1]
        rcmb=r[-1]
    
        r_2=np.append(r,[rh*scale['a'],rm])      
        rho1_2=np.append(rho1,[rhom,rhocr])
        moi = lc.get_moi(r_2,rho1_2,rhomean)
        ccc = lc.get_ccc(r_2,rho1_2,rhomean)
        cmc = 1-ccc/moi
        mass = lc.get_mass_norm(r_2,rho1_2,rhomean)
        core_mass = lc.get_mass_core(r,rho1)
    
        Picb=fout[0]
        Tcmb=fout[1]
        isnow=fout[2]
        isnowcmb=fout[3]
        chi_liin=fout[4]
        
        icb_sulfur[k] = chi_li_icb
        core_sulfur[k] = chi_liin
        mantle_density[k] = rhom
        print(rhom)
        cmb_temperature[k] = Tcmb
        cmb_radius[k] = r[-1]
            
        vis.plot_isnow(rs[k],r,rh*scale['a'],rm,T1,P1,chi_li,rho1,
                       chi_liin,moi,cmc,mass,k,param)
         
        if chi_li.any()<0: break # if light element is negative, say sulfer, break the code.
    
        Pcmb=P1[-1]
        chi_lieuticb=0.11+0.187*np.exp(-0.065*Picb*1e-9)
        chi_lieutcmb=0.11+0.187*np.exp(-0.065*Pcmb*1e-9)
      
        
        # SAVE DATA
        #root = '/Users/gregor/Projects/Evolution of Mercury/models/paper/'+param['name']+'/'
        root = present_data_path
        if os.path.isdir(root):
            print(root)
        else:
            os.makedirs(root)
        out = pd.Series(r)
        out.to_hdf(root+str(round(rs[k]/1000,0))+'_data.h5', key='r')   
        out = pd.Series(rho1)
        out.to_hdf(root+str(round(rs[k]/1000,0))+'_data.h5', key='rho')
        out = pd.Series(T1)
        out.to_hdf(root+str(round(rs[k]/1000,0))+'_data.h5', key='T')
        out = pd.Series(P1)
        out.to_hdf(root+str(round(rs[k]/1000,0))+'_data.h5', key='P')
        out = pd.Series(g1)
        out.to_hdf(root+str(round(rs[k]/1000,0))+'_data.h5', key='g')
        out = pd.Series(Tad)
        out.to_hdf(root+str(round(rs[k]/1000,0))+'_data.h5', key='Tad')
        out = pd.Series(chi_li)
        out.to_hdf(root+str(round(rs[k]/1000,0))+'_data.h5', key='chi_li')
    
        #"""
        df = pd.DataFrame({'rhom': [rhom], 'mass': [mass], 'moi': [moi], 'cmc': [cmc],
                           'Picb': [Picb], 'Tcmb': [Tcmb], 'isnow': [isnow],
                           'isnowcmb': [isnowcmb], 'chi_liin': [chi_liin], 
                           'Pcmb': [Pcmb], 'chi_lieuticb': [chi_lieuticb],
                           'chi_lieutcmb': [chi_lieutcmb], 'ricb':rs[k], 'rcmb':[rcmb],
                           'core_mass': [core_mass], 'chi_li_icb': [chi_li_icb]})
        df.to_hdf(root+str(round(rs[k]/1000,0))+'_data.h5', key='misc', mode='a')
        #"""
        
        #cmb_radius_moi[moi_index] = rcmb
        print('--------------------------')
        
   
    #data = {'is':icb_sulfur[0:k], 'cs':core_sulfur[0:k], 'cr':cmb_radius[0:k],
    #        'ct':cmb_temperature[0:k], 'md':mantle_density[0:k], 'rs':rs[0:k]}

    #np.save('/Users/gregor/Projects/Evolution of Mercury/models/paper/'+param['name']+'.npy',data)

print('Done')


for lel in ['sulfur','silicon']:
    font = {'family':'normal','size':16}
    matplotlib.rc('font', **font)

    data1 = np.load('/Users/gregor/Projects/Evolution of Mercury/models/paper/genova/'+lel+'.npy',allow_pickle=True).item()
    data1a = np.load('/Users/gregor/Projects/Evolution of Mercury/models/paper/genova/'+lel+'-1sigma.npy',allow_pickle=True).item()
    data1b = np.load('/Users/gregor/Projects/Evolution of Mercury/models/paper/genova/'+lel+'+1sigma.npy',allow_pickle=True).item()
    data2 = np.load('/Users/gregor/Projects/Evolution of Mercury/models/paper/margot/'+lel+'.npy',allow_pickle=True).item()
    data2a = np.load('/Users/gregor/Projects/Evolution of Mercury/models/paper/margot/'+lel+'-1sigma.npy',allow_pickle=True).item()
    data2b = np.load('/Users/gregor/Projects/Evolution of Mercury/models/paper/margot/'+lel+'+1sigma.npy',allow_pickle=True).item()
    #data3 = np.load('/Users/gregor/Projects/Evolution of Mercury/models/paper/genova/'+lel+'_margot_cmc.npy',allow_pickle=True).item()
        
    fig,ax = plt.subplots(2,2,figsize=(15,7))
    fig.subplots_adjust(wspace=0.35)

    """
    ax[0,0].plot(np.array(data['rs'])/1000,np.array(data['is']*100,lw=3,color='blue')
    ax[0,0].plot(np.array(data2['rs'])/1000,np.array(data2['is']*100,lw=3,color='red')
    ax[0,0].plot(np.array(data3['rs'])/1000,np.array(data3['is']*100,lw=3,color='black')
    ax[0,0].set_xlabel('ICB Radius [km]')
    ax[0,0].set_ylabel('ICB Si [wt.%]')
    """
    
    ax[0,0].plot(np.array(data1['rs'])/1000,np.array(data1['cr'])/1000,lw=3,color='blue')
    ax[0,0].plot(np.array(data1a['rs'])/1000,np.array(data1a['cr'])/1000,lw=2,ls='--',color='blue')
    ax[0,0].plot(np.array(data1b['rs'])/1000,np.array(data1b['cr'])/1000,lw=2,ls='--',color='blue')
    ax[0,0].plot(np.array(data2['rs'])/1000,np.array(data2['cr'])/1000,lw=3,color='red')
    ax[0,0].plot(np.array(data2a['rs'])/1000,np.array(data2a['cr'])/1000,lw=2,ls='--',color='red')
    ax[0,0].plot(np.array(data2b['rs'])/1000,np.array(data2b['cr'])/1000,lw=2,ls='--',color='red')
    #ax[0,0].plot(np.array(data3['rs'])/1000,np.array(data3['cr'])/1000,lw=3,ls='--',color='goldenrod')
    #ax[0,0].fill_between(np.array(data1a['rs'])[0:121]/1000,np.array(data1a['cr'])[0:121]/1000,np.array(data1b['cr'])[0:121]/1000,color='lightblue')
    #ax[0,0].fill_between(np.array(data2a['rs'])[0:110]/1000,np.array(data2a['cr'])[0:110]/1000,2050,color='lightsalmon')
    
    ax[0,0].set_xlabel('ICB Radius [km]')
    ax[0,0].set_ylabel('CMB Radius [km]')
    ax[0,0].grid()
    ax[0,0].set_xlim(0, 1400)
    ax[0,0].set_ylim(1925, 2050)
    #ax[0,0].set_ylim(1950, 1980)
    
    ax[1,0].plot(np.array(data1['rs'])/1000,np.array(data1['cs'])*100,lw=3,color='blue')
    ax[1,0].plot(np.array(data1a['rs'])/1000,np.array(data1a['cs'])*100,lw=2,ls='--',color='blue')
    ax[1,0].plot(np.array(data1b['rs'])/1000,np.array(data1b['cs'])*100,lw=2,ls='--',color='blue')
    ax[1,0].plot(np.array(data2['rs'])/1000,np.array(data2['cs'])*100,lw=3,color='red')
    ax[1,0].plot(np.array(data2a['rs'])/1000,np.array(data2a['cs'])*100,lw=2,ls='--',color='red')
    ax[1,0].plot(np.array(data2b['rs'])/1000,np.array(data2b['cs'])*100,lw=2,ls='--',color='red')
    #ax[1,0].plot(np.array(data3['rs'])/1000,np.array(data3['cs'])*100,lw=3,ls='--',color='goldenrod')
    #ax[1,0].fill_between(np.array(data1s['rs'])[0:121]/1000,np.array(data1s['cs'])[0:121]*100,np.array(data2s['cs'])[0:121]*100,color='lightgray')
    ax[1,0].set_xlabel('ICB Radius [km]')
    ax[1,0].set_ylabel('Mean Lq. Core '+lel.replace('s','S')+' [wt.%]')
    ax[1,0].grid()
    ax[1,0].set_xlim(0, 1400)
    ax[1,0].set_ylim(0, 15)
    
    ax[0,1].plot(np.array(data1['rs'])/1000,np.array(data1['ct']),lw=3,color='blue')
    ax[0,1].plot(np.array(data2['rs'])/1000,np.array(data2['ct']),lw=3,color='red')
    #ax[0,1].plot(np.array(data3['rs'])/1000,np.array(data3['ct']),lw=2,color='goldenrod')
    ax[0,1].plot(np.array(data1a['rs'])/1000,np.array(data1a['ct']),lw=2,ls='--',color='blue')
    ax[0,1].plot(np.array(data1b['rs'])/1000,np.array(data1b['ct']),lw=2,ls='--',color='blue')
    ax[0,1].plot(np.array(data2a['rs'])/1000,np.array(data2a['ct']),lw=2,ls='--',color='red')
    ax[0,1].plot(np.array(data2b['rs'])/1000,np.array(data2b['ct']),lw=2,ls='--',color='red')
    ax[0,1].set_xlabel('ICB Radius [km]')
    ax[0,1].set_ylabel('CMB Temperature [K]')
    ax[0,1].grid()
    #ax[0,1].fill_between(np.array(data1s['rs'])[0:121]/1000,np.array(data1s['ct'])[0:121],np.array(data2s['ct'])[0:121],color='lightgray')
    ax[0,1].set_xlim(0, 1400)
    if lel == 'silicon': ax[0,1].set_ylim(1900, 2500)
    else: ax[0,1].set_ylim(1200, 2400)
    
    ax[1,1].plot(np.array(data1['rs'])/1000,np.array(data1['md']),lw=3,color='blue')
    ax[1,1].plot(np.array(data2['rs'])/1000,np.array(data2['md']),lw=3,color='red')
    #ax[1,1].plot(np.array(data3['rs'])/1000,np.array(data3['md']),lw=2,color='goldenrod')
    #ax[1,1].fill_between(np.array(data1s['rs'])[0:121]/1000,np.array(data1s['md'])[0:121],np.array(data2s['md'])[0:121],color='lightgray')
    ax[1,1].plot(np.array(data1a['rs'])/1000,np.array(data1a['md']),lw=2,ls='--',color='blue')
    ax[1,1].plot(np.array(data1b['rs'])/1000,np.array(data1b['md']),lw=2,ls='--',color='blue')
    ax[1,1].plot(np.array(data2a['rs'])/1000,np.array(data2a['md']),lw=2,ls='--',color='red')
    ax[1,1].plot(np.array(data2b['rs'])/1000,np.array(data2b['md']),lw=2,ls='--',color='red')
    ax[1,1].set_xlabel('ICB Radius [km]')
    ax[1,1].set_ylabel('Mantle Density [kg/m$^3$]')
    ax[1,1].grid()
    ax[1,1].set_xlim(0, 1400)
    ax[1,1].set_ylim(2800, 3450)

    font = {'family':'normal','size':12}
    matplotlib.rc('font', **font)
    colors = ["red", "blue"]
    texts = ["MoI = 0.346 (Margot et al. 2012)", "MoI = 0.333 (Genova et al. 2019)"]

    patches = [ mpatches.Patch(color=colors[i], label="{:s}".format(texts[i]) ) for i in range(len(texts)) ]
    plt.legend(handles=patches, 
              loc='lower center', 
              bbox_to_anchor=(0.5,-0.5),
              ncol=3)
    
    plt.tight_layout()
    plt.savefig('comparison_'+lel+'.pdf',dpi=300)
    plt.show()

    
    #fig,ax = plt.subplots(figsize=(20,4))

#plt.savefig('legend.pdf',dpi=300)
#plt.show()

print('done')


# REASSEMBLE DATA

for param in model_cases:
    root = '/Users/gregor/Projects/Evolution of Mercury/models/paper/'+param['name']+'/'
    files = glob.glob(root+'*.h5')
    icb_sulfur = []
    core_sulfur = []
    cmb_radius = []
    cmb_temperature = []
    mantle_density = []
    rs = []
    if not files == []:
        files = sorted(files, key=lambda i: np.int(os.path.basename(i).replace('.0_data.h5','')))
    
    for f in files:
        df = pd.read_hdf(f,'misc') 
    
        icb_sulfur.append(df['chi_li_icb'].values[0])  
        core_sulfur.append(df['chi_liin'].values[0])
        cmb_radius.append(df['rcmb'].values[0])
        cmb_temperature.append(df['Tcmb'].values[0])
        mantle_density.append(df['rhom'].values[0])    
        rs.append(df['ricb'].values[0])
    
    
    data = {'is':icb_sulfur, 'cs':core_sulfur, 'cr':cmb_radius,
            'ct':cmb_temperature, 'md':mantle_density, 'rs':rs}

    np.save('/Users/gregor/Projects/Evolution of Mercury/models/paper/'+param['name']+'.npy',data)

    
    
    
