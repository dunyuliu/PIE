#!/bin/bash
cd ${SCRATCH:?set SCRATCH to your work dir}
export NW=16
while [ ! -f queue2.done ]; do sleep 60; done
/usr/bin/python3 run_batch.py cases_detj0.json clamp clamp_chi=1 linesearch=1 maxit=25 > runs_clamp.log 2>&1
/usr/bin/python3 run_batch.py cases_10m.json start50 start_ricb=50010 > runs_start50.log 2>&1
/usr/bin/python3 run_batch.py cases_maxit.json maxit40 maxit=40 > runs_maxit40.log 2>&1
/usr/bin/python3 run_batch.py cases_maxit.json eps5 eps=1e-5 > runs_eps5.log 2>&1
/usr/bin/python3 run_batch.py cases_later.json cold cold=1 > runs_cold.log 2>&1
echo DONE > queue3.done
