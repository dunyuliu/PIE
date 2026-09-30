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
    core_sulfur      = np.zeros(len(ricb))
    icb_sulfur       = np.zeros(len(ricb))
    mantle_density   = np.zeros(len(ricb))
    error_code       = np.zeros(len(ricb))

    # Structured per-run solver log (PATHWAY_FORWARD.md item 15): create
    # model_path up front (main.py already does this before calling
    # driverp(), so this is normally a no-op) so every radius, including
    # the first, gets its Newton iterate history logged next to the
    # run's own pMetaData csv/h5 outputs.
    if not os.path.isdir(model_path):
        os.makedirs(model_path, exist_ok=True)
    log_path = model_path + pSolverLogFileName

    for k in range(len(ricb)):
        print('Finding solutions for inner core radius = ' + str(round(rs[k],2)) + ' ... ...')
        #param['CMR2'] = mois[moi_index]
        #k = 0
        #try:
        # for a certain inner core radius, normalized, ricb[k] in rs, rhocr (crust thickness), rh (radius of crust-mantle boundary),
        # and initial guesses v0, try to solve for v.
        # The Newton method calls J_mercmodel, which calculates the Jacobian and f of the system given initial v0 guesses.
        # J_mercmodel calls shoot_mercmodel to build J and f.

        # mynewtonSys used to return None on failure (checked by the
        # `if v is None: break` below) but actually always either
        # returns a solution or calls sys.exit() -- "v is None" could
        # never fire (docs/audits/AUDIT_2026-09-29_buglist.md B1). It
        # now raises lc.SolverError instead of exiting the process; this
        # try/except IS the fix for that dead check -- it stops the
        # sweep at the same point a maxit/singular-J failure always did,
        # but via a caught, recorded exception instead of killing the
        # whole run.
        try:
            v = lc.mynewtonSys('J_mercmodel', v0, [ricb[k],rhocr,rh,param,scale],
                                xtol=xtol, ftol=ftol, maxit=maxit, verbose=False,
                                log_path=log_path,
                                log_context={'k_radius': int(k), 'ricb_m': float(rs[k])})
        except lc.SolverError as e:
            error_code[k] = e.error_code
            lc.write_solver_log(log_path, {
                'kind': 'radius_failure', 'stage': 'mynewtonSys',
                'k_radius': int(k), 'ricb_m': float(rs[k]),
                'error_code': int(e.error_code), 'error_name': e.error_code.name,
                'message': e.message, 'context': e.context,
            })
            print('Newton solve failed at ricb=%r m: %s (%s)' %
                  (rs[k], e.error_code.name, e.message))
            break

        # Set initial guess for next as previous solution.
        v0=v

        # final solution. shoot_mercmodel can also raise lc.SolverError
        # (getk2's IndexError/non-finite result, or a SuperLU singular
        # matrix from libCore.getpotvsr -- both used to crash the whole
        # process uncaught, docs/audits/AUDIT_2026-09-29_buglist.md
        # B2/B5/A1) -- caught here the same way, so a bad radius stops
        # the sweep instead of the process.
        try:
            [f,r,yy, fout, err] = lc.shoot_mercmodel(v,ricb[k],rhocr,rh,param,scale)
        except lc.SolverError as e:
            error_code[k] = e.error_code
            lc.write_solver_log(log_path, {
                'kind': 'radius_failure', 'stage': 'shoot_mercmodel',
                'k_radius': int(k), 'ricb_m': float(rs[k]),
                'error_code': int(e.error_code), 'error_name': e.error_code.name,
                'message': e.message, 'context': e.context,
            })
            print('shoot_mercmodel failed at ricb=%r m: %s (%s)' %
                  (rs[k], e.error_code.name, e.message))
            break
        print(err)
        if err == True:
            error_code[k] = ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX

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
        #fout(7) = isnow  (0,1,2,3 = no, layers, deep snow, deep snow+layers)
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

        rhom       = v[3]*rhomean
        chi_li_icb = v[4]
        chi_li_cmb = chi_li[-1]
        rcmb       = r[-1]

        # Physical-limit check (PATHWAY_FORWARD.md item 16): the solved
        # cmb radius must lie strictly outside the requested inner-core
        # radius. Recorded only -- not fatal, not fed back into the
        # solve (that backtracking behaviour is item 17's scope) -- so
        # a converged case's numeric outputs are unaffected either way.
        if rs[k] >= rcmb:
            error_code[k] = ErrorCode.RICB_GE_RCMB
            print('ricb (%r m) >= solved rcmb (%r m): outside physical domain. '
                  'Error code %d.' % (rs[k], rcmb, ErrorCode.RICB_GE_RCMB))

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
        chi_S_bulk = fout[6]

        icb_sulfur[k]     = chi_li_icb
        core_sulfur[k]    = chi_li_in
        mantle_density[k] = rhom

        print('ricb\     trcmb\      trcmb\     tx\       tTcmb\      trhoM\      tMOI')
        print(round(1e-3*rs[k],2),'\t',round(1.e-3*rcmb,2),'\t',round(100*chi_li_in,2),'\t',round(Tcmb,2),'\t',round(rhom,2),'\t',round(moi,2),'\t',round(ccc,2))

        cmb_temperature[k] = Tcmb
        cmb_radius[k]      = r[-1]
            
        isnow = vis.plot_isnow(ricb[k]*scale['a'],r,rh*scale['a'],rm,T1,P1,chi_li,rho1,chi_li_in,moi,cmc,mass,k,param, isnow)
         
        # `chi_li.any()<0` compared a bool (.any()'s return) to 0, always
        # False (docs/audits/AUDIT_2026-09-29_buglist.md B3); this is the
        # element-wise check it was named for.
        if (chi_li<0).any():
            error_code[k] = ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX # Final light element %wt negative.
            print('Final Light element %wt solution is negative. ... ...')
            print('Error code %d. ... ...' % ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX)
            print('Label error_tag to be TRUE ... ...')
            print('Drop the model. ... ...')
            #break # if light element is negative, say sulfer, break the code.
    
        Pcmb=P1[-1]
        chi_li_eut_icb=0.11+0.187*np.exp(-0.065*Picb*1e-9)
        chi_li_eut_cmb=0.11+0.187*np.exp(-0.065*Pcmb*1e-9)
      
        
        # SAVE DATA
        if not os.path.isdir(model_path): # added 7/12/2022 when needing to specify li combination and geodetic constraints
            os.mkdir(model_path)
        #root = present_data_path
        #if not os.path.isdir(root):
            #print(present_figure_path)
        #else:
        #    os.mkdir(root)
        root = presentDataName+'R'+str(round(rs[k]/1e3,0)).zfill(6)+'.h5'
        out = pd.Series(r)
        out.to_hdf(root, key='r')   
        out = pd.Series(rho1)
        out.to_hdf(root, key='rho')
        out = pd.Series(T1)
        out.to_hdf(root, key='T')
        out = pd.Series(P1)
        out.to_hdf(root, key='P')
        out = pd.Series(g1)
        out.to_hdf(root, key='g')
        out = pd.Series(Tad)
        out.to_hdf(root, key='Tad')
        out = pd.Series(chi_li)
        out.to_hdf(root, key='chi_li')
    
        #"""
        # column for chi_Si_icb added 6/30/2022
        df = pd.DataFrame({'chi_Si_icb': [chi_Si_icb], 'rhom': [rhom], 'mass': [mass], 'moi': [moi], 'cmc': [cmc],
                           'Picb': [Picb], 'Tcmb': [Tcmb], 'isnow': [isnow],
                           'isnowcmb': [isnowcmb], 'chi_li_in': [chi_li_in], 'chi_S_bulk': [chi_S_bulk],  
                           'Pcmb': [Pcmb], 'chi_li_eut_icb': [chi_li_eut_icb],
                           'chi_li_eut_cmb': [chi_li_eut_cmb], 'ricb':rs[k], 'rcmb':[rcmb],
                           'core_mass': [core_mass], 'chi_li_icb': [chi_li_icb], 'error_code':error_code[k]})
        # append dataframe to csv containing present day model data for contour plot -- added 6/30/2022
        csvMetaData = open(csvfiles_path + pMetaDataFileName, 'a')
        writer = csv.writer(csvMetaData)
        writer.writerow(df.iloc[0,:])
        csvMetaData.close()
        
        df.to_hdf(root, key='misc', mode='a') 
        #"""
        
        #cmb_radius_moi[moi_index] = rcmb
        print('--------------------------')
