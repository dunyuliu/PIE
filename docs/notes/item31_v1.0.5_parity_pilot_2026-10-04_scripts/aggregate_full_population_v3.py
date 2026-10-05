import json, os
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "..", "item18a_population_rerun_2026-10-03_scripts", "main_rerun_rows.json")))
rows = d["rows"]
print("total compositions (runs):", len(rows))
prestop_failed_total = sum(r.get("prestop_rerun_failed", 0) for r in rows)
prestop_rows_total = sum(r.get("prestop_rows", 0) for r in rows)
beyond_rows_total = sum(r.get("beyond_rows", 0) for r in rows)
n_prestop_failed_comps = sum(1 for r in rows if r.get("prestop_rerun_failed", 0) > 0)
beyond_code_totals = Counter()
for r in rows:
    for k, v in r.get("beyond_error_codes", {}).items():
        beyond_code_totals[k] += v
print("prestop_rows_total (published-converged radii matched):", prestop_rows_total)
print("prestop_rerun_failed_total (regressed radii):", prestop_failed_total)
print("compositions with prestop_rerun_failed>0:", n_prestop_failed_comps)
print("beyond_rows_total:", beyond_rows_total)
print("beyond_error_codes totals (full 1400-composition population):", dict(sorted(beyond_code_totals.items())))
