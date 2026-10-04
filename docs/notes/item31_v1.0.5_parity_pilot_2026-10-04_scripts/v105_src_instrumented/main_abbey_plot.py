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
import csv # for writing and using csv files -- added 6/27/2022
import glob,os,sys # for creating new directories -- added 6/28/2022
import pandas as pd # for reading csv files -- added 6/28/2022
import matplotlib.pyplot as plt # added 6/28/2022
import numpy as np # for help with plotting -- added 6/29/2022
import matplotlib

# Create contour plots of wt % Si and icr radius as the x and y axes
# Done outside of if statement for present day models because it exits the code in shootp.py
if model_mode == 'plot':
    plt.clf()
    plt.figure(0, figsize=(10,10))
    compiled_csv = open(compiled_data_file, 'w')
    writer = csv.writer(compiled_csv)
    writer.writerow(presentday_columns)
    compiled_csv.close()
    # Start 2D matrix of contour variable
    icr_inc = 40 # number of inner core radius increments fom 0 to X km 
    contour_matrix = np.empty((12,icr_inc)) # change from 15 to 12 wt % Si values (to account for Si going up to only 12 wt %), number of inner core radius increments
    row_index = 0
    for csvfile in os.listdir(csvfiles_path):
        if row_index < 12: # to only include data where wt % Si goes up to 12
            df_individual = pd.read_csv(csvfiles_path + '/' + csvfile)
            # Also extract data of contour variable to make into 2D matrix
            row = list(df_individual[contourcond])
            if len(row) != icr_inc:
                diff = icr_inc - len(row)
                zeros = [np.nan] * diff
                row = row + zeros
            contour_matrix[row_index, :] = np.array(row)
            # done adding row to contour matrix
            compiled_csv = open(compiled_data_file, 'a')
            df_individual.to_csv(compiled_csv, mode='a', index=False, header=False)
            compiled_csv.close()
        row_index += 1
    compiled_csv = open(compiled_data_file, 'r')
    df_compiled = pd.read_csv(compiled_csv)
    compiled_csv.close()
    # Add dataframe column with markers for snow zone/no snow zone
    # '^' = snow zone, 'o' = no snow zone   
    df_compiled['marker'] = 'o'
    for i in range(0, len(df_compiled)):
        if df_compiled.loc[i, 'isnow'] == 2:
            df_compiled.loc[i, 'marker'] = '^'
    wt_Si = np.array(df_compiled['chi_Si_icb']) * 100
    ricb = np.array(df_compiled['ricb']) / 1E+3
    icb_S = np.array(df_compiled['chi_li_icb']) * 100
    inner_S = np.array(df_compiled['chi_li_in']) * 100
    markers = np.array(df_compiled['marker'])
    sz_i = np.where(markers == '^') # used for plotting
    no_sz_i = np.where(markers == 'o') # used for plotting
    # Make axis variables and labels separately in case axes change
    xaxis = wt_Si
    yaxis = ricb
    #yaxis = inner_S
    xlabel = 'wt % Si'
    ylabel = 'Inner Core Radius [km]'
    #ylabel = 'wt % S inner core avg'
    contour_axis = np.array(df_compiled[contourcond])
    sample = contour_axis[0]
    contour_scale = int(np.log10(sample)) # get scale of contour axis values
    # Now plot
    if contourcond == 'isnow' or contourdond == 'isnowcmb':
        cmap = 'cool'
        plt.scatter(xaxis, yaxis, c=contour_axis, marker='o', s=96.0, cmap=cmap)
    else:
        minc, maxc = np.min(contour_axis), np.max(contour_axis)
        maxc = maxc + 10**(contour_scale-1) / 2
        cmap = 'gist_rainbow_r'
        plt.scatter(xaxis[sz_i], yaxis[sz_i], c=contour_axis[sz_i], marker='^', edgecolor='black', s=96.0, cmap=cmap, vmin=minc, vmax=maxc)
        plt.scatter(xaxis[no_sz_i], yaxis[no_sz_i], c=contour_axis[no_sz_i], marker='o', s=96.0, cmap=cmap, vmin=minc, vmax=maxc)
    plt.xlabel(xlabel, fontsize=20)
    plt.xlim((0,13)) # change from plt.xlim((0,16)) to account for Si going up to only 12 wt %
    plt.xticks(fontsize=15)
    plt.ylabel(ylabel, fontsize=20)
    plt.yticks(fontsize=15)
    title = mod_name.capitalize() + ' MOI -- Contouring for ' + contourcond.capitalize()
    plt.title(title, fontsize=24)
    plt.colorbar()
    plt.savefig(contourplot_file + contourcond + '_yaxis = ' + ylabel + '.tiff', dpi=300)

    # Make plot of actual grid contour + lines
    plt.clf()
    plt.figure(1, figsize=(10,10))
    xticks = np.linspace(1, 12, 12) # change from np.linspace(1, 15, 15) to account for Si going up to only 12 wt %
    yticks = np.linspace(0, 1750, icr_inc)
    #minc, maxc = np.min(contour_axis), np.max(contour_axis)
    X,Y = np.meshgrid(xticks, yticks)
    Z = np.transpose(contour_matrix)
    contouraxiscopy = np.sort(contour_axis.copy())
    levels = np.linspace(contouraxiscopy[0], contouraxiscopy[-1], 50)
    cm = plt.cm.get_cmap(cmap)
    #cp = plt.contour(xticks, yticks, Z, levels, colors='black', linestyles='dashed', linewidths=1)
    #plt.clabel(cp, inline=1, fontsize=10)
    if contourcond == 'isnow' or contourcond == 'isnowcmb':  # snow zone condition doesn't need contour scale adjusted
        cp = plt.contour(xticks, yticks, Z, levels, cmap=cm)
    else: 
        cp = plt.contourf(xticks, yticks, Z, levels, cmap=cm, vmax=maxc)
    plt.xlabel(xlabel, fontsize=15)
    plt.xticks(fontsize=10)
    plt.ylabel(ylabel, fontsize=15)
    plt.yticks(fontsize=10)
    plt.title(title, fontsize=20)
    plt.colorbar()
    plt.savefig(contourplot_file + 'contoured_for_' + contourcond + '.png', dpi=300)

    # Make figure with 4 subplots with contours of Mantle Temperature, Mantle Pressure, Mantle Density, and S concentration at inner core boundary OR
    # make figure with 6 subplots with contours for Mantle Temperature, Pressure, Density, core mass, S concentration at inner core boundary, and S 
    # concentration averaged through inner core
    # Easier visualization for putting in report/paper or poster        
    plt.rcParams['font.size']=20
    fig, ax = plt.subplots(3,2, figsize=(20,27), constrained_layout=True)

    conds = ['Tcmb', 'Pcmb', 'rhom', 'core_mass', 'chi_li_icb', 'chi_li_in']
    titles = ['CMB Temperature', 'CMB Pressure', 'Mean Mantle Density', 'Core Mass', 'S Concentration at ICB', 'Mean S Concentration in Core']

    index = 0
    for i in range(0,3):
        for j in range(0,2):
            c = np.array(df_compiled[conds[index]])
            cscale = int(np.log10(c[0]))
            minc = np.min(c)
            maxc = np.max(c) + 10**(cscale-1) / 2
            ax[i,j].scatter(xaxis[sz_i], yaxis[sz_i], c=c[sz_i], marker='^', edgecolor='black', s=96.0, cmap='gist_rainbow_r', vmin=minc, vmax=maxc)
            ax[i,j].scatter(xaxis[no_sz_i], yaxis[no_sz_i], c=c[no_sz_i], marker='o', s=96.0, cmap='gist_rainbow_r', vmin=minc, vmax=maxc)
            ax[i,j].set_xlabel(xlabel)
            ax[i,j].set_ylabel(ylabel)
            ax[i,j].set_title('Contour for '+titles[index], fontsize=30)
            norm = matplotlib.colors.Normalize(minc, maxc)
            fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap='gist_rainbow_r'), ax=ax[i,j])
            print('Min of '+titles[index] +' with Snow Zone Models: ' + str(np.min(c[sz_i])))
            print('Max of '+titles[index] +' with Snow Zone Models: ' + str(np.max(c[sz_i])))
            index += 1

    # save subplot figure
    plt.savefig(contourplot_file + 'subplots' + '_yaxis = ' + ylabel + '.png', dpi=300)

    sys.exit()   

