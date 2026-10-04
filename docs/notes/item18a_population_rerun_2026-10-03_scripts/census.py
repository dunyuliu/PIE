"""Item 18(a) stage 1 -- population census of the published Dunnigan et al. 2026
Monte Carlo runs (docs/notes/item18a_population_rerun_2026-10-03.md).

One "run" = one `main.py p CMR2 CMC light Edmund [chi_Si]` process = one
pMetaData_<chi>.csv. Each MC draw has 18 runs (S+Si chi_Si 0.00..0.15, S, Si).

Classification (reused from failure_analysis_2026-09-28_scripts/inventory.py,
end-of-segment markers in results/log.<CMR2>.<CMC>.txt; the stdout logs are
the only record of a failure -- published error_code is 0 on every row):
  finish        "Finish simulating model"
  newton_maxit  "Solution not found within tolerance"      (Mode D)
  detJ0         "Zero Determinant"                         (Mode A)
  si_exceed     "Exceeding allowed maximum Si"             (Mode F, by design)
  crash_*       none of the above: uncaught traceback to the launcher stderr
                log (Mode B singular LU, or Mode C IndexError in getk2). The
                stderr log carries no per-run identity (tracebacks only), so
                B vs C CANNOT be attributed per run from the published
                artefacts; the launcher-log totals (margot a.log.o2494644:
                4037 singular / 213 IndexError; genova a.log.o2491704:
                7749 / 532) are recorded as the only B/C split available and
                the script FAILS unless singular+IndexError == crash total.
                Split used here instead, by the last attempted radius:
                crash_at_1.95Mm  -- the geometric-limit (Mode C) candidates
                                    (failure_analysis note section 1.2: the
                                    IndexError fires "at 1.95 Mm"); 129/374
                                    runs vs 213/532 IndexErrors, so Mode C
                                    also fires at earlier radii -- on a Newton
                                    ITERATE's rcmb (getk2's nrs uses the trial
                                    v[2]), not the converged one. Only the
                                    re-run (v1.3.0+ error_code per radius) can
                                    attribute those.
                crash_lt_1.95Mm  -- all other tracebacks (Mode B, plus Mode C
                                    on an iterate).
Stage = last attempted radius: 10m / 50km-1.45Mm / >=1.5Mm / finished.

Outputs (next to this script):
  census_runs.csv      one row per run -- the sampling frame for stage 2
  census_summary.json  per (moi, composition, mode) counts + stage split +
                       cross-checks + totals

Zenodo tree is read-only; nothing is written there.
"""
import csv
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ZENODO = Path(os.path.expanduser("~/shared_dataset/zenodo.16459292/extracted/PIE"))
RS = np.arange(1e1, 2e6, 50e3)
LABELS = [("S+Si", f"{c:.2f}") for c in np.linspace(0, 0.15, 16)] + [("S", "0.00"), ("Si", "0.00")]
LAUNCHER = {"margot": "a.log.o2494644", "genova": "a.log.o2491704"}  # authoritative (failure_analysis note section 0)
MODE_C_RADIUS = 1950010.0


def comp_label(light, chi):
    return light if light in ("S", "Si") else f"S+Si_{chi}"


def stage_of(end, last_r):
    if end == "finish":
        return "finished"
    if last_r <= 10.0:
        return "10m"
    return "50km-1.45Mm" if last_r < 1.5e6 else ">=1.5Mm"


