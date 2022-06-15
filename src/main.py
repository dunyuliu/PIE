#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" 
% This is the main code of Mercury interior model.
% It is part of the software Mercury_present_evolution.
% To use or distribute it, please refer to LICENSE. 
% It constructs interior model of mercury in its present day or evolves it backwards in time.

% History:
% First created on Thu Aug 29 16:05:03 2019. 
% Further modification by dliu and arivoldini since 20220203. 

% What's new?
% Here, not only we constrain models to satisfy mean density,
% we also constrain the models to satisfy specific values of 
% Cm/C and C/Mr^2
% Here we impose that Tm = Ticb, with snow scenario
"""

import numpy as np # loading numpy. 
from globalvar import * # loading global variables. 
from planet_input import * # loading planet, which produces initial model input.
from drivere import * # loading drivere, which does the main computation for evolution model.
from driverp import * # loading driverp, which does the main computation for presentDay model.

param = planet(model_mode,'margot','S+Si') # initiate list param, which contains key model information.
# function planet takes in three variables. 
# - model_mode = 'e'/'p', for evolution/present_day, defined in globalvar.
# - 'margot', to be developed
# - 'S'/'Si'/'S+Si', for Light element combinations.
if model_mode == 'p':
    # variables to solve for:
    # 1) P at r=0
    # 2) T at r=0
    # 3) cmb radius
    # 4) rhom
    # 5) chi_li
    # Parameterize by inner core radius
    rs=np.arange(1e1, 2e6, dr)    # value for C/MR2=0.346

    print('ricb\trcmb\trcmb\tx\tTcmb\trhoM\tMOI')
	#resGenova = driver(mercuryGenova, ricb)
    res = driverp(param, rs)

    print('Finish simulating model' + param['name'] + '...')    


elif model_mode == 'e':

    rm_s = param['rm'] # initial radius of the whole planet. 
    scale = param['scale'] # scales used to normalize quantities and solutions.
 
    pday_models = glob.glob(path_to_present_day_models + "*.h5") # get present day model data. 

    print(pday_models) # show the existing present day model data.
    for model in pday_models: # loop over present_day models and then use them as initials.
        init = pd.read_hdf(model, key='misc') # key 'misc' is a list of scalar quantities, which will serve as initials for the evolution models.
    
        print('Start evolving backwards in time from ',model)

        res = drivere(param, model, init) # call drivere to do computation.
    
        print('Finish simulating model' + param['name'] + '...')

print('Done simulating evolution Mercury interior model ...')


