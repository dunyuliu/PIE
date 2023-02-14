#! /usr/bin/env python3
import sys, os
import numpy as np
# This create.parallel.launcher.py create a launcher file for Lonestar6. 
CMR2_list = [0.328, 0.332, 0.333, 0.336, 0.337, 0.340, 0.344, 0.346, 0.348, 0.352, 0.353, 0.356, 0.360]
CMC_list  = [0.424, 0.4316,0.437, 0.4392,0.443, 0.4468,0.4544,0.462]
print('CMR2 values include ', CMR2_list)
print('CMC values include ', CMC_list)

with open("commands_launcher", "w") as file:
    for CMR2 in CMR2_list:
        for CMC in CMC_list: 
            log_file= 'log.' + str(round(CMR2,4)) + '.' + str(round(CMC,4)) + '.txt'
            cmd_str = 'python scheduler.py ' + str(round(CMR2,4)) + ' ' + str(round(CMC,4)) + '  >' + log_file + '\n'
            file.write(cmd_str)
file.close()
