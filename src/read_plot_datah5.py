#!/usr/bin/env python3
# The script will read and plot radial profiles of a variety of quantites stored in data.h5 
#   for each Mercury present-day model.
#   It will plot the results in a normalized way.
 
import pandas as pd
import matplotlib.pyplot as plt
import coreEos as eos
import numpy as np

filename = "./CMR2_0.346_CMC_0.428_S+Si_Steinbruegge/present_Si%wt_0.0_data/550.0_data.h5"

# Read the data for each key
P_data = pd.read_hdf(filename, 'P')
T_data = pd.read_hdf(filename, 'T')
Tad_data = pd.read_hdf(filename, 'Tad')
chi_li_data = pd.read_hdf(filename, 'chi_li')
g_data = pd.read_hdf(filename, 'g')
r_data = pd.read_hdf(filename, 'r')
rho_data = pd.read_hdf(filename, 'rho')

# calculate alpha and C_p profiles based on P and T profiles using eosAndersonGrueneisen.eos function.
alpha_data = np.empty(r_data.shape)
C_p_data    = np.empty(r_data.shape)

# use liqudFeS. For other scenarios, please use the corresponding one. 
# This part of the code is from planet_input.py.

MFeS      = (55.845+32.065)
liquidFeS = eos.eosAndersonGrueneisen(M0=MFeS,p0=1E-5,T0=1650,
                                V0=22.956500240757844,alpha0=11.9e-5,
                                KT0=17.01901122392699,
                                KTP0=5.92217679116356,
                                deltaT=5.9221767911635,kappa=1.4,
                                gamma0=1.3,q=0)

for i in r_data.index:
    ptmp = P_data[i]/1e9 # converting Pa to GPa
    Ttmp = T_data[i]
    liquidFeS.eos(ptmp,Ttmp)
    alpha_data[i] = liquidFeS.alpha
    C_p_data[i] = liquidFeS.Cp
#print(P_data)
#print(alpha_data)
#print(C_p_data)

P_norm = P_data / P_data.max()
T_norm = T_data / T_data.max()
Tad_norm = Tad_data / Tad_data.max()
chi_li_norm = chi_li_data / chi_li_data.max()
g_norm = g_data / g_data.max()
r_norm = r_data / r_data.max()
rho_norm = rho_data / rho_data.max()
alpha_norm = alpha_data/alpha_data.max()
C_p_norm = C_p_data/C_p_data.max()

# create a list of data and labels
data_list = [P_norm, T_norm, Tad_norm, chi_li_norm, g_norm, rho_norm, alpha_norm, C_p_norm]
label_list = ['P,max='+"{:.2e}".format(P_data.max()), 'T,max='+"{:.2e}".format(T_data.max()), \
            'Tad,max='+"{:.2e}".format(Tad_data.max()), 'chi_li,max='+"{:.2e}".format(chi_li_data.max()), \
            'g,max='+"{:.2e}".format(g_data.max()), 'rho,max='+"{:.2e}".format(rho_data.max()), \
            'alpha,max='+"{:.2e}".format(alpha_data.max()), 'Cp,max='+"{:.2e}".format(C_p_data.max())]

# plot
fig = plt.figure(figsize=(10,8), dpi=600)
# plot the data
for data, label in zip(data_list, label_list):
    plt.plot(r_data/1e3, data, label=label)

plt.xlabel('Radius in km')
plt.title(filename)
plt.legend()
plt.savefig('0Datah5show.png')
