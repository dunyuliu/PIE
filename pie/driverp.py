import numpy as np
from . import shootp as lc
import glob,os,sys
from .globalvar import ( # explicit names this file's own code uses (no star-import)
    ErrorCode, chi_Si_icb, csvfiles_path, ftol, liquidus_eq, maxit,
    max_Si_Edmund2022, max_Si_Steinbruegge2020, model_path,
    pMetaDataFileName, presentDataName, presentday_columns,
    pSolverLogFileName, xtol,
)
import pandas as pd
import csv # added 6/30/2022

def _get_vis():
    """Lazily import visualization_present and cache it
    directly in this module's own namespace dict (`globals()`), not via a
    `sys.modules[__name__]` lookup -- pielib's `import_src` helper evicts
    `sys.modules['driverp']` as a side effect of re-importing OTHER src/
    modules for a different CMR2/light_element (see tests/pielib.py),
    so a already-held reference to this module's own `globals()` is the
    only reliable self-reference here, independent of that cache state.
    """
    if 'vis' not in globals():
        util_plot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'plot')
        if util_plot_dir not in sys.path:
            sys.path.insert(0, util_plot_dir)
        import visualization_present as vis_module
        globals()['vis'] = vis_module
    return globals()['vis']


def __getattr__(name):
    """PEP 562 lazy module attribute: `vis` (visualization_present, under
    scripts/plot/) is imported only on first access to `driverp.vis` -- by driverp() itself
    (see below) or by a caller/test reaching in to monkeypatch it -- and
    cached in the module namespace exactly like a normal import, so
    behaviour when plotting actually runs is unchanged.
    """
    if name == 'vis':
        return _get_vis()
    raise AttributeError("module %r has no attribute %r" % (__name__, name))


def solve_radius(k, rs_k, ricb_k, v_last, v_cold, rhocr, rh, param, scale, log_path):
    """Newton solve at one inner-core radius with the v1.3.0 start policy.

    Warm start from v_last (the last converged solution; None before the
    first convergence, in which case the cold start is the only attempt);
    if the warm start fails with a radius-dependent error (codes 1-5) and
    the cold start v_cold differs from it, one cold start from v_cold. The
    solver log records which start produced the solution ('warm'/'cold').
    Returns (v, start). Raises the LAST SolverError when every attempt
    fails (the warm-start error is kept in its context as 'warm_start_error').
    SI_ABOVE_LIQUIDUS_MAX is re-raised immediately (by design, not
    radius-dependent).
    """
    args = [ricb_k, rhocr, rh, param, scale]
    attempts = []
    if v_last is not None:
        attempts.append(('warm', v_last))
    if v_last is None or not np.array_equal(np.asarray(v_last, dtype=float), np.asarray(v_cold, dtype=float)):
        attempts.append(('cold', list(v_cold)))
    warm_error = None
    for start, v0 in attempts:
        try:
            v = lc.mynewtonSys('J_mercmodel', v0, args,
                                xtol=xtol, ftol=ftol, maxit=maxit, verbose=False,
                                log_path=log_path,
                                log_context={'k_radius': int(k), 'ricb_m': float(rs_k), 'start': start})
            return v, start
        except lc.SolverError as e:
            e.context['start'] = start
            if e.error_code == ErrorCode.SI_ABOVE_LIQUIDUS_MAX:
                raise
            if start == 'warm':
                warm_error = e
                continue
            if warm_error is not None:
                e.context['warm_start_error'] = {'error_code': int(warm_error.error_code),
                                                 'error_name': warm_error.error_code.name,
                                                 'message': warm_error.message}
            raise
    raise warm_error


def write_failure_row(rs_k, code, start):
    """Append the csv row for a radius whose solve FAILED (v1.3.0, owner
    decision 2026-09-30): ricb, chi_Si_icb, error_code, start, newton_iters
    and resid_norm are set; every physical quantity is NaN -- never 0 or a
    stale value from the previous radius. No .h5 is written for a failed
    radius; this row is the record. Consumers must filter error_code == 0
    (README 'Outputs and error codes')."""
    row = {c: np.nan for c in presentday_columns}
    row['chi_Si_icb'] = chi_Si_icb
    row['ricb'] = rs_k
    row['error_code'] = int(code)
    row['start'] = start if start is not None else ''
    row['newton_iters'] = int(lc.last_solve_info.get('n_iterations', -1))
    row['resid_norm'] = float(lc.last_solve_info.get('normf_last', np.nan))
    row['check_solution_bounds_enabled'] = bool(lc.PIE_CHECK_SOLUTION_BOUNDS)
    with open(csvfiles_path + pMetaDataFileName, 'a') as csvMetaData:
        csv.writer(csvMetaData).writerow([row[c] for c in presentday_columns])


