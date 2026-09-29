import os,re,glob,csv,json,sys
import numpy as np
D=os.path.expanduser("~/shared_dataset/zenodo.16459292/extracted/PIE")
RS=np.arange(1e1,2e6,50e3)
labels=[f"S+Si_{c:.2f}" for c in np.linspace(0,0.15,16)]+["S_0.00","Si_0.00"]
out={}
for moi in ("margot","genova"):
    res=f"{D}/work.{moi}/results"
    # --- stdout logs
    logs={}
    for lf in glob.glob(f"{res}/log.*.txt"):
        m=re.match(r"log\.([0-9.e-]+)\.(0\.[0-9e-]+)\.txt",os.path.basename(lf))
        cmr2=float(m.group(1)); cmc=float(m.group(2))
        txt=open(lf,errors="replace").read()
        segs=re.split(r"(?=Finding solutions for inner core radius = 10\.0 )",txt)
        segs=[s for s in segs if s.startswith("Finding solutions")]
        recs=[]
        for i,s in enumerate(segs):
            radii=[float(x) for x in re.findall(r"Finding solutions for inner core radius = ([0-9.]+)",s)]
            if "Finish simulating model" in s: end="finish"
            elif "Solution not found within tolerance" in s: end="newton_maxit"
            elif "Zero Determinant" in s: end="detJ0"
            elif "Exceeding allowed maximum Si" in s: end="si_exceed"
            else: end="crash_stderr"
            recs.append(dict(label=labels[i] if i<18 else f"extra{i}",nrad=len(radii),last_r=radii[-1],end=end,
                             n_negS_alert=s.count("No negative %wt"),err2="Final Light element %wt solution is negative" in s,
                             nnewton_fail_lines=s.count("Solution not found")))
        logs[(cmr2,cmc)]=dict(nseg=len(segs),segs=recs)
    # --- results dirs
    dirs={}
    for d in sorted(glob.glob(f"{res}/CMR2_*")):
        m=re.match(r"CMR2_([0-9.]+)_CMC_([0-9.]+)_(S\+Si|S|Si)_(\w+)",os.path.basename(d))
        cmr2=float(m.group(1)); cmc=float(m.group(2)); light=m.group(3)
        for cf in sorted(glob.glob(d+"/pMetaData_*.csv")):
            chi=os.path.basename(cf)[10:14]
            rows=list(csv.DictReader(open(cf)))
            ric=[float(r["ricb"]) for r in rows]
            ec=[float(r["error_code"]) for r in rows]
            isnow=[float(r["isnow"]) for r in rows]
            rcmb=[float(r["rcmb"]) for r in rows]
            nh5=len(glob.glob(d+f"/DataSi%wt{chi}_R*.h5"))
            dirs.setdefault((cmr2,cmc),{})[f"{light}_{chi}"]=dict(nrows=len(rows),max_ricb=max(ric) if ric else None,
                 n_ec1=sum(1 for e in ec if e==1),n_ec2=sum(1 for e in ec if e==2),nh5=nh5,isnow=isnow,rcmb0=rcmb[0] if rcmb else None,ricb=ric)
    out[moi]=dict(logs={f"{k[0]!r},{k[1]!r}":v for k,v in logs.items()},dirs={f"{k[0]!r},{k[1]!r}":v for k,v in dirs.items()})
    print(moi,"logs",len(logs),"draws",len(dirs))
json.dump(out,open(sys.argv[1],"w"))
