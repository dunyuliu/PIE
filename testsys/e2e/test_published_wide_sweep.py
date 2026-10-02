"""E2E tier (marker `published_wide`): a wide, UNCURATED sample of the
full published Monte Carlo dataset, read directly from
`~/shared_dataset/zenodo.16459292/extracted/PIE/` -- never copied (the
project convention: published datasets live once in `~/shared_dataset`,
projects reference them). Skipped with a clear reason when that path is
absent (e.g. CI, which has no access to another user's shared cache;
see testsys/reference/zenodo_v1.0.5/mc_wide/ for the small CURATED
slice that IS committed and runs everywhere).

Samples SAMPLE_PER_CELL directories (fixed seed, deterministic) from
each of 6 cells (2 MOI x {S, Si, S+Si}, liquidus Edmund -- the only one
in this dataset), re-solves the first converged row of each (or
confirms non-convergence, for the many MC draws that have zero rows --
see mc_wide/PROVENANCE.md), and gates all 19 scalars.
"""
import concurrent.futures as cf
import csv
import os
import pathlib
import random

import pytest

from conftest import solve_full_model, assert_scalars_match, check_converged_without_reference, pool_workers

pytestmark = [pytest.mark.e2e, pytest.mark.published_wide]

SHARED_ROOT = pathlib.Path("~/shared_dataset/zenodo.16459292/extracted/PIE").expanduser()
SAMPLE_PER_CELL = int(os.environ.get("PIE_PUBLISHED_WIDE_N", "40"))
SEED = 20260928


if not SHARED_ROOT.is_dir():
    pytest.skip(
        f"~/shared_dataset/zenodo.16459292/extracted/PIE not found on this "
        f"machine -- the published_wide tier only runs where the shared, "
        f"read-only dataset cache is mounted (not in CI); see "
        f"testsys/reference/zenodo_v1.0.5/mc_wide/ for the committed, "
        f"curated slice that DOES run in CI.",
        allow_module_level=True,
    )


def _sample_dirs():
    rng = random.Random(SEED)
    cases = []
    for moi in ("margot", "genova"):
        base = SHARED_ROOT / f"work.{moi}" / "results"
        for light in ("S", "Si", "S+Si"):
            candidates = sorted(p for p in base.iterdir()
                                 if p.name.endswith(f"_{light}_Edmund"))
            chosen = rng.sample(candidates, min(SAMPLE_PER_CELL, len(candidates)))
            cases.extend((moi, light, p) for p in chosen)
    return cases


def _parse_cmr2_cmc(dirname):
    # "CMR2_<x>_CMC_<y>_<light>_Edmund"
    parts = dirname.split("_")
    return float(parts[1]), float(parts[3])


def _load_first_row(case_dir, light):
    fname = "pMetaData_0.05.csv" if light == "S+Si" else "pMetaData_0.00.csv"
    path = case_dir / fname
    if not path.is_file():
        return None
    with open(path) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    return {k: float(v) for k, v in rows[0].items()}


def _job(case):
    moi, light, case_dir = case
    cmr2, cmc = _parse_cmr2_cmc(case_dir.name)
    reference = _load_first_row(case_dir, light)
    chi_si = 0.05 if light == "S+Si" else None
    if reference is None:
        try:
            result = solve_full_model(cmr2, cmc, light, "Edmund", 10.0, chi_Si_icb=chi_si)
            return ("recovered", result, None)
        except BaseException as e:  # noqa: BLE001
            return ("expected_nonconvergence", None, None)
    try:
        result = solve_full_model(cmr2, cmc, light, "Edmund",
                                   reference["ricb"], chi_Si_icb=chi_si)
        return ("converged", result["scalars"], reference)
    except BaseException as e:  # noqa: BLE001
        return ("unexpected_nonconvergence", repr(e), reference)


def test_published_wide_sample_matches():
    cases = _sample_dirs()
    with cf.ProcessPoolExecutor(max_workers=pool_workers(32)) as ex:
        results = list(ex.map(_job, cases))

    failures = []
    n_converged_checked = 0
    n_nonconvergent_guarded = 0
    recovered = []
    inadmissible = []  # converged where published had 0 rows, but chi outside [0, bound] (error_code 4)
    for (moi, light, case_dir), (status, payload, reference) in zip(cases, results):
        label = f"{moi}/{light}/{case_dir.name}"
        if reference is None:
            if status == "expected_nonconvergence":
                n_nonconvergent_guarded += 1
            else:
                # Published run recorded zero rows; v1.3.0 converges at the
                # same first radius (10 m). Intended recovery (item 17):
                # gated by the validity checks, tagged "recovered".
                try:
                    kind = check_converged_without_reference(payload, context=f"{label}: ")
                    (recovered if kind == "recovered" else inadmissible).append(
                        f"{label} chi_li_icb={payload['scalars']['chi_li_icb']:.4f}")
                except AssertionError as e:
                    failures.append(str(e))
            continue
        if status != "converged":
            # HARD gate since v1.3.0 (board item 19): the ricb=10 m
            # singular-LU flake (B5) is fixed by the getk2 nrs=0 index fix,
            # so a fresh failure where the published run converged is a
            # regression, whatever its signature.
            failures.append(f"{label}: published converges, fresh solve "
                             f"status={status!r} ({payload!r})")
            continue
        if {payload["isnow"], reference["isnow"]} == {2.0, 3.0}:
            payload = dict(payload, isnow=reference["isnow"])  # see mc_wide test
        try:
            # check_error_code=False: reference is a published Zenodo
            # row, predates PATHWAY_FORWARD.md item 16's error codes --
            # see test_mc_wide_parity.py's identical carve-out.
            assert_scalars_match(payload, reference, rtol=1e-4, context=f"{label}: ",
                                  check_error_code=False)
            n_converged_checked += 1
        except AssertionError as e:
            failures.append(str(e))

    print(f"\npublished_wide: {len(cases)} sampled, "
          f"{n_converged_checked} converged+matched, "
          f"{n_nonconvergent_guarded} non-convergence reproduced, "
          f"{len(recovered)} recovered (published 0 rows, v1.3.0 converges, admissible), "
          f"{len(inadmissible)} converged-inadmissible (chi outside [0, bound], error_code 4), "
          f"{len(failures)} hard failures")
    for m in recovered:
        print(f"  recovered: {m}")
    for m in inadmissible:
        print(f"  inadmissible: {m}")
    assert not failures, "\n".join(failures)
