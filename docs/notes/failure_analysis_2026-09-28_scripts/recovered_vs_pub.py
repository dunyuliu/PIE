import json, glob, collections, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
tag = sys.argv[1] if len(sys.argv) > 1 else "ls"
inv = json.load(open(HERE + "/inventory.json"))
cases = {json.dumps([c["CMR2"], c["CMC"], c["light"], c.get("chi", 0.0)]): c for c in json.load(open(HERE + "/cases.json"))}
pub = collections.defaultdict(lambda: dict(isnow=[], rcmb0=[], ricb_max=[]))
for moi in ("margot", "genova"):
    for key, d in inv[moi]["dirs"].items():
        for lab, m in d.items():
            if m["nrows"] == 0: continue
            p = pub[(moi, lab)]; p["isnow"] += m["isnow"]; p["rcmb0"].append(m["rcmb0"]); p["ricb_max"].append(m["max_ricb"])
rec = collections.defaultdict(lambda: dict(isnow=[], rcmb0=[], ricb_max=[], cmr2=[]))
for f in glob.glob(f"{HERE}/runs/{tag}/*.json"):
    d = json.load(open(f))
    if "recs" not in d: continue
    c = cases[json.dumps([d["CMR2"], d["CMC"], d["light"], d["chi"]])]
    if "/crash_stderr/10m" not in c["cls"]: continue
    ok = [r for r in d["recs"] if r["status"] == "ok"]
    if not ok: continue
    lab = c["label"]; r = rec[(c["moi"], lab)]
    r["isnow"] += [x["isnow"] for x in ok]; r["rcmb0"].append(ok[0]["rcmb_m"]); r["ricb_max"].append(ok[-1]["ricb_m"]); r["cmr2"].append(c["CMR2"])
print(f"[{tag}] Recovered 10-m-crash models vs published survivors of the same MOI/composition")
print("moi/label              n_rec  rec_isnow>0  pub_isnow>0  rec_rcmb0_km  pub_rcmb0_med  rec_maxricb_km  pub_maxricb_med")
for k in sorted(rec):
    r = rec[k]; p = pub[k]
    print(f"{k[0]+'/'+k[1]:22s} {len(r['rcmb0']):5d} {np.mean(np.array(r['isnow'])>0):12.2f} {np.mean(np.array(p['isnow'])>0):12.2f} {np.mean(r['rcmb0'])/1e3:13.0f} {np.median(p['rcmb0'])/1e3:14.0f} {np.mean(r['ricb_max'])/1e3:15.0f} {np.median(p['ricb_max'])/1e3:16.0f}")
    print("      recovered CMR2:", np.round(r["cmr2"], 4).tolist(), " rcmb0 km:", np.round(np.array(r["rcmb0"]) / 1e3).tolist(), " max ricb km:", np.round(np.array(r["ricb_max"]) / 1e3).tolist())
