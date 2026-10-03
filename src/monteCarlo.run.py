#! /usr/bin/env python3
import sys, os, time, glob
import numpy as np
from datetime import datetime

meanCMR2 = 0.346
stdCMR2  = 0.014
CMC0      = 0.426

if __name__ == "__main__":
    # Optional explicit seed (argv[1]): makes a single draw reproducible and lets
    # a launcher (TACC.LS6.create.parallel.launcher.py / the knox xargs recipe,
    # see README "Large ensemble Monte Carlo simulation") regenerate the exact
    # same CMR2/CMC for a resumability check, instead of each line being an
    # unrepeatable, unseeded draw. Unseeded (no argv) keeps the old ad hoc
    # interactive behaviour.
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else None
    rng = np.random.default_rng(seed)

    CMR2 = rng.normal(meanCMR2, stdCMR2, 1)
    CMR2 = float(CMR2)
    CMC = CMC0*meanCMR2/CMR2
    print('MONTECARLO: running model with CMR2 ', CMR2)
    print('MONTECARLO: running model with CMC ', CMC)

    log_file = './results/log.' + str(round(CMR2,17)) + '.' + str(round(CMC,17)) + '.txt'
    # Resumable: a launcher re-running this exact seeded line after a
    # partial/interrupted ensemble run skips work already done. globalvar.py
    # formats CMR2/CMC with "{:.17f}" at full float precision, which a
    # round-tripped command-line string won't reconstruct byte-for-byte, so
    # match by rounded prefix (6 decimals is far finer than this ensemble's
    # CMR2 spread, ~0.03) rather than reconstructing the exact dirname. Checks
    # the scheduler.py-produced S+Si dir only (its 16-value chi_Si_icb sweep is
    # the long pole); S/Si are quick enough that a partial ensemble re-run
    # redoing them is not worth tracking separately.
    _prefix = './results/CMR2_{:.6f}*_CMC_{:.6f}*_S+Si_Edmund'.format(CMR2, CMC)
    _existing = [d for d in glob.glob(_prefix) if os.path.isdir(d)]
    if _existing and any(f.startswith('pMetaData_') for f in os.listdir(_existing[0])):
        print('MONTECARLO: ' + _existing[0] + ' already has output, skipping.')
        sys.exit(0)

    # sys.executable, not bare 'python': this project's .venv is the only
    # interpreter with the exact pins on hosts where the bare `python3` on
    # PATH is broken (see CLAUDE.md, PATHWAY_FORWARD.md knox note).
    cmd = sys.executable + ' scheduler.py ' + str(round(CMR2,17)) + ' ' + str(round(CMC,17)) + '  >' + log_file
    startTime = time.time()
    os.system(cmd)
    print('MONTECARLO: time consumed for this model is ', "{:.2f}".format(time.time()-startTime), ' seconds.')

    with open('./results/timeLog.'+datetime.now().strftime("%Y%m%d")+'.txt','a') as file:
        file.write('Model_CMR2_'+str(round(CMR2,17))+'_CMC_'+str(round(CMC,17))+' used is'+"{:.2f}".format(time.time()-startTime)+' s. '+'\n')
