# Global parameters for both.
#20220302. Created to host constants used by the model.
chi_Si_icb = 0.05 # Si % wt. Used in the 'S+Si' scenario.
outputpath = './Model_Si%wt_'+str(chi_Si_icb) + '/' # path to host output figures
ice = 300 # inner core extension for plots in km.
path_to_present_day_models = '../v11.1-present/code/margot/Fe-S-Si/Si%wt_' + str(chi_Si_icb) + '/'
path_to_output = outputpath + 'fig/'

MFeS = (55.845+32.065)
MFeSi = (55.845+28.08)
MFe = 55.845
