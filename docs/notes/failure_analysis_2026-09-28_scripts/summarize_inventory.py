import json, sys, collections
import numpy as np
inv = json.load(open(sys.argv[1]))
RS = np.arange(1e1, 2e6, 50e3)
for moi in ("margot", "genova"):
    logs = inv[moi]["logs"]; dirs = inv[moi]["dirs"]
    print(f"\n===== {moi}: {len(logs)} logs, {len(dirs)} draws with result dirs")
    nseg = collections.Counter(v["nseg"] for v in logs.values())
    print("segments per log:", dict(nseg))
    # per-label end state
    end = collections.defaultdict(collections.Counter)
    nrad = collections.defaultdict(list)
    lastr = collections.defaultdict(collections.Counter)
    for key, v in logs.items():
        for s in v["segs"]:
            end[s["label"]][s["end"]] += 1
            nrad[s["label"]].append(s["nrad"])
            if s["end"] != "finish":
                lastr[s["label"]][s["last_r"]] += 1
    print(f"{'label':12s} {'finish':>7s} {'newton':>7s} {'detJ0':>6s} {'crash':>6s} {'siexc':>6s}  median_nrad  fail@10m  fail@50km..  fail>=1500km")
    for lab in sorted(end):
        c = end[lab]
        lr = lastr[lab]
        f10 = lr.get(10.0, 0); f50 = sum(n for r, n in lr.items() if 10 < r < 1.5e6); fbig = sum(n for r, n in lr.items() if r >= 1.5e6)
        print(f"{lab:12s} {c['finish']:7d} {c['newton_maxit']:7d} {c['detJ0']:6d} {c['crash_stderr']:6d} {c['si_exceed']:6d}  {np.median(nrad[lab]):8.0f}     {f10:5d}  {f50:5d}  {fbig:5d}")
    # distribution of the radius at which a model died (all labels, excluding si_exceed)
    allr = collections.Counter()
    for v in logs.values():
        for s in v["segs"]:
            if s["end"] not in ("finish", "si_exceed"):
                allr[(s["last_r"], s["end"])] += 1
    print("death (last radius attempted, end) top:", sorted(allr.items(), key=lambda x: -x[1])[:14])
    # rows in csv vs radii attempted
    nrows_hist = collections.Counter()
    ec1 = 0; ec2 = 0; totrows = 0; zero_rows = collections.Counter(); maxr = collections.Counter()
    for key, d in dirs.items():
        for lab, m in d.items():
            nrows_hist[m["nrows"]] += 1; ec1 += m["n_ec1"]; ec2 += m["n_ec2"]; totrows += m["nrows"]
            if m["nrows"] == 0: zero_rows[lab] += 1
            maxr[m["max_ricb"]] += 1
    print("csv files:", sum(nrows_hist.values()), "total rows:", totrows, "error_code1 rows:", ec1, "ec2:", ec2)
    print("nrows histogram:", sorted(nrows_hist.items()))
    print("zero-row csvs by label:", dict(zero_rows))
    print("max ricb (km) histogram:", sorted(((-1 if k is None else k / 1e3), v) for k, v in maxr.items()))
    # consistency: rows == nrad-1 (last attempted radius failed) ?
    mism = 0; tot = 0
    for key, v in logs.items():
        d = dirs.get(key)
        if d is None: continue
        for s in v["segs"]:
            m = d.get(s["label"])
            if m is None: continue
            tot += 1
            expect = s["nrad"] if s["end"] == "finish" else s["nrad"] - 1
            if m["nrows"] != expect: mism += 1
    print("log-vs-csv row-count mismatches:", mism, "of", tot)
    # CMR2/CMC of draws where S (chi 0) model died at 10 m vs converged
    pts = collections.defaultdict(list)
    for key, v in logs.items():
        c1, c2 = map(float, key.split(","))
        for s in v["segs"]:
            pts[(s["label"], s["end"], s["last_r"] == 10.0)].append((c1, c2))
    for lab in ("S_0.00", "Si_0.00", "S+Si_0.05"):
        for k2 in sorted(k for k in pts if k[0] == lab):
            arr = np.array(pts[k2])
            print(f"  {lab} {k2[1]:14s} at10m={k2[2]!s:5s} n={len(arr):4d} CMR2 range {arr[:,0].min():.4f}-{arr[:,0].max():.4f} mean {arr[:,0].mean():.4f}")
