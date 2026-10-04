"""Item 18(a) stages 3/4 -- join a robust_runner re-run of sampled non-finished
runs to the published Zenodo CSVs and estimate per-(MOI, composition) snow
fractions before/after (docs/notes/item18a_population_rerun_2026-10-03.md).

Same admissibility rule and the same two denominators as
item18_snowfraction_2026-10-03_scripts/resolve_and_census.py stage 3/4
(`testsys/pielib.py::is_admissible`, imported, not re-typed): (a) all
published rows, (b) published rows with chi_li_icb inside [0, chi_li_eut_icb]
(S, S+Si) or [0, max_Si] (Si). The published stage-3 census is re-derived
here and cross-checked against the committed published_census.json.

Per sampled run (one re-run pMetaData csv, 40 radii, error_code per radius):
  * rows k <  published csv_rows -> regression check vs the published rows
    (max |rel diff| of chi_li_icb/rcmb, isnow mismatches);
  * rows k >= csv_rows ("beyond the published stop") -> converged
    (error_code 0), admissible (converged and inside the box; error_code 4
    rows are by construction outside it), isnow>0 among admissible;
  * error_code histogram beyond the stop (this is what attributes the
    published Mode B/C crashes the stdout logs could not).
Stratum estimates (design weights N_h/n_h from <name>_sample.csv) give the
population totals of added admissible rows (A) and added snow rows (S) per
(moi, composition), with a stratified normal-approximation CI95 from the
per-run sample variances; strata with n_h < 10 are flagged "direction only".
"after" = (pub_snow + S) / (pub_rows + A) for each denominator.

Usage: python3 snowfraction.py <name>   (name = pilot | main; reads
<name>_sample.csv, pie/results/<model dirs>; writes <name>_rerun_rows.json,
<name>_snowfraction.json, <name>_table.md). Zenodo tree read-only.
"""
import csv
import glob
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

# pielib/globalvar rewrite sys.argv on import (they emulate `pie p ...`), so take ours first.
NAME = sys.argv[1] if len(sys.argv) > 1 else "pilot"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "testsys"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs/notes/item18_snowfraction_2026-10-03_scripts"))
os.chdir(ROOT / "pie")  # pie modules read data files relative to cwd
import resolve_and_census as rc  # noqa: E402  predecessor stage-3 helpers (comp_key, _max_si)
from pielib import is_admissible  # noqa: E402

ZENODO = rc.ZENODO
RESULTS = ROOT / "pie" / "results"
RS = np.arange(1e1, 2e6, 50e3)


def comp_key(r):
    return rc.comp_key(r["moi"], r["light"], float(r["chi_Si_icb"]))


def rerun_csv(r):
    d = RESULTS / "CMR2_{:.17f}_CMC_{:.17f}_{}_Edmund".format(float(r["CMR2"]), float(r["CMC"]), r["light"])
    chi = float(r["chi_Si_icb"]) if r["light"] == "S+Si" else 0.0
    return d / "pMetaData_{:.2f}.csv".format(chi), d / ".runner_done_{:.2f}.json".format(chi)


def adm(row, light, liq="Edmund"):
    return is_admissible({"scalars": {"chi_li_icb": float(row["chi_li_icb"]),
                                      "chi_li_eut_icb": float(row["chi_li_eut_icb"])},
                          "max_Si": rc._max_si(liq), "light_element": light, "err_flag": False})


def status_log_ends(name):
    """Last 'end' record per job from the runner status log -- the only record of
    a PROCESS_CRASHED job (robust_runner writes no sentinel and pie writes no
    csv when the process dies before its first row)."""
    out = {}
    p = RESULTS / f"{name}_status.jsonl"
    if not p.exists():
        return out
    for line in open(p):
        e = json.loads(line)
        if e.get("event") == "end":
            out[(float(e["CMR2"]), float(e["CMC"]), e["light_element"], float(e["chi_Si_icb"] or 0.0))] = e
    return out


ZERO_BEYOND = dict(beyond_rows=0, beyond_error_codes={}, beyond_converged=0, beyond_admissible=0,
                   beyond_admissible_snow=0, beyond_admissible_isnow=[], beyond_admissible_ricb_km=[],
                   beyond_admissible_chi=[], beyond_admissible_start={}, beyond_converged_inadmissible_chi=[],
                   prestop_rows=0, prestop_max_rel_diff=0.0, prestop_isnow_mismatch=0, prestop_rerun_failed=0)


