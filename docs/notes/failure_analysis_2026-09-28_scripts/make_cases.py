"""Stratified sample of published runs by (moi, label, end, died@10m) -> cases.json; plus
eutectic-clamp check on the LAST csv row of det(J)==0 / newton_maxit truncated models (read-only)."""
import os, json, random, csv, glob, collections, sys
import numpy as np
inv = json.load(open(sys.argv[1]))
D = os.path.expanduser("~/shared_dataset/zenodo.16459292/extracted/PIE")
rng = random.Random(1)
classes = collections.defaultdict(list)
for moi in ("margot", "genova"):
    for key, v in inv[moi]["logs"].items():
        c1, c2 = map(float, key.split(","))
        for s in v["segs"]:
            if s["end"] in ("finish", "si_exceed"): continue
            lab = s["label"]
            if lab not in ("S_0.00", "Si_0.00", "S+Si_0.05", "S+Si_0.10"): continue
            light, chi = lab.split("_")
            classes[(moi, lab, s["end"], s["last_r"] == 10.0)].append(dict(moi=moi, CMR2=c1, CMC=c2, light=light, chi=float(chi), label=lab, end=s["end"], last_r=s["last_r"], nrad=s["nrad"]))
cases = []
NPER = int(sys.argv[3]) if len(sys.argv) > 3 else 4
for k in sorted(classes):
    pool = classes[k]
    pick = rng.sample(pool, min(NPER, len(pool)))
    for c in pick:
        c["cls"] = f"{k[0]}/{k[1]}/{k[2]}/{'10m' if k[3] else 'later'}"
        cases.append(c)
print("classes:", {"/".join(map(str, k)): len(v) for k, v in classes.items()})
print("n cases:", len(cases))
json.dump(cases, open(sys.argv[2], "w"), indent=0)

# ---- eutectic-clamp check on last rows (margot + genova, S / S+Si_0.05 / Si, non-empty csvs)
ratio = collections.defaultdict(list)
for moi in ("margot", "genova"):
    for key, v in inv[moi]["logs"].items():
        c1, c2 = map(float, key.split(","))
        for s in v["segs"]:
            lab = s["label"]
            if lab not in ("S_0.00", "S+Si_0.05", "Si_0.00") or s["nrad"] < 2: continue
            light, chi = lab.split("_")
            d = f"{D}/work.{moi}/results/CMR2_{c1:.17f}_CMC_{c2:.17f}_{light}_Edmund/pMetaData_{chi}.csv"
            try: rows = list(csv.DictReader(open(d)))
            except FileNotFoundError: continue
            if not rows: continue
            last = rows[-1]
            x = float(last["chi_li_icb"]); eut = float(last["chi_li_eut_icb"]) if light != "Si" else 0.12
            cin = float(last["chi_li_in"]); isnow = float(last["isnow"])
            ratio[(moi, lab, s["end"])].append((x / eut, cin / eut, isnow, float(last["ricb"]) / 1e3, float(last["rcmb"]) / 1e3))
print("\nLast converged row before death: chi_li_icb/chi_eut_icb (median, 10th, 90th pct), chi_li_in/eut median, isnow counts, ricb_km median, rcmb_km median")
for k in sorted(ratio):
    a = np.array(ratio[k])
    print(f"{k[0]:7s} {k[1]:10s} {k[2]:13s} n={len(a):4d}  x/eut={np.median(a[:,0]):.3f} [{np.percentile(a[:,0],10):.3f},{np.percentile(a[:,0],90):.3f}]  in/eut={np.median(a[:,1]):.3f}  isnow={dict(collections.Counter(a[:,2].astype(int)))}  ricb={np.median(a[:,3]):.0f}  rcmb={np.median(a[:,4]):.0f}")
