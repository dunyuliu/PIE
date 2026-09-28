# PIE: Planetary Interior Evolution 
PIE is a Python-based software to invert Mercury present-day interior structure by matching geodetic, geochemical, and thermodynamic constraints, and simulate evolutions of its interior structure (under development). <br/>

./src/ contains the Python source code to simulate the present-day Mercury inteior structure and its evolution.
Compared to its predecesor present-day model ([GitHub repo](https://github.com/gregorsteinbruegge/MercuryInterior.git)) used in [Steinbruegge et al. (2020)](https://doi.org/10.1029/2020GL089895), two light elements in the core - S and Si - are implemented, based on late thermodynamic liquidus constraints, and iron snow model can be produced. 

Si %wt is currently assumed to be a constant throughout the core, while S %wt are adjusted according to liqudius properties, variable over the core radius. 

# Quickstart guide
## Monte Carlo simulation on CMR2:
```
python monteCarlo.run.py
```
will generate a suite of Mercury present-day interior models fitting a set of CMR2 and CMC that are randomly generated from assigned mean CMR2 and its STD.

## General run with specified CMR2 and CMC:
```
python scheduler.py CMR2 CMC
```
where CMR2 and CMC, for Margot et al. constraints, are 0.346 and 0.424, respectively. The scheduler.py will loop over cases (S, Si, S+Si), liquidus equation (Steinbruegge, Edmund), and in particular for the case with S+Si, Si%wt from 0% to 15% in 1% increment. 

Please create folder ./results
```
mkdir results
```
and figures and datasets will be stored under ./results/. 

# Large ensemble Monte Carlo simulation
To produce a large ensemble of interior models that samples a normal distribution from a CMR2 with its STD, supercomputuers such as Lonestar6 at TACC provides LAUNCHER computing module to run serial jobs in parallel.

```
python TACC.create.parallel.launcher.py
# create a command_launcher file that contains X number of lines of commands.
# command_launcher will be used by LAUNCHER module on TACC LS6.
# X is specified in variable total_CPU in the file.

sbatch TACC.LS6.parallel.run.slurm
# submit a parallel job requesting 8 computing nodes with a total of 1024 CPU cores,
#   in this example, that uses LAUNCHER to run all the 1024 models in parallel.

# The example run here takes less than 2 hours.
```

## Testing

```
/usr/bin/python3 testsys/run.py            # fast tiers: unit + contract + integration, ~85 s
/usr/bin/python3 testsys/run.py e2e        # full-pipeline run vs a committed golden, ~5.5 min
```

See [`testsys/README.md`](testsys/README.md) for tier definitions, the
published-paper parity check against Zenodo-archived output, and a
known-environment note (`/usr/bin/python3` needs `PYTHONNOUSERSITE=1`
for subprocess runs -- see that file).

## Citation

If you use PIE, please cite:

Dunnigan, A. H., Liu, D., Steinbrügge, G. B., Rivoldini, A., Dumberry, M., Cao, H., & Soderlund, K. M. (2026). Interior models of Mercury and conditions for iron snow formation in a Fe-S-Si core. *Journal of Geophysical Research: Planets*, 131(4), e2025JE009368. https://doi.org/10.1029/2025JE009368

Code and data archived on Zenodo for that paper (PIE v1.0.5):
- Code: https://doi.org/10.5281/zenodo.16929504
- Simulation dataset and plotting scripts: https://doi.org/10.5281/zenodo.16459292

Machine-readable metadata is in [`CITATION.cff`](CITATION.cff) (GitHub's "Cite this repository" button).

## Copyright and distribution

All the material in this repository is open-source and distributed under the GNU General Public License v3.0. For detials, see ``LICENSE``.

Contributors: Liu, Dunnigan, Steinbruegge, Rivoldini.

If you have any questions and comments, feel free to reach out to Dunyu Liu (dliu@ig.utexas.edu). 
