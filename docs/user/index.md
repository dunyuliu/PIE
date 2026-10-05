# PIE User Guide

PIE (Planetary Interior Evolution) inverts Mercury's present-day interior
structure -- an iron core carrying sulfur and/or silicon as light elements --
against geodetic (CMR2, CMC) constraints, and is developing a companion
model of how that interior evolves over time. The present-day model is
production code; the evolution model is under active development. All code
is serial Python, packaged as the installable `pie` package.

This site covers installing PIE, running a single case or a parameter
sweep, what PIE physically models, the parameter reference, output file
formats, how PIE's results are checked, and what each error code means.

## Where to go

* Getting started -- installing PIE with `uv` and running a first case.
* Running a case -- a single composition, the scheduler sweep, Monte Carlo
  ensembles, and the resumable large-ensemble runner.
* Model overview -- what PIE physically models and how it solves for it.
* Parameters -- every solver constant and physical bound, generated from
  the code itself.
* Output files -- what each output file contains and how its columns are
  defined.
* Benchmarks -- how PIE's results are checked, and what "checked" means in
  each case.
* Troubleshooting -- what each per-radius error code means operationally.
* Citing -- how to cite PIE and the paper it was built for.

## Getting the code

PIE is released under the GNU General Public License v3.0 and hosted on
GitHub. See [Citing](citing.md) for the archived code and data releases
tied to its published science.
