#! /usr/bin/env python3

import sys
n = len(sys.argv)
print(n)
if n!=6 and n!=7:
    print('!!!')
    print('Error! Please type in CMR2, CMC, S/Si/S+Si, Steinbrugge/Edmund, chi_Si_icb/none')
    print('!!!')
# Global parameters for both the present_day and evolution model.
# Main adjustables.
#model_mode = 'e' # 'e'/'p', that will switch between evolution/present_day models.
code_mode        = sys.argv[1] #input("code_mode (e, p, or plot) = ") # allows user to input the type of model (present or evolution OR make contour plots) in terminal -- added 6/23/2022
CMR2             = float(sys.argv[2]) #'margot' # 'margot' or 'genova'
CMC              = float(sys.argv[3]) # CMC value.
#CMR2             = 'genova'
light_element    = sys.argv[4] #'S+Si' # light element combination ('S', 'Si', 'S+Si') -- added 7/12/2022
liquidus_eq      = sys.argv[5] #'Steinbruegge' # Steinbruegge for Steinbruegge2020 or Edmund for Edmund2022.
#liquidus_eq    = 'Edmund'

if light_element == 'S+Si' and code_mode!='plot':
    chi_Si_icb   = float(sys.argv[6]) #float(input("chi_Si_icb = ")) # allows user to input chi_Si_icb value in terminal -- added 6/16/2022
else:
    chi_Si_icb   = 0.0

dr = 50e3 # radius increment in meters for the present_day model.
#CMR2 = input("CMR2 (margot or genova) = ") # allows user to customize MOI value used -- added 6/27/2022

max_Si_Steinbruegge2020 = 0.15 # Maximum Si%wt for calculating liquidus temperature based on Steinbruegge et al. (2020). Shouldn't be exceeded. 
max_Si_Edmund2022       = 0.12 # Maximum Si%wt for calculating liquidus temperature based on Edmund et al. (2022). Shouldn't be exceeded. 
# Paths for the present day model.
#model_path              = './CMR2_' + str(round(CMR2,4)) + '_CMC_' + str(round(CMC,4)) + '_' + light_element + '_' + liquidus_eq + '/'
model_path              = './results/CMR2_'+"{:.17f}".format(CMR2)+'_CMC_'+"{:.17f}".format(CMC)+'_'+light_element+'_'+liquidus_eq+'/'
#present_output_path     = model_path + model0 + 'present_Si%wt_'+str(chi_Si_icb) # Root path to data and figures by the present day model.
presentFigureName     = model_path + 'FigSi%wt'+"{:.2f}".format(chi_Si_icb)+'_' # Path to figures by the present day model.
presentDataName       = model_path + 'DataSi%wt'+"{:.2f}".format(chi_Si_icb)+'_' # Path to data by the present day model.
ice                     = 300 # inner core extension for plots in km.

# Paths for the evolution model.
evolution_output_path       = './TEST_results_evolution_Model_Si%wt_'+str(round(chi_Si_icb,3))  # Root path to data and figures by the evolution model.
path_to_present_day_models  = model_path  # Path to the output of the data created by the present day model. 
evolution_figure_path       = evolution_output_path + '_fig/' # Path to figures by the evolution model.
evolution_data_path         = evolution_output_path + '_data/' # Path to data by the evolution model.

# Paths for csv files that contain df variables from drivere.py and are used for making the contour plots, as well as the contour plots -- added 6/27/2022
contour_plotting_path       = model_path #'./contour_plotting_' + CMR2 + '_' + light_element
csvfiles_path               = model_path
#presentday_data_filename    = 'present_day_' + str(round(CMR2,4)) + '_' + str(round(CMC,4)) + '_'+ str(round(chi_Si_icb,3)) + '.csv'
pMetaDataFileName           = 'pMetaData_'+"{:.2f}".format(chi_Si_icb)+'.csv'
compiled_data_file          = contour_plotting_path + '/compiled_presentday_data' + '.csv'
#contourplot_file            = 'plot_' + str(round(CMR2,4)) + '_CMC_' + str(round(CMC,4)) + '_' + light_element + '_' + liquidus_eq
presentday_columns          = ['chi_Si_icb', 'rhom', 'mass', 'moi', 'cmc', 'Picb', 'Tcmb', 'isnow', 'isnowcmb', 'chi_li_in', 'chi_S_bulk', 'Pcmb', 'chi_li_eut_icb', 'chi_li_eut_cmb', 'ricb', 'rcmb', 'core_mass', 'chi_li_icb', 'error_code']
contourcond                 = 'isnow'

# Paths for csv file(s) and figure(s) that contain information on the snow zone bounds and inner core radius as a function of cmb temperature -- added 6/27/2022
radii_vs_cmbtemp_path       = './radii_cmbtemp_plotting_'+str(chi_Si_icb)
csv_radii_vs_cmbtemp_filename = '/radii_cmbtemp_data'
columns_radvtemp            = ['chi_Si_icb', 'present day icr', 'cmb temp', 'inner core radius', 'lb radius sz1', 'ub radius sz1', 'lb radius sz2', 'ub radius sz2', 'lb radius sz3', 'ub radius sz3', 'cmb radius']
radii_list                  = []

# Constants
MFeS                        = (55.845+32.065)
MFeSi                       = (55.845+28.08)
MFe                         = 55.845

# For Newton solver
xtol                        = 1.e-6 # tol
ftol                        = 1.e-6
maxit                       = 12 # maximum number of iterations
