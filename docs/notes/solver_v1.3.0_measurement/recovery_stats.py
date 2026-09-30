"""Recovery statistics (line search + continue-after-failure) with Clopper-Pearson CIs.
usage: recovery_stats.py  -> uses the invariant run (14 cases) + any finished 37-case partials."""
import json, glob, collections, sys
import numpy as np
from scipy.stats import beta
S = "/tmp/claude-16759/-home-utig5-dliu-PIE/9c4a8cf5-0ff3-4504-be1f-683a9c776a0a/scratchpad/"
W = "/home/utig5/dliu/PIE/.claude/worktrees/v1.3.0-line-search/"


def cp(k, n, a=0.05):
    if n == 0: return float("nan"), float("nan")
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return lo, hi


def summarize(title, per_case, pub_rows_of):
    """per_case: {name: (published_class, rows)}; counts radii beyond the published/v1.2.0 stop."""
    print(f"\n=== {title}")
    byclass = collections.defaultdict(lambda: dict(n=0, conv=0, adm=0, inadm=0, fail=collections.Counter(), cases=0, cases_adm=0))
    for name, (cls, rows) in per_case.items():
        npub = pub_rows_of(name)
        b = byclass[cls]; b["cases"] += 1; any_adm = False
        for r in rows:
            if r["k"] < npub: continue
            b["n"] += 1
            if r["status"] == "ok":
                b["conv"] += 1
                if 0 <= r["chi_li_icb"] <= r["chi_max"] and not r.get("err_flag", False):
                    b["adm"] += 1; any_adm = True
                else:
                    b["inadm"] += 1
            else:
                b["fail"][r.get("error_name")] += 1
        b["cases_adm"] += any_adm
    tot = dict(n=0, conv=0, adm=0, inadm=0, cases=0, cases_adm=0)
    print(f"{'published class (end/where)':28s} cases  radii  converged (CI95)      admissible (CI95)     inadmissible  failures")
    for cls, b in sorted(byclass.items()):
        lo2, hi2 = cp(b["conv"], b["n"]); lo, hi = cp(b["adm"], b["n"])
        print(f"{cls:28s} {b['cases']:5d}  {b['n']:5d}  {b['conv']:4d} ({lo2:.2f}-{hi2:.2f})   {b['adm']:4d} ({lo:.2f}-{hi:.2f})   {b['inadm']:6d}        {dict(b['fail'])}")
        for k in tot: tot[k] += b[k]
    lo2, hi2 = cp(tot["conv"], tot["n"]); lo, hi = cp(tot["adm"], tot["n"])
    print(f"TOTAL: cases={tot['cases']} radii beyond stop={tot['n']}; converged={tot['conv']} ({lo2:.2f}-{hi2:.2f}); admissible={tot['adm']} ({lo:.2f}-{hi:.2f}); inadmissible={tot['inadm']}; cases with >=1 admissible recovered radius: {tot['cases_adm']}/{tot['cases']} ({cp(tot['cases_adm'], tot['cases'])[0]:.2f}-{cp(tot['cases_adm'], tot['cases'])[1]:.2f})")
    return byclass


# --- invariant sample (14 cases, capped at v1.2.0 rows + 2)
ref = json.load(open(W + "testsys/reference/v1_2_0_sweeps/v1_2_0_sweeps.json"))["cases"]
cur = json.load(open(S + "v130_invariant_run2.json"))["cases"]
sample = {c["name"]: c for c in json.load(open(W + "testsys/reference/v1_2_0_sweeps/sample.json"))}
cls_of = lambda pc: pc.split("/")[2] + ("/10m" if pc.endswith("10m") else "/later")
per_case = {n: (cls_of(sample[n]["published_class"]), c["rows"]) for n, c in cur.items()}
summarize("invariant sample: 14 cases, radii beyond the v1.2.0 stop (max 2 per case)", per_case,
          lambda n: sum(r["status"] == "ok" for r in ref[n]["rows"]))
dt_ok = [r["dt_s"] for c in cur.values() for r in c["rows"] if r["status"] == "ok"]
dt_f = [r["dt_s"] for c in cur.values() for r in c["rows"] if r["status"] != "ok"]
print("runtime per radius (s, contended host, 8 workers): converged median %.0f (n=%d); failed radius (warm+cold attempts) median %.0f (n=%d)" % (np.median(dt_ok), len(dt_ok), np.median(dt_f), len(dt_f)))

# --- 37-case full-grid measurement, whatever has finished
files = sorted(glob.glob(S + "measure36_partial/*.json"))
if files:
    cases36 = {c["name"]: c for c in json.load(open(S + "cases36.json"))}
    pc = {}
    for f in files:
        d = json.load(open(f)); n = d["case"]["name"]
        pc[n] = (cls_of(cases36[n]["published_class"]), d["rows"])
    b = summarize(f"37-case full-grid measurement, PARTIAL: {len(files)}/37 cases finished (continue policy, radii beyond the published stop)", pc,
                  lambda n: cases36[n]["published_rows"])
    # adaptive continuation (report only)
    tried = rec = 0
    for f in files:
        for r in json.load(open(f))["rows"]:
            a = r.get("adaptive")
            if a: tried += 1; rec += bool(a["recovered"])
    print(f"adaptive continuation (report only, first 2 failures per case): tried={tried} recovered={rec} CI95 {cp(rec, tried)[0]:.2f}-{cp(rec, tried)[1]:.2f}" if tried else "adaptive: none tried yet")
    for f in files:
        d = json.load(open(f)); rows = d["rows"]
        print("  ", d["case"]["name"], "pub rows", cases36[d['case']['name']]["published_rows"], "-> ok", sum(r["status"] == "ok" for r in rows), "/", len(rows),
              "admissible", sum(1 for r in rows if r["status"] == "ok" and 0 <= r["chi_li_icb"] <= r["chi_max"] and not r["err_flag"]),
              "wall %.0f s" % sum(r["dt_s"] for r in rows))
