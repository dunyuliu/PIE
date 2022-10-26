import numpy as np
import shootp as lc
import glob,os,sys
from globalvar import *
import visualization_present as vis
import pandas as pd
import csv # added 6/30/2022

def driverp(param, rs):
    # Initiate
    
    scale       = param['scale']
    rhomean     = param['rhomean']
    rm          = param['rm']
    v0          = param['v0'] # initial guess
    rhocr       = param['rhocr']
    rh          = param['rh']
    ricb        = rs/param['scale']['a'] #non-dimensional
    cmb_radius  = np.zeros(len(ricb))
    cmb_temperature  = np.zeros(len(ricb))
    core_sulfur = np.zeros(len(ricb))
    icb_sulfur  = np.zeros(len(ricb))
    mantle_density   = np.zeros(len(ricb))

    for k in range(len(ricb)):
        #param['CMR2'] = mois[moi_index]
        #k = 0
        #try:
        # for a certain inner core radius, normalized, ricb[k] in rs, rhocr (crust thickness), rh (radius of crust-mantle boundary),
        # and initial guesses v0, try to solve for v.
        # The Newton method calls J_mercmodel, which calculates the Jacobian and f of the system given initial v0 guesses.
        # J_mercmodel calls shoot_mercmodel to build J and f. 
        
        v             = lc.mynewtonSys('J_mercmodel', v0, [ricb[k],rhocr,rh,param,scale], xtol=xtol, ftol=ftol, maxit=maxit, verbose=False)
    
        if v is None: break
	
	# Set initial guess for next as previous solution.
        v0=v 
      
        # final solution
        [f,r,yy,fout] = lc.shoot_mercmodel(v,ricb[k],rhocr,rh,param,scale)
        nr=len(r)
        #output: r= radial points of integration (non-dimensional)
        #yy(:,0) = pressure vs radius (non-dimensional)
        #yy(:,1) = g vs radius (non-dimensional)
        #yy(:,2) = temperature vs radius (non-dimensional)
        #yy(:,3) = adiabatic temperature vs radius (non-dimensional)
        #yy(:,4) = density vs radius (non-dimensional)
        #yy(:,5) = chi_li vs radius (non-dimensional)

        # if param['li_el'] == 'S' or 'S+Si', chi_li is S;
        # if param['li_el'] == 'Si', chi_li is Si;
        #fout(1) = P at icb (dimensional)
        #fout(2) = T at cmb (dimensional)
        #fout(3) = Cm/C
        #fout(4) = C/MR^2
        #fout(5) = xi
        #fout(6) = k2
        #fout(7) = isnow  (0,1,2 = no, layer, deep snow)
        #fout(8) = isnowcmb  (0,1 = snow at CMB (no,yes))
        #fout(9) = chi_li_in (initial sulfur content in core)
        #fout(10)= gradTa (adiabatic temp gradient at CMB)      
        # re-scale key results as a function of radius
        r          = scale['a']*r # radius
        P1         = scale['P']*yy[0] # pressure 
        g1         = scale['ga']*yy[1] # g
        T1         = scale['T']*yy[2] # temperature
        Tad        = scale['T']*yy[3] # adiabatic temperature
        rho1       = rhomean*yy[4] # density
        chi_li     = yy[5] # chi light element vs radius
        
        if chi_li.any()<0: break # if light element is negative, say sulfer, break the code.

        rhom       = v[3]*rhomean
        chi_li_icb = v[4]
        chi_li_cmb = chi_li[-1]
        rcmb       = r[-1]
    
        r_2        = np.append(r,[rh*scale['a'],rm])# total radius profile in meters 	
        rho1_2     = np.append(rho1,[rhom,rhocr]) # total density profile from center to surface.
        moi        = lc.get_moi(r_2,rho1_2,rhomean) # compute moment of inertia?
        ccc        = lc.get_ccc(r_2,rho1_2,rhomean) 
        cmc        = 1-ccc/moi
        mass       = lc.get_mass_norm(r_2,rho1_2,rhomean)
        core_mass  = lc.get_mass_core(r,rho1)
    
        Picb       = fout[0] # P at icb
        Tcmb       = fout[1] # T at cmb 
        isnow      = fout[2] # (0,1,2 = no, layer, deep snow)
        isnowcmb   = fout[3] #isnowcmb  (0,1 = snow at CMB (no,yes))
        chi_li_in  = fout[4] #initial sulfur content in core
        
        icb_sulfur[k]     = chi_li_icb
        core_sulfur[k]    = chi_li_in
        mantle_density[k] = rhom

        print('ricb\     trcmb\      trcmb\     tx\       tTcmb\      trhoM\      tMOI')
        print(1e-3*rs[k],'\t',1.e-3*rcmb,'\t',100*chi_li_in,'\t',Tcmb,'\t',rhom,'\t',moi,'\t',ccc)

        cmb_temperature[k] = Tcmb
        cmb_radius[k]      = r[-1]
            
        vis.plot_isnow(ricb[k]*scale['a'],r,rh*scale['a'],rm,T1,P1,chi_li,rho1,chi_li_in,moi,cmc,mass,k,param)
         
        if chi_li.any()<0: break # if light element is negative, say sulfer, break the code.
    
        Pcmb=P1[-1]
        chi_li_eut_icb=0.11+0.187*np.exp(-0.065*Picb*1e-9)
        chi_li_eut_cmb=0.11+0.187*np.exp(-0.065*Pcmb*1e-9)
      
        
        # SAVE DATA
        if not os.path.isdir(model_path): # added 7/12/2022 when needing to specify li combination and geodetic constraints
            os.mkdir(model_path)
        root = present_data_path
        if not os.path.isdir(root):
            #print(present_figure_path)
        #else:
            os.mkdir(root)
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
        # column for chi_Si_icb added 6/30/2022
        df = pd.DataFrame({'chi_Si_icb': [chi_Si_icb], 'rhom': [rhom], 'mass': [mass], 'moi': [moi], 'cmc': [cmc],
                           'Picb': [Picb], 'Tcmb': [Tcmb], 'isnow': [isnow],
                           'isnowcmb': [isnowcmb], 'chi_li_in': [chi_li_in], 
                           'Pcmb': [Pcmb], 'chi_li_eut_icb': [chi_li_eut_icb],
                           'chi_li_eut_cmb': [chi_li_eut_cmb], 'ricb':rs[k], 'rcmb':[rcmb],
                           'core_mass': [core_mass], 'chi_li_icb': [chi_li_icb]})
        # append dataframe to csv containing present day model data for contour plot -- added 6/30/2022
        presentday_data = open(csvfiles_path + presentday_data_filename, 'a')
        writer = csv.writer(presentday_data)
        writer.writerow(df.iloc[0,:])
        presentday_data.close()
        
        df.to_hdf(root+str(round(rs[k]/1000,0))+'_data.h5', key='misc', mode='a') 
        #"""
        
        #cmb_radius_moi[moi_index] = rcmb
        print('--------------------------')
        
   
    #data = {'is':icb_sulfur[0:k], 'cs':core_sulfur[0:k], 'cr':cmb_radius[0:k],
    #        'ct':cmb_temperature[0:k], 'md':mantle_density[0:k], 'rs':rs[0:k]}

    #np.save('./results/'+param['name']+'.npy',data)