param = planet(model_mode,mod_name,mod_li_el) # initiate list param, which contains key model information.
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
    # create csv file to store all the data from all present day models per MOI value
    if os.path.isdir(csvfiles_path):
        print(csvfiles_path)
    else:
        os.mkdir(contour_plotting_path)
        os.mkdir(csvfiles_path)
    # append columns to csv file for present day data
    presentday_data = open(csvfiles_path + presentday_data_filename, 'w')
    writer = csv.writer(presentday_data)
    writer.writerow(presentday_columns)
    presentday_data.close()
    
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
    i = 0.0 # represents present day inner core radius -- added 6/28/2022
    for model in pday_models: # loop over present_day models and then use them as initials.
        # create csv file to store radii of inner core, snow zone lower bounds, snow zone upper bounds, and cmb radius -- added 6/27/2022
        # first create directory to store files
        if os.path.isdir(radii_vs_cmbtemp_path):
            print(radii_vs_cmbtemp_path)
        else:
            os.mkdir(radii_vs_cmbtemp_path)
        csv_radii_cmbtemp = open(radii_vs_cmbtemp_path + csv_radii_vs_cmbtemp_filename + '_' + str(i) + '.csv', 'w')
        writer = csv.writer(csv_radii_cmbtemp)
        writer.writerow(columns_radvtemp)
        csv_radii_cmbtemp.close()

        init = pd.read_hdf(model, key='misc') # key 'misc' is a list of scalar quantities, which will serve as initials for the evolution models.
    
        print('Start evolving backwards in time from ',model)

        res = drivere(param, model, init, i) # call drivere to do computation.
    
        print('Finish simulating model' + param['name'] + '...')

        # make figures for each evolution model that plot radii as a function of cmb temperature
        csv_radii_cmbtemp = open(radii_vs_cmbtemp_path + csv_radii_vs_cmbtemp_filename + '_' + str(i) + '.csv', 'r')
        df = pd.read_csv(csv_radii_cmbtemp)
        
        tcmb_vals = np.flip(np.array(df['cmb temp']))
        icr_vals = np.flip(np.array(df['inner core radius']))
        lbsz1_vals = np.flip(np.array(df['lb radius sz1']))
        ubsz1_vals = np.flip(np.array(df['ub radius sz1']))
        lbsz2_vals = np.flip(np.array(df['lb radius sz2']))
        ubsz2_vals = np.flip(np.array(df['ub radius sz2']))
        lbsz3_vals = np.flip(np.array(df['lb radius sz3']))
        ubsz3_vals = np.flip(np.array(df['ub radius sz3']))
        rcmb_vals = np.flip(np.array(df['cmb radius']))
        print("tcmb_vals", tcmb_vals)
        plt.clf()
        plt.figure(num=i, figsize=(10,10))
        plt.plot(tcmb_vals, lbsz1_vals, linestyle='solid', linewidth=5, color='#ffc900', label='Lower Bound sz1')
        plt.plot(tcmb_vals, icr_vals, linestyle='dotted', linewidth=5, color='silver', label='Inner Core')
        plt.plot(tcmb_vals, ubsz1_vals, linestyle='dotted', linewidth=5, color='#ffc900', label='Upper Bound sz1')
        plt.plot(tcmb_vals, lbsz2_vals, linestyle='solid', linewidth=5, color='#ffe379', label='Lower Bound sz2')
        plt.plot(tcmb_vals, ubsz2_vals, linestyle='dotted', linewidth=5, color='#ffe379', label='Upper Bound sz2')
        plt.plot(tcmb_vals, lbsz3_vals, linestyle='solid', linewidth=5, color='#fff7da', label='Lower Bound sz3')
        plt.plot(tcmb_vals, ubsz3_vals, linestyle='dotted', linewidth=5, color='#fff7da', label='Upper Bound sz3')
        plt.plot(tcmb_vals, rcmb_vals, linestyle='solid', linewidth=5, color = 'salmon', label='Core-Mantle Boundary')
        plt.xlabel('CMB Temp [K]', fontsize=20)
        plt.gca().invert_xaxis()
        plt.ylabel('Radius [km]', fontsize=20)
        plt.ylim((-100,2750))
        plt.title('Radius vs. CMB Temp -- ' + str(i) + ' km Present-Day ICR', fontsize=24)
        plt.legend(loc='upper right', prop={'size': 10})
        plt.savefig(radii_vs_cmbtemp_path + '/plot_' + str(i) + '.png', dpi=300)

        # Compare radial data from evolution models of different tolerances
        # Comparing the radius of the upper bound of the first snow zone should be enough
        if xtol != 1.e-6 and ftol != 1.e-6:
            # Import radial data from original
            olddata_path = './original_tolerance_evolution_data'
            olddata_csv = open(olddata_path + csv_radii_vs_cmbtemp_filename + '_' + str(i) + '.csv', 'r')
            old_data = pd.read_csv(olddata_csv)
            old_radius = old_data['ub radius sz1']
            newdata_csv = open(radii_vs_cmbtemp_path + csv_radii_vs_cmbtemp_filename + '_' + str(i) + '.csv', 'r')
            new_data = pd.read_csv(newdata_csv)
            new_radius = new_data['ub radius sz1']
            rad_diffs = new_radius - old_radius
            print('RADIUS DIFFERENCES: ', rad_diffs)
            print('XTOL', xtol)
            print('FTOL', ftol)
            # Plot the radius differences as a function of cmb temperature
            plt.clf()
            plt.figure(num=str(i), figsize=(10,10))
            plt.plot(tcmb_vals, rad_diffs, linestyle='solid', linewidth=5, color='#ffc900', label='Upper Bound sz1 Differences')
            plt.xlabel('CMB Temp [K]', fontsize=20)
            plt.gca().invert_xaxis()
            plt.ylabel('Radius Difference [km]', fontsize=20)
            plt.ylim((-5, 5))
            plt.title('Radius Differences vs. CMB Temp -- ' + str(i) + ' km Present-Day ICR', fontsize=24)
            plt.legend(loc='upper right', prop={'size': 10})
            plt.savefig(radii_vs_cmbtemp_path + '/plot_diff_tol_' + str(i) + '.png', dpi=300)
            

        # present day inner core radius increments -- use if statements while 50 km present day icr is not in order (currently between 450 and 500 km)
        if i == 0.0:
            i += 100.0
        elif i == 450.0:
            i -= 400.0
        elif i == 50.0:
            i += 450.0
        else:
            i += 50.0

print('Done simulating evolution Mercury interior model ...')



