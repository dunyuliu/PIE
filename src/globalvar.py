# Global parameters for both the present_day and evolution model.

# Main adjustables.
chi_Si_icb = 0.05 # Si % wt. Used in the 'S+Si' two light element scenario.
dr = 50e3 # radius increment in meters for the present_day model.

# Paths for the present day model.
present_output_path = './results_present_day_Model_Si%wt_'+str(chi_Si_icb) # Root path to data and figures by the present day model.
present_figure_path = present_output_path + '_fig/' # Path to figures by the present day model.
present_data_path = present_output_path + '_data/' # Path to data by the present day model.
ice = 300 # inner core extension for plots in km.

# Paths for the evolution model.
evolution_output_path = './results_evolution_Model_Si%wt_'+str(chi_Si_icb)  # Root path to data and figures by the evolution model.
path_to_present_day_models = present_data_path # Path to the output of the data created by the present day model. 
evolution_figure_path = evolution_output_path + '_fig/' # Path to figures by the evolution model.
evolution_data_path = evolution_output_path + '_data/' # Path to data by the evolution model.

# Constants
MFeS = (55.845+32.065)
MFeSi = (55.845+28.08)
MFe = 55.845
