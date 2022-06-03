# Global parameters for both.
#20220302. Created to host constants used by the model.
chi_Si_icb = 0.05 # Si % wt. Used in the 'S+Si' two light element scenario.
outputpath = './Results/Model_Si%wt_'+str(chi_Si_icb) + '/' # Path to figures by the present day model.
ice = 300 # inner core extension for plots in km.
path_to_present_day_models = './present_data_output_margot/Fe-S-Si/Si%wt_' + str(chi_Si_icb) + '/' # Path to the output of the data created by the present day model. 
path_to_output = outputpath + 'fig/' # Path to figures by the evolution model.

MFeS = (55.845+32.065)
MFeSi = (55.845+28.08)
MFe = 55.845
