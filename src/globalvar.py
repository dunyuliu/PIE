# Global parameters for both the present_day and evolution model.

# Main adjustables.
#model_mode = 'e' # 'e'/'p', that will switch between evolution/present_day models.
model_mode = input("model_mode (e, p, or plot) = ") # allows user to input the type of model (present or evolution OR make contour plots) in terminal -- added 6/23/2022
#chi_Si_icb = 0.01 # Si % wt. Used in the 'S+Si' two light element scenario.
chi_Si_icb = float(input("chi_Si_icb = ")) # allows user to input chi_Si_icb value in terminal -- added 6/16/2022
dr = 50e3 # radius increment in meters for the present_day model.
#mod_name = input("mod_name (margot or genova) = ") # allows user to customize MOI value used -- added 6/27/2022
mod_name = 'margot' # 'margot' or 'genova'
mod_li_el = 'Si' # light element combination ('S', 'Si', 'S+Si') -- added 7/12/2022

# Paths for the present day model.
model_path = './' + mod_name + '_' + mod_li_el
present_output_path = model_path + '/results_present_day_Model_Si%wt_'+str(chi_Si_icb) # Root path to data and figures by the present day model.
present_figure_path = present_output_path + '_fig/' # Path to figures by the present day model.
present_data_path = present_output_path + '_data/' # Path to data by the present day model.
ice = 300 # inner core extension for plots in km.

# Paths for the evolution model.
evolution_output_path = './TEST_results_evolution_Model_Si%wt_'+str(chi_Si_icb)  # Root path to data and figures by the evolution model.
path_to_present_day_models = present_data_path # Path to the output of the data created by the present day model. 
evolution_figure_path = evolution_output_path + '_fig/' # Path to figures by the evolution model.
evolution_data_path = evolution_output_path + '_data/' # Path to data by the evolution model.

# Paths for csv files that contain df variables from drivere.py and are used for making the contour plots, as well as the contour plots -- added 6/27/2022
contour_plotting_path = './contour_plotting_' + mod_name + '_' + mod_li_el
csvfiles_path = contour_plotting_path + '/csvfiles'
presentday_data_filename = '/present_day_' + mod_name + '_' + str(chi_Si_icb) + '.csv'
compiled_data_file = contour_plotting_path + '/compiled_presentday_data' + '.csv'
contourplot_file = contour_plotting_path + '/plot_' + mod_name + '_'
presentday_columns = ['chi_Si_icb', 'rhom', 'mass', 'moi', 'cmc', 'Picb', 'Tcmb', 'isnow', 'isnowcmb', 'chi_li_in', 'Pcmb', 'chi_li_eut_icb', 'chi_li_eut_cmb', 'ricb', 'rcmb', 'core_mass', 'chi_li_icb']
contourcond = 'Tcmb'

# Paths for csv file(s) and figure(s) that contain information on the snow zone bounds and inner core radius as a function of cmb temperature -- added 6/27/2022
radii_vs_cmbtemp_path = './radii_cmbtemp_plotting_'+str(chi_Si_icb)
csv_radii_vs_cmbtemp_filename = '/radii_cmbtemp_data'
columns_radvtemp = ['chi_Si_icb', 'present day icr', 'cmb temp', 'inner core radius', 'lb radius sz1', 'ub radius sz1', 'lb radius sz2', 'ub radius sz2', 'lb radius sz3', 'ub radius sz3', 'cmb radius']
radii_list = []

# Constants
MFeS = (55.845+32.065)
MFeSi = (55.845+28.08)
MFe = 55.845

# For Newton solver
xtol=1.e-6 # tol
ftol=1.e-6
maxit=12 # maximum number of iterations
