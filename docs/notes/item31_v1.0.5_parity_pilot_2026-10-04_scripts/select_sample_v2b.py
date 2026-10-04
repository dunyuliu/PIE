"""item31b (corrected selection): the earlier select_sample_v2.py picked
compositions by HEAD's AGGREGATE 'beyond_error_codes' (run-level dict over
radii BEYOND where v1.0.5's own fresh sweep stopped) -- but a direct check
(see item31b note) showed NEWTON_MAXIT/SINGULAR_JACOBIAN in that tail NEVER
co-occurs with a v1.0.5-converged radius at the same ricb (v1.0.5 crashes
via sys.exit() at its own first failure, so it simply never reaches those
radii at all -- there is no v1.0.5 root to compare against there).

The actual target population (the prompt's "6,964 regressed radii", and
item18a's own `prestop_rerun_failed` field) is PRESTOP radii: where v1.0.5's
PUBLISHED sweep converged, but HEAD's rerun at that same radius did not
reproduce a clean converge. This selects compositions by `prestop_rerun_failed`
count (not `beyond_error_codes`), so re-running them actually surfaces
candidates in the right population; the resulting codes (1/2/4/other) at
those specific radii are read off HEAD's own fresh csv once run_pair_v2 has
re-executed each composition (not assumed here).
"""
import json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "item18a_population_rerun_2026-10-03_scripts", "main_rerun_rows.json")
N_RUNS = 20
SEED = 20261004

if __name__ == "__main__":
    d = json.load(open(SRC))
    rows = d["rows"]
    nz = [r for r in rows if r.get("prestop_rerun_failed", 0) > 0]
    print("runs with prestop_rerun_failed>0: %d (total failed radii across them: %d)" %
          (len(nz), sum(r["prestop_rerun_failed"] for r in nz)))
    random.seed(SEED)
    random.shuffle(nz)
    # stratify lightly across light element so S/Si/S+Si are all represented
    by_light = {}
    for r in nz:
        by_light.setdefault(r["light"], []).append(r)
    picked = []
    lights = sorted(by_light)
    per_light = max(1, N_RUNS // len(lights))
    for lt in lights:
        picked += by_light[lt][:per_light]
    if len(picked) < N_RUNS:
        rest = [r for r in nz if r not in picked]
        picked += rest[:N_RUNS - len(picked)]
    picked = picked[:N_RUNS]
    sample = [dict(moi=r["moi"], CMR2=r["CMR2"], CMC=r["CMC"], light=r["light"],
                   chi_Si_icb=r["chi_Si_icb"], source_prestop_rerun_failed=r["prestop_rerun_failed"],
                   source_prestop_rows=r["prestop_rows"])
              for r in picked]
    print("selected %d runs, total prestop_rerun_failed in selection: %d" %
          (len(sample), sum(r["source_prestop_rerun_failed"] for r in sample)))
    json.dump(sample, open(os.path.join(HERE, "item31b_sample_v2b.json"), "w"), indent=1)
