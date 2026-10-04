#! /usr/bin/env python3
import sys, os
import numpy as np

# This create.parallel.launcher.py create a launcher file for Lonestar6. 
total_CPU = 1024
with open("commands_launcher", "w") as file:
    for iCPU in range(total_CPU):
        cmd_str = 'python monteCarlo.run.py \n'
        file.write(cmd_str)
file.close()
