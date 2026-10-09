#! /usr/bin/env python3

import sys
import enum

# Global parameters for both the present_day and evolution model.
# argv parsing is an explicit function (not run at import time, which would
# crash any process that imports this module with a foreign argv, e.g.
# pytest or robust_runner.py's own CLI argv -- see parse_argv's docstring),
# called once by the real entrypoint (pie/main.py) before anything else
# imports the names it derives below.

dr = 50e3 # radius increment in meters for the present_day model.

max_Si_Steinbruegge2020 = 0.15 # Maximum Si%wt for calculating liquidus temperature based on Steinbruegge et al. (2020). Shouldn't be exceeded.
max_Si_Edmund2022       = 0.12 # Maximum Si%wt for calculating liquidus temperature based on Edmund et al. (2022). Shouldn't be exceeded.
ice                     = 300 # inner core extension for plots in km.

presentday_columns          = ['chi_Si_icb', 'rhom', 'mass', 'moi', 'cmc', 'Picb', 'Tcmb', 'isnow', 'isnowcmb', 'chi_li_in', 'chi_S_bulk', 'Pcmb', 'chi_li_eut_icb', 'chi_li_eut_cmb', 'ricb', 'rcmb', 'core_mass', 'chi_li_icb', 'error_code',
                               'start', 'newton_iters', 'resid_norm',
                               'check_solution_bounds_enabled']  # v1.3.0: appended start/newton_iters/resid_norm (format change; see README 'Outputs and error codes'). v1.8.0: appended check_solution_bounds_enabled (item 40c) -- the effective PIE_CHECK_SOLUTION_BOUNDS/PIE_BOX_CHECK_FINAL setting this run resolved to, so the box-check-on-final-iterate provenance travels with the csv instead of being invisible in the output.
contourcond                 = 'isnow'

columns_radvtemp            = ['chi_Si_icb', 'present day icr', 'cmb temp', 'inner core radius', 'lb radius sz1', 'ub radius sz1', 'lb radius sz2', 'ub radius sz2', 'lb radius sz3', 'ub radius sz3', 'cmb radius']
radii_list                  = []


def parse_argv(argv=None):
    """Parse the `main.py`/`pie p` CLI contract --
    `[prog, code_mode, CMR2, CMC, light_element, liquidus_eq, chi_Si_icb?]`
    -- and set this module's argv-derived attributes (`code_mode`, `CMR2`,
    `CMC`, `light_element`, `liquidus_eq`, `chi_Si_icb`, and everything
    derived from them: `model_path`, `presentFigureName`,
    `presentDataName`, `evolution_output_path`,
    `path_to_present_day_models`, `evolution_figure_path`,
    `evolution_data_path`, `contour_plotting_path`, `csvfiles_path`,
    `pMetaDataFileName`, `compiled_data_file`, `contourplot_file`,
    `radii_vs_cmbtemp_path`, `csv_radii_vs_cmbtemp_filename`,
    `pSolverLogFileName`).

    `argv` defaults to `sys.argv`. Called once, early, by the real
    entrypoint (`pie/main.py`, before its own `from .globalvar import
    ...`) -- NOT a module-import side effect, so importing
    `pie.globalvar` (e.g. from pytest, or from `pie/robust_runner.py`'s
    own unrelated CLI argv) no longer parses whatever argv that foreign
    process happens to have. Still raises loudly on a malformed argv
    (board rule: no silent default) -- just as an explicit call site's
    exception, not a bare import-time crash.
    """
    if argv is None:
        argv = sys.argv
    n = len(argv)
    if n != 6 and n != 7:
        raise ValueError(
            'Error! Please type in CMR2, CMC, S/Si/S+Si, Steinbrugge/Edmund, '
            f'chi_Si_icb/none (expected 6 or 7 argv entries, got {n}: {argv!r})'
        )
    code_mode        = argv[1] #input("code_mode (e, p, or plot) = ") # allows user to input the type of model (present or evolution OR make contour plots) in terminal -- added 6/23/2022
    CMR2             = float(argv[2]) #'margot' # 'margot' or 'genova'
    CMC              = float(argv[3]) # CMC value.
    light_element    = argv[4] #'S+Si' # light element combination ('S', 'Si', 'S+Si') -- added 7/12/2022
    liquidus_eq      = argv[5] #'Steinbruegge' # Steinbruegge for Steinbruegge2020 or Edmund for Edmund2022.

    if light_element == 'S+Si' and code_mode != 'plot':
        chi_Si_icb   = float(argv[6]) #float(input("chi_Si_icb = ")) # allows user to input chi_Si_icb value in terminal -- added 6/16/2022
    else:
        chi_Si_icb   = 0.0

    # Paths for the present day model.
    model_path              = './results/CMR2_'+"{:.17f}".format(CMR2)+'_CMC_'+"{:.17f}".format(CMC)+'_'+light_element+'_'+liquidus_eq+'/'
    presentFigureName     = model_path + 'FigSi%wt'+"{:.2f}".format(chi_Si_icb)+'_' # Path to figures by the present day model.
    presentDataName       = model_path + 'DataSi%wt'+"{:.2f}".format(chi_Si_icb)+'_' # Path to data by the present day model.

    # Paths for the evolution model.
    evolution_output_path       = './TEST_results_evolution_Model_Si%wt_'+str(round(chi_Si_icb,3))  # Root path to data and figures by the evolution model.
    path_to_present_day_models  = model_path  # Path to the output of the data created by the present day model.
    evolution_figure_path       = evolution_output_path + '_fig/' # Path to figures by the evolution model.
    evolution_data_path         = evolution_output_path + '_data/' # Path to data by the evolution model.

    # Paths for csv files that contain df variables from drivere.py and are used for making the contour plots, as well as the contour plots -- added 6/27/2022
    contour_plotting_path       = model_path #'./contour_plotting_' + CMR2 + '_' + light_element
    csvfiles_path               = model_path
    pMetaDataFileName           = 'pMetaData_'+"{:.2f}".format(chi_Si_icb)+'.csv'
    compiled_data_file          = contour_plotting_path + '/compiled_presentday_data' + '.csv'
    # Uses the same directory prefix as compiled_data_file above, rather
    # than a bare filename that would land in whatever cwd summaryPlot.py
    # is run from (scripts/plot/summaryPlot.py references contourplot_file).
    contourplot_file            = contour_plotting_path + '/plot_' + str(round(CMR2,4)) + '_CMC_' + str(round(CMC,4)) + '_' + light_element + '_' + liquidus_eq

    # Paths for csv file(s) and figure(s) that contain information on the snow zone bounds and inner core radius as a function of cmb temperature -- added 6/27/2022
    radii_vs_cmbtemp_path       = './radii_cmbtemp_plotting_'+str(chi_Si_icb)
    csv_radii_vs_cmbtemp_filename = '/radii_cmbtemp_data'

    pSolverLogFileName          = 'solverLog_'+"{:.2f}".format(chi_Si_icb)+'.jsonl'

    globals().update(
        code_mode=code_mode, CMR2=CMR2, CMC=CMC, light_element=light_element,
        liquidus_eq=liquidus_eq, chi_Si_icb=chi_Si_icb,
        model_path=model_path, presentFigureName=presentFigureName,
        presentDataName=presentDataName,
        evolution_output_path=evolution_output_path,
        path_to_present_day_models=path_to_present_day_models,
        evolution_figure_path=evolution_figure_path,
        evolution_data_path=evolution_data_path,
        contour_plotting_path=contour_plotting_path,
        csvfiles_path=csvfiles_path, pMetaDataFileName=pMetaDataFileName,
        compiled_data_file=compiled_data_file,
        contourplot_file=contourplot_file,
        radii_vs_cmbtemp_path=radii_vs_cmbtemp_path,
        csv_radii_vs_cmbtemp_filename=csv_radii_vs_cmbtemp_filename,
        pSolverLogFileName=pSolverLogFileName,
    )

