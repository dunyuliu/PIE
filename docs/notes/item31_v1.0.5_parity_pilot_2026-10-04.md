# Item 31 — v1.0.5-vs-HEAD convergence-regression pilot (2026-10-04)

**Scope: PILOT ONLY**, ~20-40 radii across 14 stratified compositions, NOT the
full 6,964-radius regression population. Read-only diagnosis; `pie/shootp.py`
and the Zenodo v1.0.5 copy were never modified in place. Harness:
`item31_v1.0.5_parity_pilot_2026-10-04_scripts/`.

## Verdict — CORRECTED 2026-10-04 (conductor, post-audit; see addendum below)

**The original 29/30 "HEAD-over-constrains" headline below is WRONG as
stated and must not be read as evidence of Newton line-search/warm-start
over-constraint.** `verify_v105_root.py` only reproduced `mercmodel_box`
(`pie/shootp.py:319-358`, the bounded-Newton's MID-SOLVE trial-rejection
rule, `CHI_MIN=None`). It never reproduced the SEPARATE, POST-CONVERGENCE
check `pie/driverp.py:287-288`: `if (chi_li<0).any(): error_code[k] =
CHI_OUTSIDE_ADMISSIBLE_BOX`. That check runs on every converged solution's
full radial profile, independent of `mercmodel_box` and independent of
whether a bounded line search was even active, and it DOES enforce a chi>=0
floor — the exact opposite of what `mercmodel_box`'s `CHI_MIN=None`
disables. **All 29 of the sampled "over-constrains" cases have negative
`chi_li_icb`** (conductor-checked against the raw `classification.json`
`verify` dicts, range roughly -0.001 to -0.023), so every one of them would
ALSO be flagged `error_code=4` by HEAD's actual production code via
`driverp.py:287-288`, regardless of the bounded Newton's behavior. This is
not a Newton-robustness artifact; `pie/shootp.py:329-334`'s own docstring
already documents it as a **deliberate v1.2.0 policy decision**: 21.8% of
v1.0.5's published converged rows have negative `chi_li_icb` and are
treated as physically inadmissible under v1.2.0+, "since v1.2.0."

**Corrected classification of the 30 sampled radii:**

| Classification | Count | % |
|---|---|---|
| Correctly-rejects under `mercmodel_box`'s upper (eutectic) bound | 1 | 3.3% |
| **Undetermined by this pilot — confounded by the separate, deliberate v1.2.0 chi>=0 post-hoc policy (`driverp.py:287-288`), not a test of Newton over-constraint** | 29 | 96.7% |

**Coverage caveat:** item 18/30's own population breakdown has error_code=4
(CHI_OUTSIDE_ADMISSIBLE_BOX) at ~39% of the 6,964 regressed radii, code 1
(NEWTON_MAXIT) ~10%, code 2 (SINGULAR_JACOBIAN) <0.5%, others the remainder.
This pilot's 278 candidates and 30-row sample are **100% error_code=4 by
construction** (the sampling method selected only pre-stop radii that
carried code 4) — it says nothing about the other ~61% of the regressed
population (NEWTON_MAXIT, SINGULAR_JACOBIAN, etc.), which were not sampled
and remain fully open.

**Net effect: this pilot does not confirm or refute lars-eriksson's original
over-constraint-vs-correct-rejection question for the CHI_OUTSIDE_BOX
population.** It surfaces a different, better-evidenced finding instead: the
dominant share of the sampled CHI_OUTSIDE_BOX population traces to a
documented, deliberate v1.2.0 chi>=0 admissibility policy that is orthogonal
to the bounded-Newton line-search mechanism this pilot was designed to
probe. Whether that v1.2.0 policy itself is the right physical call (v1.0.5
published rows down to chi_li_icb~-0.045 as valid) is a separate, open
physics question, not addressed here, and not something this pilot was
scoped to answer.

---

### Original (superseded) verdict text, kept for audit trail — DO NOT read as current

Of 30 sampled "pre-stop" radii (v1.0.5 converged and published a row; HEAD's
own sweep reaches the same radius via warm-start and records
`error_code=4`, CHI_OUTSIDE_ADMISSIBLE_BOX):

| Classification | Count | % |
|---|---|---|
| **HEAD-over-constrains** | 29 | 96.7% |
| HEAD-correctly-rejects | 1 | 3.3% |
| inconclusive/other | 0 | 0% |

