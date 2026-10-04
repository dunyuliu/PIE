"""
Item 18(b) figure comparison -- step 1: materialize row-level CSVs.

Builds, per MoI range (high=margot, low=genova):
  - recovered_all_{high,low}MoI.csv : the rows beyond item 18(a)'s
    `published_rows` stop index, restricted to S+Si/chi_Si_icb>0 (the
    paper's sample scope per jordan-kim's note section 0), converged
    (error_code==0), chi_S_bulk>0 (sort_models.py's "all" row filter).
    Same column schema as the published Zenodo CSVs plus one extra
    `weight` column (= item 18(a)'s stratified N_h/n_h, straight from
    `main_sample.csv`), so a recovered row represents `weight` population
    rows, not one. Published rows are exact population counts (weight=1
    implicitly). This is the same Horvitz-Thompson weighting
    jordan-kim's `analyze.py::estimate()` uses for the headline
    percentages in her note -- reapplied here per-bin instead of
    aggregated, so a per-bin sum below reproduces her per-category totals
    (point estimates, not the CI) as a cross-check.

These are a read-derived CACHE (reruns are stable; this script is
idempotent and does not mutate any read-only source): item 18(a)'s
pie/results/ tree (agent-a7d2fd536939b904f worktree, read-only) and the
published Zenodo bundle (read-only) are the only inputs.

Downstream (make_figures.py) derives all five sort_models.py categories
(all/sl/goodTCMB/goodTCMB_sl/goodTCMB_goodchiS) from this cache plus the
published CSVs by applying the identical row predicates jordan-kim's
analyze.py used -- not reimplemented differently here.
"""
import csv
from pathlib import Path

import pandas as pd

import os
ZEN = Path(os.path.expanduser(
    "~/shared_dataset/zenodo.16459292/extracted/Plotting and Analysis Scripts/For Monte Carlo Study"))
ITEM18A = Path(__file__).resolve().parent.parent / "item18a_population_rerun_2026-10-03_scripts"
import os as _os
RESULTS = Path(_os.environ.get(
    "PIE_ITEM18A_RAW_RESULTS",
    "CHANGE_ME_set_PIE_ITEM18A_RAW_RESULTS_env_var_to_the_item18a_raw_results_dir"))
OUTDIR = Path(__file__).parent / "cache"
OUTDIR.mkdir(exist_ok=True)

MOI_MAP = {"margot": "high", "genova": "low"}
# Published CSV column schema (all_models_*MoI.csv header), reused verbatim
# so recovered rows concat cleanly onto the published dataframes.
SCHEMA = ["chi_Si_icb", "rhom", "mass", "moi", "cmc", "Picb", "Tcmb", "isnow",
          "isnowcmb", "chi_li_in", "chi_S_bulk", "Pcmb", "chi_li_eut_icb",
          "chi_li_eut_cmb", "ricb", "rcmb", "core_mass", "chi_li_icb", "error_code"]


def main():
    sample_rows = list(csv.DictReader(open(ITEM18A / "main_sample.csv")))
    sample_rows = [r for r in sample_rows if r["light"] == "S+Si" and float(r["chi_Si_icb"]) > 0]

    recovered = {"high": [], "low": []}
    missing = 0
    for r in sample_rows:
        tag = MOI_MAP[r["moi"]]
        d = RESULTS / "CMR2_{:.17f}_CMC_{:.17f}_{}_Edmund".format(float(r["CMR2"]), float(r["CMC"]), r["light"])
        chi = float(r["chi_Si_icb"])
        cf = d / "pMetaData_{:.2f}.csv".format(chi)
        if not cf.exists():
            missing += 1
            continue
        rows = list(csv.DictReader(open(cf)))
        pub_n = int(r["csv_rows"])
        beyond = rows[pub_n:]
        w = float(r["weight"])
        for x in beyond:
            if int(float(x["error_code"])) != 0:
                continue
            if float(x["chi_S_bulk"]) <= 0:
                continue
            rec = {k: x[k] for k in SCHEMA}
            rec["weight"] = w
            recovered[tag].append(rec)

    for tag in ("high", "low"):
        df = pd.DataFrame(recovered[tag], columns=SCHEMA + ["weight"])
        for col in SCHEMA + ["weight"]:
            df[col] = pd.to_numeric(df[col])
        outp = OUTDIR / f"recovered_all_{tag}MoI.csv"
        df.to_csv(outp, index=False)
        print(tag, "recovered rows:", len(df), "->", outp)
    print("sample_runs", len(sample_rows), "missing_csv", missing)


if __name__ == "__main__":
    main()
