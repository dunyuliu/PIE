import csv, json, math, os, glob
from collections import defaultdict
from pathlib import Path
import numpy as np
ZEN = Path("/home/utig5/dliu/shared_dataset/zenodo.16459292/extracted/Plotting and Analysis Scripts/For Monte Carlo Study")
ITEM18A = Path("/home/utig5/dliu/PIE/docs/notes/item18a_population_rerun_2026-10-03_scripts")
RESULTS = Path("/home/utig5/dliu/PIE/.claude/worktrees/agent-a7d2fd536939b904f/pie/results")
HEATMAP_MAX_RICB = 1800010.0

MOI_MAP = {"margot": "high", "genova": "low"}
CATS = ["all", "sl", "goodTCMB", "goodTCMB_sl", "goodTCMB_goodchiS"]
CSV_NAMES = {
    "all": "all_models_{}MoI.csv",
    "sl": "snowlayer_{}MoI.csv",
    "goodTCMB": "goodTCMB_{}MoI.csv",
    "goodTCMB_sl": "goodTCMB_snowlayer_{}MoI.csv",
    "goodTCMB_goodchiS": "goodTCMB_goodchiS_{}MoI.csv",
}

published = defaultdict(lambda: defaultdict(int))
published_maxricb = defaultdict(float)
for moi, tag in MOI_MAP.items():
    for cat in CATS:
        path = ZEN / CSV_NAMES[cat].format(tag)
        with open(path) as f:
            for row in csv.DictReader(f):
                chi = round(float(row["chi_Si_icb"]), 2)
                published[(moi, chi)][cat] += 1
                if cat == "all":
                    published_maxricb[(moi, chi)] = max(published_maxricb[(moi, chi)], float(row["ricb"]))

sample_rows = list(csv.DictReader(open(ITEM18A / "main_sample.csv")))
sample_rows = [r for r in sample_rows if r["light"] == "S+Si" and float(r["chi_Si_icb"]) > 0]

def comp_key(r):
    return (r["moi"], round(float(r["chi_Si_icb"]), 2))

coldcheck = json.load(open(ITEM18A / "main_coldcheck.json"))
flip_to_nosnow = defaultdict(int)
root_disagree = defaultdict(int)
for e in coldcheck["summary"]["isnow_disagree"]:
    comp = e["comp"]
    chi = round(float(comp.split("_")[-1]), 2)
    key = (e["moi"], chi)
    root_disagree[key] += 1
    if e["cold"] == 0:
        flip_to_nosnow[key] += 1

per_run = []
missing = 0
for r in sample_rows:
    d = RESULTS / "CMR2_{:.17f}_CMC_{:.17f}_{}_Edmund".format(float(r["CMR2"]), float(r["CMC"]), r["light"])
    chi = float(r["chi_Si_icb"])
    cf = d / "pMetaData_{:.2f}.csv".format(chi)
    if not cf.exists():
        missing += 1
        continue
    rows = list(csv.DictReader(open(cf)))
    pub_n = int(r["csv_rows"])
    beyond = rows[pub_n:]
    conv = [x for x in beyond if int(float(x["error_code"])) == 0]
    out = dict(moi=r["moi"], chi=round(chi, 2), stratum=r["stratum"], N_h=int(r["N_h"]), n_h=int(r["n_h"]))
    for cat in CATS:
        out[cat + "_full"] = 0
        out[cat + "_hm"] = 0
    out["snow_flip_full"] = 0
    out["snow_flip_hm"] = 0
    key = comp_key(r)
    avail_flip = flip_to_nosnow.get(key, 0)
    for x in conv:
        chiS = float(x["chi_S_bulk"])
        if chiS <= 0:
            continue
        isnow = int(float(x["isnow"]))
        tcmb = float(x["Tcmb"])
        ricb = float(x["ricb"])
        is_sl = isnow in (1, 3)
        is_goodT = 1700 <= tcmb <= 2100
        is_goodT_sl = is_goodT and is_sl
        is_goodT_chiS = is_goodT and chiS < 0.02
        hm = ricb <= HEATMAP_MAX_RICB
        flags = [("all", True), ("sl", is_sl), ("goodTCMB", is_goodT), ("goodTCMB_sl", is_goodT_sl), ("goodTCMB_goodchiS", is_goodT_chiS)]
        for cat, flag in flags:
            if flag:
                out[cat + "_full"] += 1
                if hm:
                    out[cat + "_hm"] += 1
        if is_sl and avail_flip > 0:
            out["snow_flip_full"] += 1
            if hm:
                out["snow_flip_hm"] += 1
            avail_flip -= 1
    per_run.append(out)

def estimate(rows, field):
    by_comp = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_comp[(r["moi"], r["chi"])][r["stratum"]].append(r)
    est = {}
    for comp, strata in by_comp.items():
        A, varA, n, N = 0.0, 0.0, 0, 0
        for key, rr in strata.items():
            N_h, n_h = rr[0]["N_h"], len(rr)
            a = np.array([x[field] for x in rr], float)
            w = N_h / n_h
            A += w * a.sum()
            if n_h > 1:
                fpc = 1 - n_h / N_h
                varA += N_h ** 2 * fpc * a.var(ddof=1) / n_h
            n += n_h
            N += N_h
        est[comp] = dict(A=A, ci95=[A - 1.96 * math.sqrt(varA), A + 1.96 * math.sqrt(varA)], n=n, N=N)
    return est

results = {}
for cat in CATS:
    for suf in ("full", "hm"):
        results[cat + "_" + suf] = estimate(per_run, cat + "_" + suf)
results["snow_flip_full"] = estimate(per_run, "snow_flip_full")
results["snow_flip_hm"] = estimate(per_run, "snow_flip_hm")

root_disagree_by_comp = defaultdict(int)
for (moi, chi), v in root_disagree.items():
    root_disagree_by_comp[(moi, round(chi, 2))] += v

out = dict(
    published={"%s|%.2f" % (moi, chi): dict(d) for (moi, chi), d in published.items()},
    published_maxricb={"%s|%.2f" % (moi, chi): v for (moi, chi), v in published_maxricb.items()},
    estimates={cat: {"%s|%.2f" % (moi, chi): v for (moi, chi), v in est.items()} for cat, est in results.items()},
    root_disagree_by_comp={"%s|%.2f" % (moi, chi): v for (moi, chi), v in root_disagree_by_comp.items()},
    n_sample_runs=len(sample_rows), n_missing_csv=missing, n_per_run=len(per_run),
)
json.dump(out, open("docs/notes/item18b_paper_filter_recompute_2026-10-04_scripts/item18b_results.json", "w"), indent=1)
print("sample_runs", len(sample_rows), "missing_csv", missing, "per_run", len(per_run))
