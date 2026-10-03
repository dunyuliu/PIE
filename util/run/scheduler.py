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
# CMC ranges from 0.424 to 0.462. delta is 0.038

#dCMR2 = 0.004
#dCMC  = 0.008
#CMR2_list = np.linspace(0.328, 0.360, 9); also add the means from different studies.
# 13 Values: [0.328, 0.332, 0.333, 0.336, 0.337, 0.340, 0.344, 0.346, 0.348, 0.352, 0.353, 0.356, 0.360]

#CMC_list  = np.linspace(0.424, 0.462, 6); also add the means of 0.437 and 0.443 from studies.
# 8 Values : [0.424  0.4316 0.437 0.4392 0.443 0.4468 0.4544 0.462 ]

if __name__ == "__main__":
    CMR2tmp   = sys.argv[1]
    CMCtmp    = sys.argv[2]

    CMR2_list = [CMR2tmp] #dCMR2 = 0.004
    CMC_list  = [CMCtmp]

    chi_li_icb_list  = np.linspace(0.0, 0.15, 16)
    light_el_list1    = ['S', 'Si']
    light_el_list2    = ['S+Si']
    #liquidus_eq_list = ['Steinbruegge', 'Edmund']
    liquidus_eq_list = ['Edmund']

    print('SCHEDULER: running model with CMR ', CMR2_list)
    print('SCHEDULER: running model with CMC ', CMC_list)
    print('SCHEDULER: running model with %wt ', chi_li_icb_list)

    for CMR2 in CMR2_list:
      for CMC in CMC_list:
        for light in light_el_list2:
          for liquidus in liquidus_eq_list:
            for chi_li_icb in chi_li_icb_list:
              print('Running the scenario with')
              print('CMR2 = ', str(CMR2))
              print('CmC = ', str(CMC))
              print('Light el = ', light)
              print('Liquidus eq = ', liquidus)
              print('Chi_li_icb = ', chi_li_icb)
              cmd = sys.executable + ' -m pie p '+ str(CMR2) + ' ' + str(CMC) + ' ' + light + ' ' + liquidus + ' ' + str(chi_li_icb)
              os.system(cmd)

    for CMR2 in CMR2_list:
      for CMC in CMC_list:
        for light in light_el_list1:
          for liquidus in liquidus_eq_list:
            print('Running the scenario with')
            print('CMR2 = ', str(CMR2))
            print('CmC = ', str(CMC))
            print('Light el = ', light)
            print('Liquidus eq = ', liquidus)
            cmd = sys.executable + ' -m pie p '+ str(CMR2) + ' ' + str(CMC) + ' ' + light + ' ' + liquidus
            os.system(cmd)
