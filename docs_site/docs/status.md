# Project status

A short summary of recently closed engineering and verification work, for
readers who don't need the full internal working board
(`PATHWAY_FORWARD.md`). This page is a paraphrase, not a mirror -- it does
not republish the board verbatim, and it will drift behind the board
between releases.

## Packaging and layout

- The repository was reorganised from a flat `src/` tree into an
  installable `pie` package (`pyproject.toml`, editable `uv` install), with
  operational scripts split out into `util/plot/` and `util/run/`.
- `pie/robust_runner.py` -- a resumable batch runner with provenance
  logging, for large Monte Carlo ensembles on a shared box or TACC
  Lonestar6 -- was added and then hardened (a stale-lock race and a
  partial-row observability gap were both found and fixed).

## Solver correctness and robustness

- The present-day Newton solver gained a bounded line search, so a sweep
  across radii continues past an individual radius's failure instead of
  stopping the whole composition; failed radii are now recorded as rows
  (with an `error_code`) rather than silently truncating the output.
- A crash class where a non-finite inner-core-boundary density escaped the
  solver's own error handling and killed an entire sweep was found and
  fixed, with regression tests added.

## Science-impact verification (Dunnigan et al. 2026)

- A multi-pass, independently re-derived investigation into whether
  previously-discarded (non-converging) solver cases biased the paper's
  snow-layer-fraction results was carried through to closure: the
  recovered cases were re-solved, the resulting shift in the paper's
  headline figures was found to be within existing confidence intervals,
  and the owner decided no erratum or comment is warranted. No disputed
  number was ever sent to a coauthor during the investigation.
- A separate audit of an alternative meshing/loading path against the
  reference path found no discrepancy warranting a code change.

## Process

- CI runs a fast gate (unit + contract + integration) on every push and
  PR, plus a non-blocking canary against unpinned current dependencies,
  and opt-in slower e2e/wide-sweep jobs on a schedule or manual dispatch.
- Branch protection and a machine-local-path-hygiene pre-commit hook are
  in place.
