import csv
from pathlib import Path
ITEM18A = Path(__file__).resolve().parent.parent / "item18a_population_rerun_2026-10-03_scripts"
import os as _os
RESULTS = Path(_os.environ.get(
    "PIE_ITEM18A_RAW_RESULTS",
    "CHANGE_ME_set_PIE_ITEM18A_RAW_RESULTS_env_var_to_the_item18a_raw_results_dir"))
sample_rows = list(csv.DictReader(open(ITEM18A/"main_sample.csv")))
sample_rows = [r for r in sample_rows if r["light"]=="S+Si" and r["moi"]=="genova" and float(r["chi_Si_icb"])>0]
for r in sample_rows:
    d = RESULTS / "CMR2_{:.17f}_CMC_{:.17f}_{}_Edmund".format(float(r["CMR2"]), float(r["CMC"]), r["light"])
    cf = d / "pMetaData_{:.2f}.csv".format(float(r["chi_Si_icb"]))
    rows = list(csv.DictReader(open(cf)))
    beyond = rows[int(r["csv_rows"]):]
    conv = [x for x in beyond if int(float(x["error_code"]))==0]
    picked = [x for x in conv if float(x["chi_S_bulk"])>0 and int(float(x["isnow"])) in (1,3)]
    if picked:
        x = picked[0]
        print("run:", cf)
        print("published_rows=", r["csv_rows"], "row_index_in_sweep=", rows.index(x))
        print(dict((k,x[k]) for k in ("ricb","Tcmb","isnow","chi_S_bulk","error_code")))
        is_goodT = 1700<=float(x["Tcmb"])<=2100
        print("sl=True goodTCMB=", is_goodT, "goodTCMB_sl=", is_goodT, "goodTCMB_goodchiS=", is_goodT and float(x["chi_S_bulk"])<0.02)
        print("heatmap-eligible (ricb<=1800010)?", float(x["ricb"])<=1800010.0)
        break
