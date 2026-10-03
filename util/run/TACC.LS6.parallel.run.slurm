#!/bin/bash
#SBATCH -J v1.0.4.Mercury.present.20250707 # job name
#SBATCH -o a.log.o%j             # output and error file name (%j expands to SLURM jobID)
#SBATCH -N 8                     # number of nodes requested
#SBATCH -n 1024                  # total number of tasks to run in parallel
#SBATCH -p normal                # queue (partition) 
#SBATCH -t 3:00:00              # run time (hh:mm:ss) 
#SBATCH -A EAR24017              # Allocation name to charge job against

#SBATCH --mail-user=dliu@ig.utexas.edu
#SBATCH --mail-type=begin   # email me when the job starts
#SBATCH --mail-type=end     # email me when the job finishes

module load launcher

export LAUNCHER_WORKDIR=/scratch/07931/dunyuliu/3.Krista/MercuryInteriorMonteCarlo_fixISNOWIndex_20250707/PIE/work.margot
export LAUNCHER_JOB_FILE=commands_launcher 

${LAUNCHER_DIR}/paramrun
