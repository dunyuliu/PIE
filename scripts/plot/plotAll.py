#! /usr/bin/env python3
import sys, os
import numpy as np

# This scheduler script will loop over CMR2 and CmC parameter space. 
# Data source.
  # CMR2:
  # Verma and Margot 2016. CMR2 = 0.346+-0.014 ~ 0.332 - 0.360.
  # Genova et al. 2019, CMR2 = 0.333+-0.005 ~ 0.328 - 0.338. 
  # Konopliv et al., 2020, CMR2 = 0.337+-
  # Smith et al., 2012. CMR2 = 0.353+-0.017 ~ 0.336 - 0.370. ??
  # CmC:
  # Verma and Margot. ?
  # Genova et al., 2019. CMC=0.443+-0.019 ~ 0.424 - 0.462. 
  # Konopliv et al., 2020, CMC = 0.437. 

# So, CMR2 ranges from 0.328 to 0.360. delta is 0.032. 
# CMC ranges from 0.424 to 0.462. delta is 0.03


CMR2_list = [0.328, 0.332, 0.333, 0.336, 0.337, 0.340, 0.344, 0.346, 0.348, 0.352, 0.353, 0.356, 0.360]
CMC_list  = [0.424, 0.4316,0.437, 0.4392,0.443, 0.4468,0.4544,0.462]

chi_li_icb_list  = np.linspace(0.0, 0.15, 16)
light_el_list1    = ['S', 'Si']
light_el_list2    = ['S+Si']
liquidus_eq_list = ['Steinbruegge', 'Edmund']

print(CMR2_list)
print(CMC_list)
print(chi_li_icb_list)

for CMR2 in CMR2_list:
  for CMC in CMC_list: 
    for light in light_el_list2:
      for liquidus in liquidus_eq_list:
        print('Running the scenario with')
        print('CMR2 = ', str(CMR2))
        print('CmC = ', str(CMC))
        print('Light el = ', light)
        print('Liquidus eq = ', liquidus)
        cmd = 'python summaryPlot.py plot '+ str(CMR2) + ' ' + str(CMC) + ' ' + light + ' ' + liquidus
        os.system(cmd)


