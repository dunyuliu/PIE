# Provenance: v1.0.4 (2023-01-27) historical regression fixture

Source (outside this repo, not committed in full): a prior collaborator
run stored at
`3.Krista_Soderlund/MercuryEvolution/Mercury_present_evolution_v1.0.4_20230127/`
on this machine, dated 2023-01-27, running an earlier `libCore.py`
(`get_mass_core` = `rho[i]*(r[i]**3-r[i-1]**3)`, missing the ENTIRE
`(4/3)*pi` volume prefactor -- not just the `pi` factor bb37b0a's
commit message names; see below). This directory holds only the ONE
small file compared here (17 rows, ~2 KB), not the full v1.0.4 tree.

## File

`CMR2_0.346_CMC_0.424_S_Edmund/present_day_0.346_0.424_0.0.csv` --
copied verbatim from
`.../CMR2_0.346_CMC_0.424_S_Edmund/csvfiles/present_day_0.346_0.424_0.0.csv`
in the source above. Same (CMR2, CMC, light_element, liquidus_eq) as
`self_v1.0.5/CMR2_0.346_CMC_0.424_S_Edmund/pMetaData_0.00.csv` (this
repo's current-HEAD e2e golden), so the two are directly row-comparable
(same `ricb` grid, both 17/18-row sweeps that stop at the same Newton
non-convergence point).

## Measured deltas (v1.0.4 -> current HEAD), all 17 common rows

| Field | max relative diff | Attribution |
|---|---|---|
| `core_mass` | constant ratio 4.18879 = exactly `(4/3)*pi` | `get_mass_core`'s volume prefactor: v1.0.4 had NEITHER `4/3` nor `pi` (`rho[i]*(r[i]**3-r[i-1]**3)`); current HEAD has `rho[i]*(4./3.)*np.pi*(...)`. bb37b0a's commit message says "fix missing pi", but the v1.0.4 snapshot here is missing the `4/3` too -- either an intermediate, undocumented state existed between 2023 and bb37b0a (2025-03-03), or bb37b0a's diff (`1.0.4.dev/libCore.py`) was against a branch that already carried the `4/3` and this 2023 snapshot is from a different, older line. Either way: fully attributable to `get_mass_core`'s volume-prefactor formula, not a new divergence. |
| `isnow` | categorical, 10/17 rows differ (v1.0.4 always reports `2`; current HEAD reports `1` or `3` for those rows) | Iron-snow classification logic (`2a9d576`, "fix iron snow layer classification to include 3 for deep snow+layers", and likely earlier refinements the 2023 snapshot predates) -- NOT gated to equality (see test), the classification is KNOWN to have changed. |
| every other field (`rhom`, `mass`, `moi`, `cmc`, `Picb`, `Tcmb`, `chi_li_in`, `Pcmb`, `chi_li_eut_icb`, `chi_li_eut_cmb`, `rcmb`, `chi_li_icb`) | ≤ 1.1e-9 | Below the Newton solver's own xtol=ftol=1e-6 -- these are UNCHANGED between v1.0.4 and current HEAD; the test gates them at rtol=1e-6 (equality, not a documented delta). |

`chi_S_bulk` is not in v1.0.4's column set at all (added `f06b395`,
after this snapshot) -- not compared.