def census_moi(moi):
    res = ZENODO / f"work.{moi}" / "results"
    runs = []
    for lf in sorted(glob.glob(f"{res}/log.*.txt")):
        m = re.match(r"log\.([0-9.e-]+)\.(0\.[0-9e-]+)\.txt", os.path.basename(lf))
        cmr2, cmc = float(m.group(1)), float(m.group(2))
        txt = open(lf, errors="replace").read()
        segs = [s for s in re.split(r"(?=Finding solutions for inner core radius = 10\.0 )", txt)
                if s.startswith("Finding solutions")]
        if len(segs) != 18:
            raise RuntimeError(f"{lf}: {len(segs)} segments, expected 18")
        for i, s in enumerate(segs):
            light, chi = LABELS[i]
            radii = [float(x) for x in re.findall(r"Finding solutions for inner core radius = ([0-9.]+)", s)]
            if "Finish simulating model" in s:
                end = "finish"
            elif "Solution not found within tolerance" in s:
                end = "newton_maxit"
            elif "Zero Determinant" in s:
                end = "detJ0"
            elif "Exceeding allowed maximum Si" in s:
                end = "si_exceed"
            else:
                end = "crash_at_1.95Mm" if radii[-1] == MODE_C_RADIUS else "crash_lt_1.95Mm"
            d = res / "CMR2_{:.17f}_CMC_{:.17f}_{}_Edmund".format(cmr2, cmc, light)
            cf = d / f"pMetaData_{chi}.csv"
            if not cf.exists():
                raise RuntimeError(f"missing csv {cf}")
            with open(cf) as f:
                nrows = sum(1 for _ in f) - 1
            expect = len(radii) if end == "finish" else len(radii) - 1
            runs.append(dict(moi=moi, CMR2=repr(cmr2), CMC=repr(cmc), light=light, chi_Si_icb=chi,
                             composition=comp_label(light, chi), mode=end, stage=stage_of(end, radii[-1]),
                             n_radii_attempted=len(radii), last_r_m=radii[-1], csv_rows=nrows,
                             rows_match_log=int(nrows == expect), csv=str(cf.relative_to(ZENODO))))
    return runs


def launcher_counts(moi):
    p = ZENODO / f"work.{moi}" / LAUNCHER[moi]
    txt = open(p, errors="replace").read()
    return dict(singular=txt.count("Factor is exactly singular"), indexerror=txt.count("IndexError"))


def summarize(runs):
    per = defaultdict(Counter)
    stage = defaultdict(Counter)
    for r in runs:
        key = f"{r['moi']}/{r['composition']}"
        per[key][r["mode"]] += 1
        if r["mode"] != "finish":
            stage[key][r["stage"]] += 1
    out = {}
    for key in sorted(per):
        c = per[key]
        nonfin = sum(v for k, v in c.items() if k not in ("finish", "si_exceed"))
        out[key] = dict(runs=sum(c.values()), modes=dict(sorted(c.items())), non_finished_excl_si_exceed=nonfin,
                        stage_of_non_finished=dict(sorted(stage[key].items())))
    return out


def main():
    runs = []
    checks = {}
    for moi in ("margot", "genova"):
        rr = census_moi(moi)
        runs += rr
        modes = Counter(r["mode"] for r in rr)
        lc = launcher_counts(moi)
        checks[moi] = dict(runs=len(rr), draws=len({(r["CMR2"], r["CMC"]) for r in rr}), modes=dict(modes),
                           launcher_log=LAUNCHER[moi], launcher_counts=lc,
                           rows_match_log_mismatches=sum(1 - r["rows_match_log"] for r in rr),
                           published_rows=sum(r["csv_rows"] for r in rr))
        n_crash = modes["crash_at_1.95Mm"] + modes["crash_lt_1.95Mm"]
        if n_crash != lc["singular"] + lc["indexerror"]:
            raise RuntimeError(f"{moi}: {n_crash} crash runs in stdout logs vs launcher log {lc}")
        print(moi, json.dumps(checks[moi]))
    with open(HERE / "census_runs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(runs[0].keys()))
        w.writeheader()
        w.writerows(runs)
    per = summarize(runs)
    tot = Counter()
    for r in runs:
        tot[r["mode"]] += 1
    nonfin = [r for r in runs if r["mode"] not in ("finish", "si_exceed")]
    summary = dict(zenodo=str(ZENODO), n_runs=len(runs), n_draws_per_moi=1024, modes_total=dict(tot),
                   non_finished_excl_si_exceed=len(nonfin),
                   non_finished_by_mode=dict(Counter(r["mode"] for r in nonfin)),
                   non_finished_by_moi=dict(Counter(r["moi"] for r in nonfin)),
                   radii_beyond_stop_total=int(sum(len(RS) - r["csv_rows"] for r in nonfin)),
                   published_rows_total=sum(r["csv_rows"] for r in runs),
                   cross_checks=checks, per_moi_composition=per)
    json.dump(summary, open(HERE / "census_summary.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "per_moi_composition"}, indent=1))
    for k, v in per.items():
        print(k, v["modes"], v["stage_of_non_finished"])


if __name__ == "__main__":
    main()
