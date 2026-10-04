"""Item 18(a) stage 2 -- stratified, size-weighted sampling design over the
census sampling frame (census_runs.csv, non-finished runs only; `finish` and
by-design `si_exceed` excluded), written as a pie/robust_runner.py manifest.

Allocation: proportional to stratum size N_h (largest-remainder rounding)
with a floor of `--min` per stratum (capped at N_h), draws without replacement
inside each stratum with a fixed seed. The sample csv keeps the stratum label
and the design weight N_h/n_h so stage-4 estimates can be weighted back to
the population.

  pilot  strata = (moi, mode, stage)          -- timing only (72 runs)
  main   strata = (moi, composition, mode)    -- the estimate (93 strata).
         Stage is NOT an allocation variable: the pilot showed admissible
         recoveries are rare events, so precision is set by runs per
         composition, and (moi, composition, mode, stage) would be 400+
         strata whose floor alone exceeds the wall-time budget. Stage stays
         in the sample csv as a descriptive variable.
         (--exclude-manifest: leave out runs already in an earlier manifest;
         not used for main -- pilot runs are in the main frame and resume for
         free via robust_runner's sentinels.)

Usage:
  python3 design.py pilot --n 72 --seed 20261003
  python3 design.py main --n 1600 --min 10 --seed 20261004
Outputs: <name>_manifest.csv (robust_runner format), <name>_sample.csv,
<name>_design.json.
"""
import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXCLUDED_MODES = ("finish", "si_exceed")


def load_frame():
    rows = list(csv.DictReader(open(HERE / "census_runs.csv")))
    return [r for r in rows if r["mode"] not in EXCLUDED_MODES]


def job_key(r):
    return (r["moi"], r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"])


def allocate(sizes, n, floor):
    """Proportional allocation with per-stratum floor and largest-remainder rounding."""
    keys = sorted(sizes)
    base = {k: min(sizes[k], floor) for k in keys}
    rest = n - sum(base.values())
    if rest < 0:
        raise ValueError(f"n={n} smaller than the floors' total {sum(base.values())}")
    room = {k: sizes[k] - base[k] for k in keys}
    tot_room = sum(room.values())
    quota = {k: (rest * room[k] / tot_room if tot_room else 0.0) for k in keys}
    alloc = {k: base[k] + int(quota[k]) for k in keys}
    left = n - sum(alloc.values())
    for k in sorted(keys, key=lambda k: -(quota[k] - int(quota[k]))):
        if left <= 0:
            break
        if alloc[k] < sizes[k]:
            alloc[k] += 1
            left -= 1
    return alloc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=["pilot", "main"])
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--min", type=int, default=1)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--exclude-manifest", default=None)
    a = ap.parse_args()

    frame = load_frame()
    if a.exclude_manifest:
        ex = {(r["moi"], r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"])
              for r in csv.DictReader(open(HERE / a.exclude_manifest.replace("_manifest.csv", "_sample.csv")))}
        frame = [r for r in frame if job_key(r) not in ex]

    def stratum(r):
        return (r["moi"], r["mode"], r["stage"]) if a.name == "pilot" else (r["moi"], r["composition"], r["mode"])

    groups = defaultdict(list)
    for r in frame:
        groups[stratum(r)].append(r)
    sizes = {k: len(v) for k, v in groups.items()}
    alloc = allocate(sizes, a.n, a.min)
    rng = random.Random(a.seed)
    sample = []
    for k in sorted(groups):
        picked = rng.sample(sorted(groups[k], key=job_key), alloc[k])
        for r in picked:
            r = dict(r)
            r["stratum"] = "|".join(k)
            r["N_h"] = sizes[k]
            r["n_h"] = alloc[k]
            r["weight"] = sizes[k] / alloc[k]
            sample.append(r)

    with open(HERE / f"{a.name}_manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["CMR2", "CMC", "light_element", "liquidus_eq", "chi_Si_icb", "seed"])
        for r in sample:
            w.writerow([r["CMR2"], r["CMC"], r["light"], "Edmund",
                        repr(float(r["chi_Si_icb"])) if r["light"] == "S+Si" else "", ""])
    with open(HERE / f"{a.name}_sample.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sample[0].keys()))
        w.writeheader()
        w.writerows(sample)
    design = dict(name=a.name, n_requested=a.n, n_sampled=len(sample), floor=a.min, seed=a.seed,
                  frame_size=len(frame), n_strata=len(sizes), excluded_manifest=a.exclude_manifest,
                  strata={"|".join(k): dict(N_h=sizes[k], n_h=alloc[k]) for k in sorted(sizes)})
    json.dump(design, open(HERE / f"{a.name}_design.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in design.items() if k != "strata"}))
    full = sum(1 for k in sizes if alloc[k] == sizes[k])
    print(f"strata fully enumerated: {full}/{len(sizes)}; min n_h {min(alloc.values())}, max {max(alloc.values())}")


if __name__ == "__main__":
    main()
