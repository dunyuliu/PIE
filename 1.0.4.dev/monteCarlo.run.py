#! /usr/bin/env python3
import sys, os, time
import numpy as np
from datetime import datetime

meanCMR2 = 0.346
stdCMR2  = 0.014
CMC      = 0.426
CMR2 = np.random.normal(meanCMR2, stdCMR2, 1)
CMR2 = float(CMR2)
print('MONTECARLO: running model with CMR2 ', CMR2)
print('MONTECARLO: running model with CMC ', CMC)

log_file= './results/log.' + str(round(CMR2,4)) + '.' + str(round(CMC,4)) + '.txt'
cmd = 'python scheduler.py ' + str(round(CMR2,4)) + ' ' + str(round(CMC,4)) + '  >' + log_file 
startTime = time.time()
#os.system(cmd)
print('MONTECARLO: time consumed for this model is ', "{:.2f}".format(time.time()-startTime), ' seconds.')

with open('./results/timeLog.'+datetime.now().strftime("%Y%m%d")+'.txt','a') as file:
    file.write('Model_CMR2_'+str(CMR2)+'_CMC_'+str(CMC)+' used is'+"{:.2f}".format(time.time()-startTime)+' s. '+'\n')