# Constants
MFeS                        = (55.845+32.065)
MFeSi                       = (55.845+28.08)
MFe                         = 55.845

# For Newton solver
xtol                        = 1.e-6 # tol
ftol                        = 1.e-6
maxit                       = 12 # maximum number of iterations

# Error-code table (PATHWAY_FORWARD.md items 15/16). One authoritative
# enum used by shootp.py/libCore.py/driverp.py instead of ad hoc ints,
# so a per-radius `error_code` (written to the pMetaData csv, unchanged
# schema) and the structured solver log (pSolverLogFileName below) agree
# on what each value means.
class ErrorCode(enum.IntEnum):
    CONVERGED                  = 0  # Newton converged within xtol/ftol
    NEWTON_MAXIT                = 1  # Newton hit maxit without meeting xtol/ftol
    SINGULAR_JACOBIAN           = 2  # det(J)==0, or J numerically singular in np.linalg.inv
    NONFINITE_SHOOT             = 3  # NaN/Inf or an uncaught IndexError/RuntimeError
                                     # (SuperLU singular matrix, getk2 index wrap-around)
                                     # while shooting/building A, rho, or g
    CHI_OUTSIDE_ADMISSIBLE_BOX  = 4  # chi_li (S or Si %wt) went negative or above the
                                     # eutectic/liquidus bound during the solve
    RICB_GE_RCMB                = 5  # inner-core radius reached/exceeded the solved cmb
                                     # radius -- outside the model's physical domain
    SI_ABOVE_LIQUIDUS_MAX       = 6  # chi_Si_icb above the liquidus table's max Si%wt --
                                     # an intentional, by-design stop, not a solver bug
    NONFINITE_ICB_DENSITY       = 7  # eosInnerCore returned a non-finite density at the
                                     # centre/ICB, so the ODE initial state y0 is non-finite
                                     # (a Newton trial iterate left the EoS domain); caught
                                     # before solve_ivp so it is a per-radius failure row,
                                     # not a process-killing ValueError

ERROR_CODE_DESCRIPTIONS = {
    ErrorCode.CONVERGED:                 "converged",
    ErrorCode.NEWTON_MAXIT:              "Newton solver: maxit reached without convergence",
    ErrorCode.SINGULAR_JACOBIAN:         "Newton solver: singular Jacobian",
    ErrorCode.NONFINITE_SHOOT:           "shoot: non-finite result or uncaught exception (A/rho/g)",
    ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX:"chi_li outside admissible box (negative or > eutectic)",
    ErrorCode.RICB_GE_RCMB:              "ricb >= rcmb: outside physical domain",
    ErrorCode.SI_ABOVE_LIQUIDUS_MAX:     "chi_Si_icb above liquidus max Si%wt (by design)",
    ErrorCode.NONFINITE_ICB_DENSITY:     "shoot: non-finite ICB density from eosInnerCore (y0 non-finite)",
}

# Structured per-run solver log: one JSONL file per (CMR2, CMC,
# light_element, liquidus_eq, chi_Si_icb) run, next to the run's own
# pMetaData csv/h5 outputs (same model_path, same chi_Si_icb-suffixed
# naming convention as pMetaDataFileName/presentDataName above). One JSON
# object per line: either a per-radius Newton solve record (iterate
# history: v, |f|, |dx|, det(J)) or a failure-context record (non-finite
# counts in A/rho/g, chi_li vs eutectic/admissible box) -- see
# libCore.py's write_solver_log.
# (pSolverLogFileName itself is argv-derived -- computed and set by
# parse_argv() above, not here.)
