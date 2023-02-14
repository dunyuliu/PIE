#!/bin/bash
#SBATCH -J v1.0.4.Mercury.present   # job name
#SBATCH -o a.log.o%j             # output and error file name (%j expands to SLURM jobID)
#SBATCH -N 1                        # number of nodes requested
#SBATCH -n 110                       # total number of tasks to run in parallel
#SBATCH -p normal              # queue (partition) 
#SBATCH -t 24:00:00                 # run time (hh:mm:ss) 
#SBATCH -A EAR22012                  # Allocation name to charge job against

#SBATCH --mail-user=dliu@ig.utexas.edu
#SBATCH --mail-type=begin   # email me when the job starts
#SBATCH --mail-type=end     # email me when the job finishes

module load launcher

export LAUNCHER_WORKDIR=/work2/07931/dunyuliu/3.Krista/Mercury_present_evolution_v1.0.4_20230127
export LAUNCHER_JOB_FILE=commands_launcher 

${LAUNCHER_DIR}/paramrun
