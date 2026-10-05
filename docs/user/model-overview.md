# Model Overview

## What PIE solves

Mercury's large iron core, inferred from its high uncompressed density and
its measured moment-of-inertia parameters, is thought to carry one or more
lighter alloying elements -- sulfur and/or silicon -- that lower the melting
point of the core and control whether, and where, solid iron can
crystallize out of the liquid outer core today. PIE inverts a Mercury
interior model (core composition, size, and thermal state) against two
geodetic constraints on the planet's mass distribution:

* **CMR2** -- the normalized polar moment of inertia (C/MR^2), from
  libration and gravity measurements.
* **CMC** -- the fraction of the planet's total moment of inertia carried
  by the core (Cc/C).

Given CMR2, CMC, a choice of light element combination (S, Si, or S+Si),
and a liquidus equation, PIE finds the core/mantle structure consistent
with those constraints, for each tried inner-core radius: core and mantle
densities, central pressure and temperature, the light-element
concentration profile, and whether "iron snow" -- an inverted-density
crystallization layer where solid iron forms partway up the outer core
rather than at the inner-core boundary -- can occur at that configuration.

This supersedes a predecessor present-day model that assumed sulfur as the
only light element ([Steinbruegge et al. 2020](https://doi.org/10.1029/2020GL089895));
PIE adds silicon and the combined Fe-S-Si system, built on late
thermodynamic liquidus constraints ([Dunnigan et al. 2026](https://doi.org/10.1029/2025JE009368)).

## How it solves it

Each present-day model, at one trial inner-core radius, is a 5-unknown
shooting problem: pressure and temperature at the planet's centre, the
outer-core/mantle-boundary radius, mantle density, and the light-element
fraction at the inner-core boundary. PIE integrates the structure equations
outward from the centre (an ODE shoot through the EOS) and adjusts the 5
unknowns with a bounded line-search Newton's method until the integrated
profile matches CMR2, CMC, and the light-element mass balance. A run
sweeps a grid of trial inner-core radii (`dr` apart, see
[Parameters](parameters.md)), warm-starting each radius from the last
converged one; a radius that fails to converge is recorded with an error
code (see [Troubleshooting](troubleshooting.md)) and the sweep continues to
the next radius rather than stopping.

Si weight percent is currently assumed constant across the whole core,
while S weight percent is allowed to vary with radius according to the
liquidus relation chosen.

## The companion evolution model

A separate, in-development model (`pie/drivere.py`/`pie/shoote.py`) aims to
simulate how this interior structure evolves over Mercury's thermal
history, rather than inverting a single present-day snapshot. It is not
yet production code and is not covered by the rest of this guide.

## Regression-anchored vs. independently verified

PIE's single-light-element cases (S-only, Si-only) have an independent
truth anchor: the predecessor Fe-S/Fe-Si codes and published liquidus/EOS
limits. The combined **S+Si** case does not -- its only check against
external data is the Zenodo-archived Monte Carlo dataset from Dunnigan et
al. 2026, produced by this same code family (v1.0.5), so a match there
demonstrates reproducibility, not independent correctness. See
[Benchmarks](benchmarks.md) for exactly which checks fall in which
category.