**lars-eriksson's hypothesis is not supported at pilot scale.** The dominant
failure mode is the opposite of "v1.3.0 correctly rejects a root v1.0.5
wrongly accepted": in 29/30 sampled cases, v1.0.5's root is admissible under
**HEAD's own** `mercmodel_box` rule, converges to residual norm 1e-11..1e-7,
and is physically sane (finite Picb, rcmb>ricb) — yet HEAD's production
sweep still records `error_code=4` at that exact radius. One case (3.3%) is
a genuine correct rejection: `chi_li_icb=0.12174 > chi_max=0.12` (Si, exceeds
by 0.0017).

Across all 14 sampled compositions, 278 pre-stop candidates were found and
**100% carry `head_error_code=4`** (none `MISSING`, no other error code
appeared) — consistent with item18a's finding that the regression is
CHI_OUTSIDE_ADMISSIBLE_BOX-dominated. **[SUPERSEDED: this 100% figure is a
sampling artifact of this pilot's own candidate selection, not a population
statistic — see coverage caveat above.]**

## Methodology

1. 14 compositions sampled (genova/margot x S / S+Si(2 chi values) / Si),
   stratified from `item18a_population_rerun_2026-10-03_scripts/main_rerun_rows.json`
   run-level fields (the item18a per-radius CSVs were reaped; a fresh sample
   was re-run rather than trying to reconstruct a non-existent file).
2. For each composition, v1.0.5 (`~/shared_dataset/zenodo.16459292/extracted/PIE/src`,
   vendored into a scratch copy, never edited in place in the read-only tree)
   and HEAD (`pie/`, pinned venv) were each run in their **own subprocess**
   (never imported into the same process), same CLI args, same cwd-local
   `./results/`.
3. v1.0.5's `src/shootp.py::mynewtonSys` (scratch copy) was instrumented to
   dump one JSONL record per converged radius (`ricb`, full 5-vector `x`,
   `normf`) — the Newton algorithm itself untouched, only debug I/O added.
