import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "item18a_population_rerun_2026-10-03_scripts", "main_rerun_rows.json")
d = json.load(open(SRC))
rows = d["rows"]
nz = [r for r in rows if r.get("prestop_rerun_failed", 0) > 0]
already = set()
for prev_name in ["item31b_sample_v2b.json", "item31b_sample_v2c.json", "item31c_trial_sample.json"]:
    try:
        prev = json.load(open(os.path.join(HERE, prev_name)))
        already |= set((r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"]) for r in prev)
    except FileNotFoundError:
        pass
rest = [r for r in nz if (r["CMR2"], r["CMC"], r["light"], r["chi_Si_icb"]) not in already]
print(len(nz), len(already), len(rest))
sample = [dict(moi=r["moi"], CMR2=r["CMR2"], CMC=r["CMC"], light=r["light"], chi_Si_icb=r["chi_Si_icb"],
               liquidus_eq="Edmund", source_prestop_rerun_failed=r["prestop_rerun_failed"],
               source_prestop_rows=r["prestop_rows"]) for r in rest]
json.dump(sample, open(os.path.join(HERE, "item31c_full_sample.json"), "w"), indent=1)
print("wrote", len(sample))
