"""Bias estimate: how the published per-composition statistics change if the numerically-lost
10-m runs are recovered (recovery rate and recovered-model properties taken from the best-of
recovery batches over the stratified sample)."""
import json, glob, collections, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
tags = sys.argv[1:] or ["ls", "clamp_rest", "start50"]
inv = json.load(open(HERE + "/inventory.json"))
cases = json.load(open(HERE + "/cases.json"))
ckey = lambda c: json.dumps([c["CMR2"], c["CMC"], c["light"], c.get("chi", 0.0)])
best = {}  # case key -> (n_ok rows, isnow list, rcmb0, tag)
for tag in tags:
    for f in glob.glob(f"{HERE}/runs/{tag}/*.json"):
        d = json.load(open(f))
        if "recs" not in d: continue
        k = json.dumps([d["CMR2"], d["CMC"], d["light"], d["chi"]])
        ok = [r for r in d["recs"] if r["status"] == "ok"]
        if k not in best or len(ok) > best[k][0]:
            best[k] = (len(ok), [r["isnow"] for r in ok], ok[0]["rcmb_m"] if ok else None, tag, [r["chi_li_in"] for r in ok])
print("Recovery of published zero-row runs (best of tags", tags, "), by class:")
rec_rate = {}
for cls in sorted(set(c["cls"] for c in cases)):
    if "/10m" not in cls: continue
    cc = [c for c in cases if c["cls"] == cls]
    n = len(cc); rec = [best.get(ckey(c), (0,))[0] for c in cc]
    nrec = sum(1 for r in rec if r >= 5)
    rows = [r for r in rec if r >= 5]
    isn = [np.mean(np.array(best[ckey(c)][1]) > 0) for c in cc if best.get(ckey(c), (0,))[0] >= 5]
    rec_rate[cls] = (nrec / n, np.mean(rows) if rows else 0, np.mean(isn) if isn else float("nan"))
    print(f"  {cls:40s} recovered {nrec}/{n} (>=5 radii)  mean rows {np.mean(rows) if rows else 0:5.1f}  recovered isnow>0 frac {np.mean(isn) if isn else float('nan'):.2f}  rcmb0 km {[round(best[ckey(c)][2]/1e3) for c in cc if best.get(ckey(c),(0,))[0]>=5]}")

print("\nPublished vs. corrected per-composition statistics (rows = model radii; isnow>0 = any iron-snow state):")
print(f"{'moi/label':22s} {'draws_pub':>9s} {'lost@10m(num.)':>14s} {'est.recoverable':>15s} {'pub isnow>0':>11s} {'corrected':>10s} {'pub rcmb0 med km':>16s} {'corr rcmb0 med':>14s} {'pub CMR2 mean':>13s} {'corr CMR2 mean':>14s}")
for moi in ("margot", "genova"):
    for lab in ("S_0.00", "Si_0.00", "S+Si_0.05", "S+Si_0.10"):
        light, chi = lab.split("_")
        # published survivors
        isn = []; rc = []; cm = []; lost = collections.Counter(); lost_cmr2 = collections.defaultdict(list)
        for key, v in inv[moi]["logs"].items():
            c1 = float(key.split(",")[0]); d = inv[moi]["dirs"].get(key, {}); m = d.get(lab)
            for s in v["segs"]:
                if s["label"] != lab: continue
                if m and m["nrows"] > 0:
                    isn += m["isnow"]; rc.append(m["rcmb0"]); cm.append(c1)
                elif s["last_r"] == 10.0:
                    lost[s["end"]] += 1; lost_cmr2[s["end"]].append(c1)
        n_pub = len(rc)
        # recoverable: apply class recovery rates
        add_rows = 0; add_isnow = 0; add_rc = []; add_cm = []
        for end in ("crash_stderr", "newton_maxit", "detJ0"):
            cls = f"{moi}/{lab}/{end}/10m"
            if cls not in rec_rate or lost[end] == 0: continue
            rate, rows, isnf = rec_rate[cls]
            nrec = rate * lost[end]
            add_rows += nrec * rows; add_isnow += nrec * rows * (0 if np.isnan(isnf) else isnf)
            # recovered rcmb0 from sample
            rcs = [best[ckey(c)][2] for c in cases if c["cls"] == cls and best.get(ckey(c), (0,))[0] >= 5]
            add_rc += list(np.random.default_rng(0).choice(rcs, int(round(nrec)))) if rcs else []
            add_cm += list(np.random.default_rng(0).choice(lost_cmr2[end], int(round(nrec)))) if lost_cmr2[end] else []
        pub_isn = np.mean(np.array(isn) > 0) if isn else float("nan")
        corr_isn = (np.sum(np.array(isn) > 0) + add_isnow) / (len(isn) + add_rows) if (len(isn) + add_rows) else float("nan")
        print(f"{moi+'/'+lab:22s} {n_pub:9d} {lost['crash_stderr']:14d} {len(add_rc):15d} {pub_isn:11.3f} {corr_isn:10.3f} {np.median(rc)/1e3 if rc else 0:16.0f} {np.median(rc+add_rc)/1e3 if rc+add_rc else 0:14.0f} {np.mean(cm) if cm else 0:13.4f} {np.mean(cm+add_cm) if cm+add_cm else 0:14.4f}")
