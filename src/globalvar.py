# Global parameters for both.
#20220302. Created to host constants used by the model.
chi_Si_icb = 0.05 # Si % wt. Used in the 'S+Si' two light element scenario.
present_output_path = './Results/present_day/Model_Si%wt_'+str(chi_Si_icb) + '/' # Root path to data and figures by the present day model.
present_figure_path = present_output_path + 'fig/' # Path to figures by the present day model.
present_data_path = present_output_path + 'data/' # Path to data by the present day model.
ice = 300 # inner core extension for plots in km.

evolution_output_path = './Results/evolution/Model_Si%wt_'+str(chi_Si_icb) + '/' # Root path to data and figures by the evolution model.
path_to_present_data_for_evolution = present_data_path # Path to the output of the data created by the present day model. 
evolution_figure_path = evolution_output_path + 'fig/' # Path to figures by the evolution model.

MFeS = (55.845+32.065)
MFeSi = (55.845+28.08)
MFe = 55.845
