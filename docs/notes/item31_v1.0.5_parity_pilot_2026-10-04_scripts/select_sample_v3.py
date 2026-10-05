"""item31c: select NEW compositions (not already run in item31b's v2b/v2c
attempts) from the same `prestop_rerun_failed>0` population
(main_rerun_rows.json), to extend the matched-prestop candidate pool so it
can be mined directly for error_code 1 (NEWTON_MAXIT) and error_code 2
(SINGULAR_JACOBIAN) rows. Stratified across light element (S/Si/S+Si) the
same way v2b did; liquidus_eq is NOT stratified because the source
population (main_manifest.csv) is 100% liquidus_eq='Edmund' -- confirmed via
`cut -d, -f4 main_manifest.csv | sort -u` before this script was written
(item31c note, section 0).
"""
import json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "item18a_population_rerun_2026-10-03_scripts", "main_rerun_rows.json")
N_RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20261004331
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "item31c_sample.json")

d = json.load(open(SRC))
rows = d["rows"]
nz = [r for r in rows if r.get("prestop_rerun_failed", 0) > 0]
already = set()
for prev_name in ("item31b_sample_v2b.json", "item31b_sample_v2c.json"):
    try:
        prev = json.load(open(os.path.join(HERE, prev_name)))
        already |= set((r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"]) for r in prev)
    except FileNotFoundError:
        pass

by_light = {}
for r in nz:
    key = (r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"])
    if key in already:
        continue
    by_light.setdefault(r["light"], []).append(r)

random.seed(SEED)
for lt in by_light:
    random.shuffle(by_light[lt])

picked = []
lights = sorted(by_light)
per_light = max(1, N_RUNS // len(lights))
for lt in lights:
    picked += by_light[lt][:per_light]
if len(picked) < N_RUNS:
    rest = [r for lt in lights for r in by_light[lt][per_light:]]
    random.shuffle(rest)
    picked += rest[:N_RUNS - len(picked)]
picked = picked[:N_RUNS]

sample = [dict(moi=r["moi"], CMR2=r["CMR2"], CMC=r["CMC"], light=r["light"],
               chi_Si_icb=r["chi_Si_icb"], liquidus_eq="Edmund",
               source_prestop_rerun_failed=r["prestop_rerun_failed"],
               source_prestop_rows=r["prestop_rows"])
          for r in picked]
by_lt = {}
for s in sample:
    by_lt[s["light"]] = by_lt.get(s["light"], 0) + 1
print("available new candidates by light:", {k: len(v) for k, v in by_light.items()})
print("selected %d new runs: %s" % (len(sample), by_lt))
json.dump(sample, open(OUT, "w"), indent=1)