def analyse_run(r, ends):
    cf, sentinel = rerun_csv(r)
    out = dict(moi=r["moi"], CMR2=r["CMR2"], CMC=r["CMC"], light=r["light"], chi_Si_icb=r["chi_Si_icb"],
               composition=r["composition"], mode=r["mode"], stage=r["stage"], stratum=r["stratum"],
               N_h=int(r["N_h"]), n_h=int(r["n_h"]), weight=float(r["weight"]), published_rows=int(r["csv_rows"]))
    if not sentinel.exists():
        key = (float(r["CMR2"]), float(r["CMC"]), r["light"], float(r["chi_Si_icb"]) if r["light"] == "S+Si" else 0.0)
        e = ends.get(key)
        if e is None:
            out["status"] = "not_done"
            return out
        # crashed in the re-run too (uncaught exception, no csv): contributes
        # zero added rows; the traceback's last frame is kept for the note.
        tail = e.get("stderr_tail", "").strip().splitlines()
        out.update(status="done", rerun_crashed=True, runner_status=e["status"], duration_s=e["duration_s"],
                   git_sha=e.get("git_sha"), git_src_dirty=e.get("git_src_dirty"),
                   crash_last_line=tail[-1] if tail else "", **ZERO_BEYOND)
        return out
    sent = json.load(open(sentinel))
    out.update(status="done", duration_s=sent["end_time"] - sent["start_time"], runner_status=sent["status"],
               git_sha=sent.get("git_sha"), git_src_dirty=sent.get("git_src_dirty"))
    new = list(csv.DictReader(open(cf)))
    pub = list(csv.DictReader(open(ZENODO / r["csv"])))
    k0 = len(pub)
    if len(new) != len(RS):
        out["n_rows_rerun"] = len(new)
        out["status"] = "unexpected_row_count"
        return out
    # regression check on the rows the published run did reach
    rel = 0.0
    isnow_mismatch = 0
    repro_fail = 0
    for k in range(k0):
        n, p = new[k], pub[k]
        if float(n["error_code"]) != 0:
            repro_fail += 1
            continue
        for col in ("chi_li_icb", "rcmb"):
            a, b = float(n[col]), float(p[col])
            rel = max(rel, abs(a - b) / max(abs(b), 1e-12))
        isnow_mismatch += int(float(n["isnow"])) != int(float(p["isnow"]))
    out.update(prestop_rows=k0, prestop_max_rel_diff=rel, prestop_isnow_mismatch=isnow_mismatch,
               prestop_rerun_failed=repro_fail)
    beyond = new[k0:]
    ec = Counter(int(float(x["error_code"])) for x in beyond)
    conv = [x for x in beyond if int(float(x["error_code"])) == 0]
    admissible = [x for x in conv if adm(x, r["light"])]
    out.update(beyond_rows=len(beyond), beyond_error_codes={str(k): v for k, v in sorted(ec.items())},
               beyond_converged=len(conv), beyond_admissible=len(admissible),
               beyond_admissible_snow=sum(int(float(x["isnow"])) > 0 for x in admissible),
               beyond_admissible_isnow=[int(float(x["isnow"])) for x in admissible],
               beyond_admissible_ricb_km=[round(float(x["ricb"]) / 1e3, 2) for x in admissible],
               beyond_admissible_chi=[float(x["chi_li_icb"]) for x in admissible],
               beyond_admissible_start=Counter(x["start"] for x in admissible),
               beyond_converged_inadmissible_chi=[float(x["chi_li_icb"]) for x in conv if not adm(x, r["light"])])
    return out


