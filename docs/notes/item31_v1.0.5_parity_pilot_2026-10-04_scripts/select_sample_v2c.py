"""item31b round 2: select_sample_v2b.py's top-prestop_rerun_failed selection
(20 runs, chi_Si_icb mostly 0.00) turned up 495 code4 vs only 1 code1 and 0
code2 matched-prestop candidates -- a second, broader random draw (different
seed, no sort-by-magnitude bias) to check whether that is representative or
an artifact of the first draw's composition skew."""
import json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "item18a_population_rerun_2026-10-03_scripts", "main_rerun_rows.json")
N_RUNS = 18
SEED = 777

d = json.load(open(SRC))
rows = d["rows"]
nz = [r for r in rows if r.get("prestop_rerun_failed", 0) > 0]
already = set()
try:
    prev = json.load(open(os.path.join(HERE, "item31b_sample_v2b.json")))
    already = set((r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"]) for r in prev)
except FileNotFoundError:
    pass
random.seed(SEED)
random.shuffle(nz)
picked = []
for r in nz:
    key = (r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"])
    if key in already:
        continue
    picked.append(r)
    if len(picked) >= N_RUNS:
        break
sample = [dict(moi=r["moi"], CMR2=r["CMR2"], CMC=r["CMC"], light=r["light"],
               chi_Si_icb=r["chi_Si_icb"], source_prestop_rerun_failed=r["prestop_rerun_failed"],
               source_prestop_rows=r["prestop_rows"])
          for r in picked]
print("selected", len(sample), "new runs")
json.dump(sample, open(os.path.join(HERE, "item31b_sample_v2c.json"), "w"), indent=1)
