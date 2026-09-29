#!/usr/bin/env python3
"""run_batch.py cases.json tag [probe opts...]  -> runs/<tag>/<i>.json ; 16 workers, nice."""
import json, sys, os, subprocess, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__))
cases = json.load(open(sys.argv[1])); tag = sys.argv[2]; opts = sys.argv[3:]
outdir = f"{HERE}/runs/{tag}"; os.makedirs(outdir, exist_ok=True)
env = dict(os.environ, PYTHONNOUSERSITE="1", MPLBACKEND="Agg", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")

def job(ic):
    i, c = ic
    out = f"{outdir}/{i:03d}.json"
    if os.path.exists(out): return i, "cached"
    chi = c.get("chi", 0.0)
    cmd = ["nice", "-n", "10", "/usr/bin/python3", f"{HERE}/probe.py", repr(c["CMR2"]), repr(c["CMC"]), c["light"], "Edmund", str(chi), out] + opts
    r = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=7200)
    if not os.path.exists(out):
        json.dump(dict(case=c, opts=opts, crashed=r.stdout[-1500:]), open(out, "w"))
    return i, r.stdout.strip().split("\n")[-1][-120:]

with cf.ProcessPoolExecutor(max_workers=int(os.environ.get("NW", "16"))) as ex:
    for i, msg in ex.map(job, list(enumerate(cases))):
        print(i, cases[i]["cls"], msg, flush=True)
