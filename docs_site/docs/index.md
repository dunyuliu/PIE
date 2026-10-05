# PIE: Planetary Interior Evolution

PIE is a Python-based software package that inverts Mercury's present-day
interior structure (a Fe core carrying S and/or Si as light elements) by
matching geodetic, geochemical, and thermodynamic constraints, and is
developing a companion model of the interior's evolution over time.

Compared to its predecessor present-day model
([GitHub repo](https://github.com/gregorsteinbruegge/MercuryInterior.git))
used in
[Steinbruegge et al. (2020)](https://doi.org/10.1029/2020GL089895), PIE
implements two light elements in the core (S and Si) based on later
thermodynamic liquidus constraints, and can produce an iron-snow model.
Si wt% is currently assumed constant throughout the core, while S wt% is
adjusted according to liquidus properties, varying over the core radius.

All code is serial Python, packaged as the installable `pie` package. No
compiled component, no MPI, no conda.

## Where to go next

- **[Install](install.md)** -- the one supported environment (Python 3.12,
  exact pins) and the `uv`-based setup.
- **Running PIE** -- a single case, the composition [scheduler](running/scheduler.md),
  a [Monte Carlo ensemble](running/monte-carlo.md), and
  [large batch runs](running/robust-runner.md) on a shared box or TACC
  Lonestar6.
- **[Project layout](layout.md)** -- what lives where in the repository.
- **[Version history](versions.md)** -- the release timeline, from v1.0.5
  (the Dunnigan et al. 2026 Zenodo archive) to the current tag.
- **[Project status](status.md)** -- a short summary of recently closed
  engineering milestones.

## Citation

If you use PIE, please cite the archived code release and the accompanying
paper -- see `CITATION.cff` in the repository root for the current
citation metadata.