def published_census():
    """Stage 3 of the predecessor, re-derived (same rule), cross-checked."""
    agg = {}
    for moi in ("margot", "genova"):
        for d in sorted(glob.glob(f"{ZENODO}/work.{moi}/results/CMR2_*")):
            m = re.match(r"CMR2_([0-9.]+)_CMC_([0-9.]+)_(S\+Si|S|Si)_(\w+)", os.path.basename(d))
            light, liq = m.group(3), m.group(4)
            for cf in sorted(glob.glob(d + "/pMetaData_*.csv")):
                chi = float(os.path.basename(cf)[10:14])
                a = agg.setdefault(rc.comp_key(moi, light, chi), dict(n_rows=0, n_snow=0, n_adm=0, n_snow_adm=0))
                for row in csv.DictReader(open(cf)):
                    isnow = int(float(row["isnow"]))
                    ok = adm(row, light, liq)
                    a["n_rows"] += 1
                    a["n_snow"] += isnow > 0
                    a["n_adm"] += ok
                    a["n_snow_adm"] += ok and isnow > 0
    ref = json.load(open(ROOT / "docs/notes/item18_snowfraction_2026-10-03_scripts/published_census.json"))["per_composition"]
    for k, a in agg.items():
        if k in ref and any(ref[k][f] != a[f] for f in ("n_rows", "n_snow", "n_adm", "n_snow_adm")):
            raise RuntimeError(f"published census mismatch vs predecessor for {k}: {a} vs {ref[k]}")
    return agg


def estimate(rows):
    """Stratified totals + CI95 for added admissible rows (A) and added snow rows (S)."""
    by_comp = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_comp[rc.comp_key(r["moi"], r["light"], float(r["chi_Si_icb"]))][r["stratum"]].append(r)
    est = {}
    for comp, strata in by_comp.items():
        tot = dict(A=0.0, S=0.0, varA=0.0, varS=0.0, n=0, N=0, strata=0, thin_strata=0, sample_A=0, sample_S=0,
                   sample_beyond=0, sample_converged=0)
        for key, rr in strata.items():
            N_h, n_h = rr[0]["N_h"], len(rr)
            a = np.array([x["beyond_admissible"] for x in rr], float)
            s = np.array([x["beyond_admissible_snow"] for x in rr], float)
            w = N_h / n_h
            tot["A"] += w * a.sum(); tot["S"] += w * s.sum()
            if n_h > 1:
                fpc = (1 - n_h / N_h)
                tot["varA"] += N_h ** 2 * fpc * a.var(ddof=1) / n_h
                tot["varS"] += N_h ** 2 * fpc * s.var(ddof=1) / n_h
            tot["n"] += n_h; tot["N"] += N_h; tot["strata"] += 1; tot["thin_strata"] += n_h < 10
            tot["sample_A"] += int(a.sum()); tot["sample_S"] += int(s.sum())
            tot["sample_beyond"] += sum(x["beyond_rows"] for x in rr)
            tot["sample_converged"] += sum(x["beyond_converged"] for x in rr)
        tot["A_ci95"] = [tot["A"] - 1.96 * math.sqrt(tot["varA"]), tot["A"] + 1.96 * math.sqrt(tot["varA"])]
        tot["S_ci95"] = [tot["S"] - 1.96 * math.sqrt(tot["varS"]), tot["S"] + 1.96 * math.sqrt(tot["varS"])]
        est[comp] = tot
    return est


