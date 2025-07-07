# PIE: Planetary Interior Evolution 
PIE is a python-based code to invert Mercury interior structure to match geodetic observations and geochemical constraints. <br/>

src/ contains the python source code to simulate the present day Mercury structure and its evolution.
Compared to its predecesor present day model ([GitHub repo](https://github.com/gregorsteinbruegge/MercuryInterior.git)), used in [Steinbruegge et al. 2020](https://doi.org/10.1029/2020GL089895), two light elements - S and Si - are implemented. 

Si is currently assumed to be a constant throughout the core, which can be adjusted in src/globalvar.py.

# Quickstart guide
## Monte Carlo simulation on CMR2:
```
python monteCarlo.run.py
```
will generate a suite of Mercury interior models fitting a set of CMR2 and CMC that are randomly generated from a mean CMR2 and its STD.  

## General run with specified CMR2 and CMC:
```
python scheduler.py CMR2 CMC
```
where CMR2 and CMC should be numbers like 0.346 and 0.424. Then the scheduler.py will loop over cases (S, Si, S+Si), liquidus equation (Steinbruegge and Edmund), and for the case S+Si, Si%wt from 0% to 15% in 1% increment. 

Figures and datasets will be stored in the same directory under ./results/. If ./results is nonexist, please create one by 
```
mkdir results
```
## Copyright and distribution

All the material in this repository is open-source and distributed under the GNU General Public License v3.0. For detials, see ``LICENSE``.

Contributors: Liu, Dunnigan, Steinbruegge, Rivoldini.

If you have any questions and comments, feel free to reach out to Dunyu Liu (dliu@ig.utexas.edu). 
