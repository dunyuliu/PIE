"""item31b: build a stratified-by-error-code composition sample from
item18a's main_rerun_rows.json (the only surviving per-run census; the raw
per-radius CSVs from that rerun were reaped, so each selected composition is
RE-RUN fresh here via run_pair_v2.py, not read from any stale artifact).

Selects compositions (moi/CMR2/CMC/light/chi) whose 'beyond_error_codes'
(item18a's rerun, same v1.6.0 HEAD git_sha) contains code 1 (NEWTON_MAXIT,
priority), code 2 (SINGULAR_JACOBIAN), or code 4 (CHI_OUTSIDE_ADMISSIBLE_BOX,
for continuity/contrast with the original item31 pilot). One run can surface
candidate RADII of more than one code; the actual per-radius code1/code2/
code4 sample is drawn downstream (classify_v2.py) from run_pair_v2's fresh
output, not from this run-level selection, which only maximises the chance
each code is represented.
"""
import json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "item18a_population_rerun_2026-10-03_scripts", "main_rerun_rows.json")
N_CODE1_RUNS = 14
N_CODE2_RUNS = 10
N_CODE4_RUNS = 6
SEED = 20261004

if __name__ == "__main__":
    d = json.load(open(SRC))
    rows = d["rows"]
    has1 = [r for r in rows if r.get("beyond_error_codes", {}).get("1", 0) > 0]
    has2 = [r for r in rows if r.get("beyond_error_codes", {}).get("2", 0) > 0]
    has4 = [r for r in rows if r.get("beyond_error_codes", {}).get("4", 0) > 0]
    print("candidate runs: code1=%d code2=%d code4=%d (of %d total)" % (len(has1), len(has2), len(has4), len(rows)))
    random.seed(SEED)
    random.shuffle(has1); random.shuffle(has2); random.shuffle(has4)
    picked = {}
    for r in has1[:N_CODE1_RUNS]:
        picked[(r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"])] = r
    for r in has2[:N_CODE2_RUNS]:
        picked[(r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"])] = r
    for r in has4[:N_CODE4_RUNS]:
        picked[(r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"])] = r
    sample = [dict(moi=r["moi"], CMR2=r["CMR2"], CMC=r["CMC"], light=r["light"],
                   chi_Si_icb=r["chi_Si_icb"], source_beyond_error_codes=r["beyond_error_codes"])
              for r in picked.values()]
    print("deduped sample size:", len(sample))
    json.dump(sample, open(os.path.join(HERE, "item31b_sample.json"), "w"), indent=1)
