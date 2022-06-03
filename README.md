# Mercury_present_evolution

## Introduction

src/ contains the python source code to simulate the present day Mercury structure and its evolution.
Compared to its predecesor present day model ([GitHub repo](https://github.com/gregorsteinbruegge/MercuryInterior.git)), used in [Steinbruegge et al. 2020](https://doi.org/10.1029/2020GL089895), two light elements - S and Si - are implemented. 

Si is currently assumed to be a constant, which can be adjusted in src/globalvar.py.

## How to run the code?

To run the present day model, use the following command
```
python main_present.py
```
To run the evolution model, first the corresponding present day model needs to be run to generate datasets as input for the evolution model.
Then, run the following command
```
python main_evolution.py
```

Figures and datasets will be generated under the paths specified in the src/globalvar.py.

## Code 

## Copyright and distribution

All the material in this repository is open-source and distributed under the GNU General Public License v3.0. For detials, see ``LICENSE``. (Will change it after our discussion)

Contributors: Steinbruegge, Liu.

If you have any questions and comments, feel free to reach out to XXX. 