4. Radii match exactly in meters between the two codebases: both use
   `rs = np.arange(1e1, 2e6, dr)` with `dr=50e3` (`pie/main.py:158`;
   identical in v1.0.5's `main.py`) and `scale['a'] = rm = 2439360.0`
   constant across all compositions — no interpolation needed.
5. `classify.py::prestop_candidates` matches each v1.0.5-converged radius to
   HEAD's `pMetaData_<chi>.csv` row at the same `ricb` (meters) and flags
   `error_code != 0`.
6. **Independent verification never trusts v1.0.5's own "converged" flag.**
   `verify_v105_root.py` re-imports v1.0.5's own `shootp.py::shoot_mercmodel`
   in a fresh process and recomputes `f`/`fout` from the dumped root vector,
   then applies **HEAD's own admissibility rule, exactly**:
   `pie/shootp.py:317-358` (`mercmodel_box`) — finite f/fout, `rcmb>ricb`,
   `chi<=chi_max` — and, critically, **no `chi>=0` lower bound**, because
   `pie/shootp.py:360`: `CHI_MIN = None` (disabled by design; see that
   file's own docstring: 21.8% of v1.0.5's published converged rows have
   negative `chi_li_icb`, and a lower bound would break the v1.2.0 identity
   invariant). An earlier draft of this pilot's verifier used item18a's
   broader admissible-set definition (`chi_li_icb>=0` AND `<=chi_max`); that
   produced the OPPOSITE verdict (29/30 "HEAD-correctly-rejects") purely
   because it enforced a bound HEAD's live code does not enforce — flagged
   here as a cautionary methodological note, corrected before this verdict
   was drawn (Pattern-3-style oracle mismatch, caught before being reported).

## Evidence (representative, full 30-row dump in `classification.json`)

```
genova Si   ricb=250010 m  chi_li_icb=-0.00850  chi_max=0.1200  rcmb=1935194  normf=3.5e-11  -> admissible, yet HEAD error_code=4
margot S+Si ricb=200010 m  chi_li_icb=-0.01086  chi_max=0.1230  rcmb=1935717  normf=1.5e-11  -> admissible, yet HEAD error_code=4
genova Si   ricb=1450010 m chi_li_icb= 0.12174  chi_max=0.1200  rcmb=1998827  normf=4.1e-7   -> genuinely inadmissible (chi>chi_max)
```

File:line evidence:
- `pie/shootp.py:317-358` — `mercmodel_box`, the exact rejection rule
  reproduced by the verifier.
- `pie/shootp.py:360` — `CHI_MIN = None` and its docstring rationale.
- v1.0.5 reference `src/shootp.py` lines 253-313 (`mynewtonSys`) — pure
  unconstrained Newton, no line search, no box check, confirming v1.0.5
  never screens for `chi<=chi_max` either; the admissible-box concept is
  entirely a v1.3.0 addition layered on top of warm-start sweeping.

## Interpretation — why "admissible root exists" but HEAD still reports error_code=4

The 29 over-constrained cases are NOT evidence that `mercmodel_box`'s
boundary itself is wrong (the admissible v1.0.5 root does satisfy HEAD's own
box). The likely mechanism is **warm-start path dependence**: HEAD's Newton
at this radius starts from `v_last` (the previous radius's HEAD solution,
which itself diverges from v1.0.5's unconstrained trajectory once any prior
radius differs), and its *own* trial iterates during line-search backtracking
apparently leave the box before alpha backtracking (`ALPHA_MIN=1e-3`,
`pie/shootp.py:303`) recovers a path to the same admissible root — i.e. a
convergence-robustness gap in the bounded Newton's line search / warm-start
policy, not a box-definition bug. This pilot did not instrument HEAD's own
per-iterate trial trajectory (only its final csv row), so this mechanism is
inferred, not directly observed — **recommended next step (not applied
here):** add the same per-iterate JSONL dump to `pie/shootp.py::mynewtonSys`
(mirroring what was done to the v1.0.5 scratch copy) and diff iterate-by-
iterate against v1.0.5's trajectory for 2-3 of the 29 over-constrained
cases, to confirm whether the failure is in the line-search backtracking,
the warm-start choice of `v_last`, or elsewhere. Any resulting fix must ship
behind a flag or as a bit-identical no-op per the standing integrator rule,
and is OUT OF SCOPE for this pilot.

## Cost estimate — full 6,964-radius (1,400-run) population on knox

Per-pilot measurements (14 runs, sequential v1.0.5-then-HEAD within each
`run_one` call):
- v1.0.5 subprocess: mean 244s / median 233s per composition (~40 radii).
- HEAD subprocess: mean 161s / median 166s per composition.
- Per-run wall time (sequential pair): ~405s (6.75 min).
- Verification step (`verify_v105_root.py`): sub-second per radius; for the
  full 6,964 confirmed-regressed radii this adds <2h even run serially.

The regression population is driven by the 1,400 reruns in
`item18a_population_rerun_2026-10-03_scripts/main_rerun_rows.json`
(`n_sample=1400`), which produced the 23,608 pre-stop / 6,964 regressed
radii — i.e. the unit of parallel work is the **1,400 compositions**, not
the 6,964 radii directly.

| Workers (`PIE_WORKERS`) | Wall time for 1,400 runs |
|---|---|
| 8 (this pilot's setting) | ~1400/8 x 405s ≈ 19.7 h |
| 16 | ~9.8 h |
| 24 | ~6.6 h |
| 32 (half of knox's 64 cores, the standing cap) | ~4.9 h |

Box has 64 cores (`nproc`); other users' jobs were observed concurrently
running during this pilot (5+ live `pie p` / v1.0.5 processes from a sibling
session), so 32 is an upper bound, not a safe default — recommend capping at
16-24 and checking `nproc`-minus-current-load at launch time, per the
standing half-cores-including-other-processes rule.

**This estimate is NOT a go-ahead to launch the full run — reporting back to
the conductor per the dispatch, not scaling up.**

## Conductor verification addendum (2026-10-04)

Independently re-derived the 29/1 split by hand from `classification.json`'s
raw `verify` sub-dicts (not the stored `label` field) for both the
over-constrains and correctly-rejects representative cases quoted above —
matches exactly. priya-nair independently re-derived the full 30-row split
the same way (29/1, no discrepancies) and confirmed the 278-candidate /
100%-`head_error_code=4` aggregate against `classification.json`'s top-level
`n_candidates_total`/`by_head_error_code` fields (the conductor read these
directly: `n_candidates_total: 278`, `by_head_error_code: {'4.0': 278}` — a
full-population count, not sample-derived, resolving priya's own flagged
caveat that the 30-row sample alone can't prove it).

lars-eriksson's read-only review (file:line) found a real latent bug:
`verify_v105_root.py:42` checks only `np.all(np.isfinite(f))`, omitting the
`fout` finiteness check `pie/shootp.py:343`'s own `mercmodel_box` rule
requires. A case with non-finite `fout` would get a NaN `chi_max`, making
`chi_li_icb <= chi_max` silently `False` and misclassifying a NONFINITE_SHOOT
failure as `HEAD-correctly-rejects`. **Checked against all 30 sampled rows:
zero have a None/NaN `chi_max` (all 24 distinct values are well-formed
floats), so this pilot's 29/1 verdict is unaffected.** This is a required fix
before any full 6,964-radius run — a NONFINITE_SHOOT case is plausible at
that scale and would silently misattribute cause. (`classify.py:86`'s
hardcoded `"error_code ?"` string in the `reason` field is cosmetic only —
the correct `head_error_code` is always stored as its own JSON field, this
only affects the free-text reason string.)
