# Parameters

## Per-run inputs (command line)

These are supplied on every run, not defaulted in code -- see
[Running a Case](running-a-case.md) for the full invocation:

* **`CMR2`** -- normalized polar moment of inertia constraint (e.g. `0.346` for Margot et al.).
* **`CMC`** -- core moment-of-inertia fraction constraint (e.g. `0.424` for Margot et al.).
* **`light_element`** -- `S`, `Si`, or `S+Si`.
* **`liquidus_eq`** -- `Steinbruegge` (Steinbruegge et al. 2020) or `Edmund` (Edmund et al. 2022).
* **`chi_Si_icb`** -- Si weight fraction at the inner-core boundary; required only when `light_element` is `S+Si`, otherwise fixed at `0.0`.

## Solver constants and physical bounds (generated)

<!-- BEGIN PARAMETER REFERENCE (generated from pie/globalvar.py by docs/user/gen_params.py; do not edit by hand) -->

Every entry below is a module-level constant in `pie/globalvar.py`, read by the present-day solver (`pie/shootp.py`, `pie/driverp.py`) and the Newton iteration it drives. These are solver constants and physical bounds, not per-run inputs -- CMR2, CMC, the light-element choice, the liquidus equation, and `chi_Si_icb` are supplied on the command line instead; see [Running a Case](running-a-case.md).

* **`dr`** -- default `50000.0`

  radius increment in meters for the present_day model.

* **`max_Si_Steinbruegge2020`** -- default `0.15`

  Maximum Si%wt for calculating liquidus temperature based on Steinbruegge et al. (2020). Shouldn't be exceeded.

* **`max_Si_Edmund2022`** -- default `0.12`

  Maximum Si%wt for calculating liquidus temperature based on Edmund et al. (2022). Shouldn't be exceeded.

* **`MFeS`** -- default `55.845+32.065`

  Constants

* **`MFeSi`** -- default `55.845+28.08`

* **`MFe`** -- default `55.845`

* **`xtol`** -- default `1e-06`

  For Newton solver tol

* **`ftol`** -- default `1e-06`

* **`maxit`** -- default `12`

  maximum number of iterations

<!-- END PARAMETER REFERENCE -->