def driverp(param, rs):
    # Initiate

    # `_get_vis()` (rather than a bare `import visualization_present as
    # vis`) returns the same cached module object `driverp.vis` resolves
    # to from outside, so a test/caller that already monkeypatched
    # `driverp.vis` before calling driverp() sees that patch, not a fresh
    # import.
    vis = _get_vis()

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

    # Structured per-run solver log: create model_path up front (main.py
    # already does this before calling driverp(), so this is normally a
    # no-op) so every radius, including the first, gets its Newton
    # iterate history logged next to the run's own pMetaData csv/h5
    # outputs.
    if not os.path.isdir(model_path):
        os.makedirs(model_path, exist_ok=True)
    log_path = model_path + pSolverLogFileName

    # SI_ABOVE_LIQUIDUS_MAX (code 6) does not depend on the radius: checked
    # once, before the sweep. One csv row (ricb = rs[0]) records it and the
    # composition ends (owner decision 2026-09-30, point 5).
    if param['li_el'] == 'S+Si':
        si_max = max_Si_Steinbruegge2020 if liquidus_eq == 'Steinbruegge' else max_Si_Edmund2022
        if chi_Si_icb > si_max:
            lc.last_solve_info.clear()
            code = ErrorCode.SI_ABOVE_LIQUIDUS_MAX
            lc.write_solver_log(log_path, {
                'kind': 'composition_failure', 'stage': 'pre-sweep',
                'error_code': int(code), 'error_name': code.name,
                'message': 'chi_Si_icb %r exceeds the %s liquidus Si max %r (by design)' % (chi_Si_icb, liquidus_eq, si_max),
                'context': {'chi_Si_icb': chi_Si_icb, 'max_Si_allowed': si_max, 'liquidus_eq': liquidus_eq},
            })
            print('chi_Si_icb %r exceeds allowed maximum Si%%wt %r (%s): error code %d, composition ends.'
                  % (chi_Si_icb, si_max, liquidus_eq, code))
            write_failure_row(rs[0], code, None)
            return

    v_last = None                 # last converged solution (warm start)
    v_cold = list(param['v0'])    # the generic initial guess (cold start)

    for k in range(len(ricb)):
        print('Finding solutions for inner core radius = ' + str(round(rs[k],2)) + ' ... ...')
        # For a certain inner core radius, normalized, ricb[k] in rs, rhocr (crust thickness), rh (radius of crust-mantle boundary),
        # solve for v. The Newton method calls J_mercmodel, which calculates the Jacobian and f of the system given the initial v0 guesses.
        # J_mercmodel calls shoot_mercmodel to build J and f.
        #
        # Sweep policy: a failure at one radius is recorded (error_code + a
        # radius_failure record in the solver log) and the sweep continues
        # to the next radius, warm-starting from the last converged
        # solution. solve_radius tries the warm start first and, if that
        # fails, one cold start from the generic v0. Only
        # SI_ABOVE_LIQUIDUS_MAX (by design, radius-independent) ends the
        # composition.
        try:
            v, start = solve_radius(k, rs[k], ricb[k], v_last, v_cold, rhocr, rh, param, scale, log_path)
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
            write_failure_row(rs[k], error_code[k], e.context.get('start'))
            if e.error_code == ErrorCode.SI_ABOVE_LIQUIDUS_MAX:
                break
            continue

        # final solution. shoot_mercmodel can also raise lc.SolverError
        # (getk2's physical-limit / non-finite guards, or a SuperLU singular
        # matrix from libCore.getpotvsr) -- recorded the same way; the sweep
        # continues from the last converged solution.
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
            write_failure_row(rs[k], error_code[k], start)
            continue
        # Set initial guess for the next radius to this converged solution.
        v_last = v
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

        # Physical-limit check: the solved cmb radius must lie strictly
        # outside the requested inner-core radius. Recorded only -- not
        # fatal, not fed back into the solve -- so a converged case's
        # numeric outputs are unaffected either way.
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
        # False (docs/dev/audits/AUDIT_2026-09-29_buglist.md B3); this is the
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
                           'core_mass': [core_mass], 'chi_li_icb': [chi_li_icb], 'error_code':error_code[k],
                           # v1.3.0 columns: which start converged, Newton iterations, final ||f|| at the returned v
                           'start': [start], 'newton_iters': [int(lc.last_solve_info.get('n_iterations', -1))],
                           'resid_norm': [float(np.linalg.norm(f))],
                           # v1.8.0 (item 40c): effective PIE_CHECK_SOLUTION_BOUNDS/
                           # PIE_BOX_CHECK_FINAL setting this run resolved to --
                           # read from shootp's own env resolution (lc.PIE_CHECK_SOLUTION_BOUNDS),
                           # never a literal, so the column can't go stale if the
                           # resolution logic changes.
                           'check_solution_bounds_enabled': [bool(lc.PIE_CHECK_SOLUTION_BOUNDS)]})
        # append dataframe to csv containing present day model data for contour plot -- added 6/30/2022
        csvMetaData = open(csvfiles_path + pMetaDataFileName, 'a')
        writer = csv.writer(csvMetaData)
        writer.writerow(df.iloc[0,:])
        csvMetaData.close()
        
        df.to_hdf(root, key='misc', mode='a') 
        #"""
        
        #cmb_radius_moi[moi_index] = rcmb
        print('--------------------------')
