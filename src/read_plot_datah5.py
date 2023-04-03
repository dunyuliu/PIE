#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt

filename = "./CMR2_0.346_CMC_0.428_S+Si_Steinbruegge/present_Si%wt_0.0_data/550.0_data.h5"

# Read the data for each key
P_data = pd.read_hdf(filename, 'P')
T_data = pd.read_hdf(filename, 'T')
Tad_data = pd.read_hdf(filename, 'Tad')
chi_li_data = pd.read_hdf(filename, 'chi_li')
g_data = pd.read_hdf(filename, 'g')
r_data = pd.read_hdf(filename, 'r')
rho_data = pd.read_hdf(filename, 'rho')

P_norm = P_data / P_data.max()
T_norm = T_data / T_data.max()
Tad_norm = Tad_data / Tad_data.max()
chi_li_norm = chi_li_data / chi_li_data.max()
g_norm = g_data / g_data.max()
r_norm = r_data / r_data.max()
rho_norm = rho_data / rho_data.max()

# create a list of data and labels
data_list = [P_norm, T_norm, Tad_norm, chi_li_norm, g_norm, rho_norm]
label_list = ['P', 'T', 'Tad', 'chi_li', 'g', 'rho']

# plot the data
for data, label in zip(data_list, label_list):
    plt.plot(r_data, data, label=label)

plt.xlabel('r')
plt.legend()
plt.savefig('0Datah5show.png')
