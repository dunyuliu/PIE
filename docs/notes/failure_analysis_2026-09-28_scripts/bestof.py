import json, glob, collections, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
cases = json.load(open(HERE + "/cases.json")); ck = lambda c: json.dumps([c["CMR2"], c["CMC"], c["light"], c.get("chi", 0.0)])
tags = ["base", "ls", "clamp", "clamp_rest", "start50", "maxit40", "eps5", "cold"]
res = collections.defaultdict(dict)
for t in tags:
    for f in glob.glob(f"{HERE}/runs/{t}/*.json"):
        d = json.load(open(f))
        if "recs" not in d: continue
        k = json.dumps([d["CMR2"], d["CMC"], d["light"], d["chi"]])
        ok = sum(r["status"] == "ok" for r in d["recs"]); last = d["recs"][-1]
        nf = min([h["nf"] for h in last.get("hist", [])] or [float("nan")])
        res[k][t] = (ok, last["status"], nf)
byclass = collections.defaultdict(list)
for c in cases:
    k = ck(c); pub = (c["nrad"] - 1) if c["end"] != "finish" else c["nrad"]
    byclass[c["cls"]].append((pub, max((v[0] for v in res[k].values()), default=0), res[k]))
print("class | n | mean published rows | mean best-of rows | n improved | n improved by >=5 radii | n unchanged")
for cls in sorted(byclass):
    L = byclass[cls]
    print(f"{cls:40s} {len(L)} {np.mean([p for p,_,_ in L]):5.1f} {np.mean([b for _,b,_ in L]):5.1f} {sum(b>p for p,b,_ in L)} {sum(b>=p+5 for p,b,_ in L)} {sum(b==p for p,b,_ in L)}")
print("\nPer-variant: n cases with MORE rows than published / FEWER / same (variant alone, not best-of)")
for t in tags[1:]:
    more = fewer = same = 0
    for c in cases:
        r = res[ck(c)].get(t)
        if r is None: continue
        pub = (c["nrad"] - 1) if c["end"] != "finish" else c["nrad"]
        more += r[0] > pub; fewer += r[0] < pub; same += r[0] == pub
    print(f"  {t:12s} more={more:3d} fewer={fewer:3d} same={same:3d} (n={more+fewer+same})")
print("\nResidual floor (min |f| over all variants) for 10-m cases never recovered (no converged radius under any variant):")
for c in cases:
    if "/10m" not in c["cls"]: continue
    r = res[ck(c)]
    if max(v[0] for v in r.values()) > 0: continue
    fl = [v[2] for v in r.values() if v[2] == v[2]]
    print(f"  {c['cls']:40s} CMR2={c['CMR2']:.4f} min|f|={min(fl):.1e}  statuses={sorted(set(v[1] for v in r.values()))}")
