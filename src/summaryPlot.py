#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

plt.clf()
plt.figure(0, figsize=(10,10))

compiled_csv   = open(compiled_data_file, 'w')
writer         = csv.writer(compiled_csv)
writer.writerow(presentday_columns)
compiled_csv.close()

# Start 2D matrix of contour variable
icr_inc        = 40 # number of inner core radius increments fom 0 to X km 
contour_matrix = np.empty((15,icr_inc)) # change from 15 to 12 wt % Si values (to account for Si going up to only 12 wt %), number of inner core radius increments
row_index      = 0

for csvfile in os.listdir(csvfiles_path):
    if row_index < 15: # to only include data where wt % Si goes up to 12
        df_individual   = pd.read_csv(csvfiles_path + '/' + csvfile)
        print(df_individual)
        # Also extract data of contour variable to make into 2D matrix
        row             = list(df_individual[contourcond])
        if len(row) != icr_inc:
            diff        = icr_inc - len(row)
            zeros       = [np.nan] * diff
            row         = row + zeros
        contour_matrix[row_index, :] = np.array(row)
        # done adding row to contour matrix
        compiled_csv    = open(compiled_data_file, 'a')
        df_individual.to_csv(compiled_csv, mode='a', index=False, header=False)
        compiled_csv.close()
    row_index += 1

compiled_csv    = open(compiled_data_file, 'r')
df_compiled     = pd.read_csv(compiled_csv)
compiled_csv.close()
# Add dataframe column with markers for snow zone/no snow zone
# '^' = snow zone, 'o' = no snow zone   
df_compiled['marker'] = 'o'

for i in range(0, len(df_compiled)):
    if df_compiled.loc[i, 'isnow'] == 2:
        df_compiled.loc[i, 'marker'] = '^'
wt_Si     = np.array(df_compiled['chi_Si_icb']) * 100
ricb      = np.array(df_compiled['ricb']) / 1E+3
icb_S     = np.array(df_compiled['chi_li_icb']) * 100
inner_S   = np.array(df_compiled['chi_li_in']) * 100
markers   = np.array(df_compiled['marker'])
sz_i      = np.where(markers == '^') # used for plotting
no_sz_i   = np.where(markers == 'o') # used for plotting

# Make axis variables and labels separately in case axes change
xaxis     = wt_Si
yaxis     = ricb
#yaxis = inner_S
xlabel    = 'wt % Si'
ylabel    = 'Inner Core Radius [km]'
#ylabel = 'wt % S inner core avg'
contour_axis  = np.array(df_compiled[contourcond])
sample    = contour_axis[0]
#contour_scale = int(np.log10(sample)) # get scale of contour axis values

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
title = CMR2.capitalize() + ' MOI -- Contouring for ' + contourcond.capitalize()
plt.title(title, fontsize=24)
plt.colorbar()
plt.savefig(contourplot_file + contourcond + '_yaxis = ' + ylabel + '.tiff', dpi=300)

# Make plot of actual grid contour + lines
plt.clf()
plt.figure(1, figsize=(10,10))
xticks   = np.linspace(1, 15, 15) # change from np.linspace(1, 15, 15) to account for Si going up to only 12 wt %
yticks   = np.linspace(0, 1750, icr_inc)
#minc, maxc = np.min(contour_axis), np.max(contour_axis)
X,Y      = np.meshgrid(xticks, yticks)
Z        = np.transpose(contour_matrix)
contouraxiscopy = np.sort(contour_axis.copy())
levels   = np.linspace(contouraxiscopy[0], contouraxiscopy[-1], 50)
cm       = plt.cm.get_cmap(cmap)
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
        # cscale = int(np.log10(c[0]))
        if index     == 0: 
            minc, maxc = 900, 2300
        elif index == 1:
            minc, maxc = 4.7e9, 5.4e9
        elif index == 2:
            minc, maxc = 3250, 3700
        elif index == 3:
            minc, maxc = 5.79e22, 5.95e22
        elif index == 4:
            minc, maxc = -0.01, 0.2
        elif index == 5:
            minc, maxc = -0.03, 0.16
        #minc = np.min(c)
        #maxc = np.max(c) + 10**(cscale-1) / 2
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
plt.savefig(contourplot_file + '.png', dpi=600)

sys.exit()  
