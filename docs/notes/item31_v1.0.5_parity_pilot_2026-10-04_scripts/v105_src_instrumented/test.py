import numpy as np
import coreEos as eos
from planet_input import*
from globalvar import *

p   = 5e9
t   = 1000
x1  = [0,0.1]
x2  = 0.1

res1 = eos.liquidNonIdalFeSSi(x1,p,t,param)
res2 = eos.liquidNonIdalFeSi(x2,p,t,param)
print(res1)
print(res2)
