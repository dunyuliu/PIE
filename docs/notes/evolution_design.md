# Evolution-mode design (item 11) — design pass only, no code

Date: 2026-10-01. Author: Dunyu Liu (design pass per owner's 2026-10-01 unpark).
Status: **design only** — `src/drivere.py`, `src/shoote.py`, and the `'e'`
branch of `src/planet_input.py` are untouched; this doc does not implement
anything. No `src/*.py` file is modified by this change.

## 0. What's actually broken today (recap, not re-derived)

`main.py e` crashes immediately: `planet_input.py:119` reads
`elif mod_type == 'e':` but the variable in scope is `code_mode` (set at
line 62's `if code_mode == 'p':`). Calling `planet('e', ...)` always raises
`NameError`. This is a dead-code bug, not evidence of a deeper design flaw in
the `'e'` path — the rest of `shoote.py`/`drivere.py` does run, in isolation,
once the entry point is patched (confirmed by reading the two files; not
re-run here, since that would mean editing `planet_input.py`, out of scope
for a docs-only change). Locked by the strict xfail in
`testsys/unit/test_planet_input.py::test_planet_evolution_mode_would_ideally_work`.

`drivere.py` today is **not a time integration**. It is a quasi-static
snapshot sequence: it loads a present-day `.h5` model, fixes core mass,
mantle mass, and total light element (`chi_li_in`) from that model, and
steps `r_icb` down in fixed 20 km decrements, re-solving the interior
structure at each step under those three conservation constraints (`r_cmb`
and planet radius `rm` are free). Below `r_icb = 0` it switches to
`shoot_mercmodel_nosic` (no inner core, parameterized by central-temperature
excess above the liquidus instead of `r_icb`). Everything is indexed by
`T_cmb`/step count, not by wall-clock time — there is no heat budget, no
`dT_cmb/dt`, nothing is integrated against a clock.

## 1. Target physics and outputs, staged

### Stage 1 — snapshot mode (this is what "reviving evolution mode" means in the near term)

Reproduce today's `r_icb`-stepped snapshot sequence, properly, on the
hardened `shootp.py` solver:

- Same three conservation constraints as `shoote.py`'s `shoot_mercmodel`:
  core mass, mantle mass, and total light-element content (`chi_li_in`)
  held fixed at the values read off the chosen present-day `.h5` model.
- `r_icb` stepped down from the present-day value in a controllable
  decrement (20 km today; make it a parameter, not a literal).
- Below `r_icb = 0`: hand off to `shoot_mercmodel_nosic`'s no-inner-core
  branch, parameterized by central superheat above the liquidus
  (`Tctrplus`), exactly as `drivere.py` does today — this switch-over
  mechanism itself is kept, not redesigned (see Risks, it has a known rough
  edge at the handoff).
- Output per step: `T_cmb`, `r_icb`, `r_cmb`, up to 3 snow-zone bounds
  (layer + deep-snow bounds, same as `shoote.py`'s snow-state logic), plus
  the full radial profile (`r, rho, P, T, T_ad, chi_li`) — same fields
  `driverp.py`/`shootp.py` already write per radius, so Stage 1 output
  schema is a strict superset reusing `presentday_columns`-style naming,
  not a new one.
- Still no wall-clock time axis in Stage 1 — it inherits that limitation
  from `shoote.py` on purpose, to keep Stage 1 a bounded, reviewable port
  rather than a redesign. State this explicitly to the owner (see Risks
  §5.1): Stage 1 alone does **not** satisfy "evolution" in the sense of
  "Mercury's interior at time t Gyr before present."

### Stage 2 — real time evolution (scope only, not designed here)

A genuine time axis requires a heat-budget integration layer sitting above
Stage 1's snapshot solver:

- State variables: `T_cmb(t)`, core heat flux `q_cmb(t)`, secular cooling
  rate, latent heat release at the growing ICB, gravitational energy
  release from light-element exclusion, mantle heat flux (boundary
  condition from a mantle thermal history model — out of this project's
  scope unless one already exists elsewhere in PIE; not found in this repo).
- Stepper: `dT_cmb/dt` (or equivalently `dr_icb/dt`) from an energy balance
  `Q_cmb = Q_secular + Q_latent + Q_gravitational`, each term a function of
  the current snapshot's output (density/entropy profile) from Stage 1.
  Each timestep still requires one full Stage-1 structure solve (same
  conservation constraints) at the trial `r_icb`.
- Snow-zone tracking becomes a continuous state across timesteps (today
  it's recomputed independently at every `r_icb`, with no check that a
  layer at step k connects to the "same" layer at step k+1).
- This is named here as a future stage with its own risk/estimate (§6); not
  designed further in this pass per the owner's instruction.

## 2. Inputs / CLI

`main.py p`'s CLI today is five-to-six positional `sys.argv` entries, parsed
in `globalvar.py` (not `driverp.py` — `driverp.py` takes `param` and `rs`,
already resolved):

```
code_mode CMR2 CMC light_element liquidus_eq [chi_Si_icb if S+Si]
```

(`globalvar.py:14-25`). `main.py` then calls `planet(code_mode, CMR2,
light_element, liquidus_eq)` and, for `'p'`, builds `rs =
np.arange(1e1, 2e6, dr)` and calls `driverp(param, rs)`.

Stage 1's CLI should follow the same shape, substituting the present-day
radius sweep for a present-day **model selection**:

```
e <path-to-present-day-.h5-or-directory> <light_element> <liquidus_eq> \
  [chi_Si_icb if S+Si] [--dricb <m>, default 20000] [--rlow <m>, default 0]
```

- `path_to_present_day_model(s)`: today `drivere.py` globs a whole directory
  (`glob.glob(path_to_present_day_models + "*.h5")`) and loops over every
  match, producing one evolution run per present-day model found. Keep that
  — it's the natural "run evolution for every converged present-day
  composition" use case — but make the path an explicit CLI argument
  instead of a `globalvar.py` module-level constant, matching how
  `driverp.py` receives `rs` as a function argument rather than reading a
  global.
- `light_element`/`liquidus_eq`/`chi_Si_icb`: unchanged in meaning from `p`
  mode — they select the EOS/liquidus table, must match what the present-day
  model was itself produced with (today's code silently trusts the caller to
  pass the same values used to generate the `.h5`; this should become an
  explicit consistency check: read `chi_Si_icb`/`li_el` back out of the
  `.h5`'s `misc` key and assert equality, or warn loudly if not — is a Stage
  1 implementation item, not merely a design nicety, because a silent
  mismatch would silently corrupt every downstream number).
- `--dricb`: the step size, today hard-coded as the literal `20` (km) in
  `drivere.py`'s loop bound; expose it.
- No separate "which quantities get fixed" flag — core mass, mantle mass,
  and `chi_li_in` are fixed by construction of the snapshot method (that is
  the method, not a choice the caller makes per run). If a future caller
  wants a different constraint set, that is a new `shoot_mercmodel` variant,
  not a CLI flag on this one.
- Output: one `.h5` per step (same schema as `driverp.py`'s per-radius
  `.h5` — `r/rho/T/P/g/Tad/chi_li` series + a `misc` key with the scalar
  outputs) plus one CSV accumulating `(r_icb, r_cmb, T_cmb, snow bounds,
  error_code, start, newton_iters, resid_norm)` across the whole step
  sequence — i.e., reuse `driverp.py`'s per-radius csv-row pattern
  (`write_failure_row`, `presentday_columns`-style) rather than `drivere.py`'s
  current separate `csv_radii_cmbtemp` file with its own column list; one
  output convention across `p` and `e` modes, not two.

## 3. Code plan

### Delete (stale duplicates of code already hardened in `shootp.py`)

- `shoote.py::getPgcmb_crust` — 98% identical to `shootp.py`'s; the 2% delta
  is not a semantic difference worth preserving as a fork.
- `shoote.py::getk2` — 55% identical; missing the v1.3 `nrs=0` fix
  (item 17's index-wrap-bug fix). Keeping it would re-import the exact bug
  item 17 just closed, in a second file.
- `shoote.py::mynewtonSys` — 16% identical; this is the pre-item-16/17
  undadamped Newton solver with a bare `sys.exit()` on non-convergence,
  no error codes, no line search, no admissible-box rejection. This is the
  single biggest reason "port, don't patch" is the right call: patching this
  back up to v1.3.0 parity would just be re-doing items 16/17 a second time
  in a second file.
- `shoote.py::shoot_mercmodel` / `J_mercmodel` — the CMR2/CMC-fit residual
  vector (`f`) is replaced wholesale by the conservation-constraint residual
  vector in the ported version (see below); keeping both forks invites drift.

### Merge / port (into `shootp.py`, as an option, not a new file)

- Add a constraint-mode switch to `shootp.py`'s `shoot_mercmodel`: today its
  residual vector `f` is `[P_cmb match, g_cmb match, T_icb match, CmC
  match, CMR2 match]` (`shootp.py:260-264`). The ported evolution mode needs
  `f = [P_cmb match, g_cmb match, T_icb match, (core_mass -
  core_mass_fix)/M, (mantle_mass_fix - mantle_mass)/mantle_mass_fix,
  chi_li_in_fix - chi_li_in]` — `shoote.py`'s six-element residual
  (`shoote.py:211-216`), which is a strict superset (6 unknowns/residuals
  instead of 5: `shoote.py`'s `v` carries `r_icb` itself as an unknown,
  `shootp.py`'s does not, since `shootp.py` is parameterized directly by a
  caller-supplied `ricb`). Concretely: a `constraint_mode` argument
  (`'cmr2_cmc'` today's default, `'mass_chi'` the new one) selecting which
  3 of the 6 total possible constraints apply, built on the *same* hardened
  `mynewtonSys`/line-search/box-rejection machinery — not a second Newton
  loop. `mercmodel_box`'s admissible-box test (chi_li_icb bound,
  `rcmb <= ricb`, non-finite) is constraint-mode-agnostic and needs no
  change.
- `shoot_mercmodel_nosic`'s residual (`shoote.py:808-812`, 4-element: P/g
  match plus the same two mass/chi constraints) needs the equivalent port —
  it already lacks a `shootp.py` counterpart entirely (no-inner-core
  present-day models aren't a thing `driverp.py` produces), so this is new
  code in `shootp.py`, not a merge, but it should reuse
  `getPgcmb_crust`/`mynewtonSys` from the same hardened module rather than
  `shoote.py`'s copies once those are deleted.

### Keep as-is (pending their own tests, not touched by this port)

- `shoot_mercmodel_nosic` / `J_mercmodel_nosic` — the no-inner-core shooting
  function itself (not its residual wiring, which is touched above) has no
  `shootp.py` equivalent; keep the physics, swap only the solver call it
  rides on.
- The Debye/Grüneisen thermal helpers (`CvC`, `debye3`, `Eth`, `gammaC`,
  `thetaC`, `cheval`) — unused by anything in `shootp.py`/`driverp.py`
  today; not exercised by Stage 1's constraint-mode port either (Stage 1 has
  no thermal-energy budget yet — that's Stage 2). Keep them in place, flag
  as untested (§5.3), do not delete, do not extend.
- `get_mass_mantle` — trivial (`rhom*(rmantle**3-rcmb**3)`), already used by
  both the constraint-mode residual and `drivere.py`; keep, add a one-line
  unit test as part of Stage 1's test plan (trivial but currently untested).

## 4. Test plan

Per `PROJECT_RULES.md` rule 5 (name regression- vs truth-class) and rule 10
(new code ships with tests in the same change):

| Test | Class | What it checks |
|---|---|---|
| Core-mass/mantle-mass/`chi_li_in` held constant across one snapshot step | **truth** (exact algebraic identity: the constraint-mode residual drives these three quantities to zero by construction — `|core_mass - core_mass_fix| < tol` etc. is not a regression, it's the solver's own convergence criterion restated as a test) | Run one step from a converged present-day model at the existing `xtol`/`ftol`; assert the three conserved quantities match the `.h5`'s own `misc` values to solver tolerance. |
| Snow-zone bound continuity | **regression** (no independent truth for "should the layer persist between adjacent steps" — Stage 1 doesn't model that; this just checks the existing per-step `isnow`/`isnowcmb` classification is internally self-consistent, e.g. `isnowcmb==1` implies `isnow in (1,2)`) | Assert the existing invariant the code already encodes (`shoote.py:180-189`/`shootp.py:206-216`'s `if isnow==1 or isnow==2` gate) holds on every step of a short sweep. |
| Zero-elapsed-step round-trip | **truth** (an analytic limit: stepping `r_icb` by 0 km should reproduce the present-day model's own `r_cmb`/`T_cmb`/profile to solver tolerance, since the constraint-mode residual at the present-day `r_icb` is satisfied by the present-day solution itself) | Take a converged present-day `.h5`, run the ported snapshot solver at `r_icb = r_icb_present_day` (no decrement), diff its outputs against the `.h5`'s own stored profile. This is the single highest-value test in this list — it is the thing that proves the port preserves the original method, not just that it runs. |
| `get_mass_mantle` unit test | **truth** (trivial closed-form) | `get_mass_mantle(rcmb, rm, rhom) == rhom*(rm**3-rcmb**3)` for a couple of hand-picked values. |
| `shoot_mercmodel_nosic` switch-over: last `r_icb>0` step vs first `r_icb<=0` step | **regression**, flagged explicitly as such (no independent truth oracle for continuity across the two different parameterizations — see Risks §5.2) | Assert `T_cmb`/`r_cmb` do not jump discontinuously (some tolerance TBD by the owner) across the switch; if they do, that is a recorded, not silently accepted, finding. |
| Existing xfail (`test_planet_evolution_mode_would_ideally_work`) flips to pass once `planet_input.py:119`'s `mod_type`→`code_mode` typo is fixed | n/a (locking test, already exists) | Owned by whoever lands the `planet_input.py` fix (likely bundled with item 9's refactor, see §5.4) — not this design doc's deliverable, but the gate that proves Stage 1 is reachable at all. |

No bitwise-identity-to-`shoote.py` test is proposed: `shoote.py`'s own
Newton solver (16% identical to `shootp.py`'s) is the thing being replaced
*because* it is unhardened, so matching its exact numeric output on
non-pathological inputs is a weak target — the zero-elapsed-step round-trip
against the present-day `.h5` (a truth-class check) is the stronger anchor
and should gate the port instead.

## 5. Risks

**5.1 — "No time axis" gap.** Stage 1 alone, if shipped under the banner
"evolution mode works again," will likely be read by a reviewer or the
owner as giving Mercury's interior at a real past time. It does not — it is
indexed by `r_icb`/`T_cmb`, with no `dt`. This must be stated loudly in
whatever lands (README, CHANGELOG, docstring on the entry point) — the
owner-endorsed direction already treats Stage 2 as separate and later; the
risk is that gap getting lost between this design doc and the eventual PR
description.

**5.2 — `shoot_mercmodel_nosic` switch-over discontinuity.** The two
branches are parameterized differently (`r_icb` directly vs. central
superheat `Tctrplus` above the liquidus) and solve genuinely different
systems (6 unknowns/3-plus-mass-chi constraints vs. 5 unknowns/2-plus-mass-chi
constraints). Nothing in today's code checks that the last `r_icb>0` step's
`T_cmb` and the first `r_icb<=0` step's `T_cmb` are close; they may not be.
This is a real physics risk, not just a code-cleanliness one — route to
rafael-santos if the Stage 1 implementation surfaces a visible jump, since
that is a question about whether the no-inner-core parameterization is
itself matched to the with-inner-core one at the handoff, not a bug in
either branch alone.

**5.3 — Unvalidated Debye/Grüneisen thermal helpers.** `CvC`, `debye3`,
`Eth`, `gammaC`, `thetaC` have zero test coverage today and are not
exercised by Stage 1 (no thermal-energy budget yet). They will become
load-bearing in Stage 2. Flagging now so Stage 2's estimate (§6) budgets
time for validating them before they are relied on, rather than discovering
mid-Stage-2 that `debye3`'s truncated series (`maxdeg=7`, "truncated to save
computation time") or `cheval`'s Chebyshev evaluation has never been checked
against an independent value.

**5.4 — Sequencing risk against item 9.** Item 9 (kai-fischer, in flight,
branch `item9-refactor-libcore`, PR #24) is refactoring `libCore.py` and
`globalvar.py` concurrently. Stage 1's implementation touches exactly those
modules (plus `planet_input.py`, to fix the `mod_type`→`code_mode` bug that
blocks reaching the `'e'` branch at all) and a Stage 1 PR opened before item
9 lands risks merge conflicts or, worse, silently assuming a pre-refactor
`libCore.py`/`globalvar.py` signature that item 9 changes out from under it.
**Implementation of Stage 1 is sequenced to start only after item 9's
refactor of `libCore.py`/`globalvar.py` lands and the fast tiers re-gate
green** — this design pass itself is not blocked (it is docs, reading only),
but the first Stage 1 code PR should rebase onto item 9's merge commit, not
onto today's `main`.

**5.5 — `chi_li_in` conservation target may not be independently meaningful
once Stage 2 adds mass loss/gain terms** (e.g., does the core's light
element content stay perfectly conserved across real geologic time, or does
light-element partitioning at a growing ICB change the total slowly?). Not
a Stage 1 blocker (Stage 1 inherits the constraint from `shoote.py` as-is)
but worth flagging now so Stage 2's physics review (rafael-santos) checks
whether "total `chi_li_in` fixed across all time" is itself a Stage-1-only
simplification that Stage 2 must relax.

## 6. Per-stage effort estimate (owner-approval needed, not a commitment)

- **Stage 1** (constraint-mode port into `shootp.py`/`mynewtonSys`, new
  `driverp`-equivalent driver reusing the `.h5`/csv output convention, the
  5 tests in §4, fixing `planet_input.py:119`): **roughly 4-6 working
  sessions** — 1 for the constraint-mode residual + box/trial function
  wiring in `shootp.py`, 1 for the no-inner-core variant's equivalent port,
  1-2 for the driver/CLI/output-schema work, 1 for the test suite
  (zero-elapsed round-trip is the one likely to take longer than it looks,
  since it needs a converged present-day `.h5` fixture committed or
  generated fresh), 1 buffer for the `planet_input.py` fix + re-sequencing
  around item 9's merge.
- **Stage 2** (heat-budget integration layer: CMB heat flux, secular
  cooling, latent + gravitational energy terms, snow-zone state tracking
  across timesteps, a real `dT_cmb/dt` stepper, validating the
  Debye/Grüneisen helpers before relying on them): **roughly 10-15 working
  sessions**, with high uncertainty — this is new physics-modeling work (the
  energy-balance closure itself needs a physics review before
  implementation, likely routed to rafael-santos first), not a port, and the
  estimate should be treated as a rough order of magnitude pending that
  review, not a plan.

Both estimates are the author's rough judgment for the owner to sanity-check
and revise, not commitments.
