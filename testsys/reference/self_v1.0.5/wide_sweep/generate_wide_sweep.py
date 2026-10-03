#!/usr/bin/env python3
"""Regenerate wide_sweep.json -- see PROVENANCE.md in this directory.

Run from the repo root:
    PYTHONNOUSERSITE=1 MPLBACKEND=Agg /usr/bin/python3 \\
        testsys/reference/self_v1.0.5/wide_sweep/generate_wide_sweep.py
"""
import concurrent.futures as cf
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "testsys"))
# `pie` itself is not sys.path-inserted (board item 28e): it is installed
# (`uv pip install -e .`), so no chdir/sys.path trick is needed to import it.

from pielib import solve_full_model, pool_workers  # noqa: E402

MOI_CONFIGS = [(0.346, 0.426), (0.333, 0.443)]  # Margot, Genova
COMPOSITIONS = [
    ("S", "Edmund", None), ("S", "Steinbruegge", None),
    ("Si", "Edmund", None), ("Si", "Steinbruegge", None),
    ("S+Si", "Edmund", 0.01), ("S+Si", "Steinbruegge", 0.01),
]
RADII_M = [150_010.0, 400_010.0, 650_010.0]


def _job(args):
    CMR2, CMC, light, liq, ricb_m, chi_si = args
    try:
        result = solve_full_model(CMR2, CMC, light, liq, ricb_m, chi_Si_icb=chi_si)
        return {
            "CMR2": CMR2, "CMC": CMC, "light_element": light, "liquidus_eq": liq,
            "ricb_m": ricb_m, "chi_Si_icb": chi_si, "converged": True,
            "scalars": result["scalars"], "profiles": result["profiles"],
        }
    except BaseException as e:  # noqa: BLE001 -- mynewtonSys uses sys.exit()
        return {
            "CMR2": CMR2, "CMC": CMC, "light_element": light, "liquidus_eq": liq,
            "ricb_m": ricb_m, "chi_Si_icb": chi_si, "converged": False,
            "error": repr(e),
        }


def main():
    jobs = [(CMR2, CMC, light, liq, ricb_m, chi_si)
            for CMR2, CMC in MOI_CONFIGS
            for light, liq, chi_si in COMPOSITIONS
            for ricb_m in RADII_M]
    t0 = time.time()
    with cf.ProcessPoolExecutor(max_workers=pool_workers(32)) as ex:
        results = list(ex.map(_job, jobs))
    print(f"{len(jobs)} cases in {time.time()-t0:.1f}s; "
          f"{sum(r['converged'] for r in results)} converged")
    out_path = HERE / "wide_sweep.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