def table(pub, est):
    lines = ["| moi/composition | published rows | before isnow>0 | sampled runs n/N | sample: beyond/conv/adm/snow | est. added adm A [CI95] | est. added snow S [CI95] | after | delta (pp) [CI95] | before adm-only | after adm-only | delta (pp) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for comp in sorted(pub):
        p = pub[comp]
        if p["n_rows"] == 0 or comp not in est:
            continue
        e = est[comp]
        b = p["n_snow"] / p["n_rows"]
        A, S = e["A"], e["S"]
        af = (p["n_snow"] + S) / (p["n_rows"] + A)
        lo = (p["n_snow"] + max(0, e["S_ci95"][0])) / (p["n_rows"] + A)
        hi = (p["n_snow"] + e["S_ci95"][1]) / (p["n_rows"] + A)
        b2 = p["n_snow_adm"] / p["n_adm"]
        af2 = (p["n_snow_adm"] + S) / (p["n_adm"] + A)
        flag = f" ({e['thin_strata']}/{e['strata']} strata n<10)" if e["thin_strata"] else ""
        lines.append(f"| {comp} | {p['n_rows']} | {b:.4f} | {e['n']}/{e['N']}{flag} | "
                     f"{e['sample_beyond']}/{e['sample_converged']}/{e['sample_A']}/{e['sample_S']} | "
                     f"{A:.0f} [{max(0, e['A_ci95'][0]):.0f}, {e['A_ci95'][1]:.0f}] | {S:.0f} [{max(0, e['S_ci95'][0]):.0f}, {e['S_ci95'][1]:.0f}] | "
                     f"{af:.4f} | {100 * (af - b):+.3f} [{100 * (lo - b):+.3f}, {100 * (hi - b):+.3f}] | {b2:.4f} | {af2:.4f} | {100 * (af2 - b2):+.3f} |")
    return "\n".join(lines)


def main(name):
    sample = list(csv.DictReader(open(HERE / f"{name}_sample.csv")))
    ends = status_log_ends(name)
    rows = [analyse_run(r, ends) for r in sample]
    done = [r for r in rows if r["status"] == "done"]
    crashed = [r for r in done if r.get("rerun_crashed")]
    json.dump(dict(n_sample=len(sample), n_done=len(done),
                   statuses=dict(Counter(r["status"] for r in rows)), rows=rows),
              open(HERE / f"{name}_rerun_rows.json", "w"), indent=1, default=str)
    dur = np.array([r["duration_s"] for r in done]) if done else np.array([0.0])
    summary = dict(
        n_sample=len(sample), n_done=len(done), n_rerun_crashed=len(crashed),
        rerun_crashed_by={"|".join(k): v for k, v in Counter((r["light"], r["mode"], r["stage"]) for r in crashed).items()},
        rerun_crash_last_lines=dict(Counter(r["crash_last_line"] for r in crashed)) if crashed else {},
        wall_per_job_s=dict(mean=float(dur.mean()), median=float(np.median(dur)), p90=float(np.percentile(dur, 90)),
                            max=float(dur.max()), total_cpu_s=float(dur.sum())),
        by_stage_wall_s={st: float(np.mean([r["duration_s"] for r in done if r["stage"] == st]))
                         for st in sorted({r["stage"] for r in done})},
        prestop=dict(rows=sum(r["prestop_rows"] for r in done),
                     max_rel_diff=max((r["prestop_max_rel_diff"] for r in done), default=None),
                     isnow_mismatch=sum(r["prestop_isnow_mismatch"] for r in done),
                     rerun_failed=sum(r["prestop_rerun_failed"] for r in done)),
        beyond=dict(rows=sum(r["beyond_rows"] for r in done), converged=sum(r["beyond_converged"] for r in done),
                    admissible=sum(r["beyond_admissible"] for r in done),
                    admissible_snow=sum(r["beyond_admissible_snow"] for r in done),
                    runs_with_admissible=sum(r["beyond_admissible"] > 0 for r in done),
                    error_codes=dict(sum((Counter(r["beyond_error_codes"]) for r in done), Counter())),
                    admissible_start=dict(sum((Counter(r["beyond_admissible_start"]) for r in done), Counter()))),
        by_mode_beyond={m: dict(runs=sum(1 for r in done if r["mode"] == m),
                                beyond=sum(r["beyond_rows"] for r in done if r["mode"] == m),
                                converged=sum(r["beyond_converged"] for r in done if r["mode"] == m),
                                admissible=sum(r["beyond_admissible"] for r in done if r["mode"] == m),
                                snow=sum(r["beyond_admissible_snow"] for r in done if r["mode"] == m),
                                error_codes=dict(sum((Counter(r["beyond_error_codes"]) for r in done if r["mode"] == m), Counter())))
                        for m in sorted({r["mode"] for r in done})},
        git_shas=sorted({str(r.get("git_sha")) for r in done}),
        git_src_dirty=sorted({str(r.get("git_src_dirty")) for r in done}),
    )
    print(json.dumps(summary, indent=1, default=str))
    if name == "pilot" or len(done) < len(sample):
        json.dump(dict(summary=summary), open(HERE / f"{name}_snowfraction.json", "w"), indent=1)
        if name == "pilot":
            return
    pub = published_census()
    est = estimate(done)
    tbl = table(pub, est)
    si_adm_snow = [r for r in done if r["light"] == "Si" and r["beyond_admissible_snow"] > 0]
    json.dump(dict(summary=summary, published=pub, estimates=est,
                   si_only_admissible_snow_runs=[dict(moi=r["moi"], CMR2=r["CMR2"], isnow=r["beyond_admissible_isnow"],
                                                      chi=r["beyond_admissible_chi"]) for r in si_adm_snow]),
              open(HERE / f"{name}_snowfraction.json", "w"), indent=1, default=str)
    open(HERE / f"{name}_table.md", "w").write(tbl + "\n")
    print(tbl)


if __name__ == "__main__":
    main(NAME)
