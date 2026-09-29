"""analyze_runs.py tag [tag2 ...] : per-case summary of probe results vs published class."""
import json, glob, sys, os, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
cases_all = {json.dumps([c["CMR2"], c["CMC"], c["light"], c.get("chi", 0.0)]): c for c in json.load(open(HERE + "/cases.json"))}

def eut(P):  # Dumberry & Rivoldini 2015 eq 28, P in Pa
    return 0.11 + 0.187 * np.exp(-0.065 * P * 1e-9)

def signature(hist):
    nf = np.array([h["nf"] for h in hist if h["nf"] is not None])
    if len(nf) < 4: return "short"
    if not np.all(np.isfinite(nf)): return "nan"
    tail = nf[-6:]
    if np.std(tail) / np.mean(tail) < 0.05: return "stagnation"
    # period-2 oscillation: alternating pattern with tiny drift
    if len(tail) >= 6 and np.allclose(tail[::2], tail[0], rtol=0.05) and np.allclose(tail[1::2], tail[1], rtol=0.05): return "period2_oscillation"
    if nf[-1] > 10 * nf[0]: return "divergence"
    if nf[-1] < nf[0] and nf[-1] > 1e-3: return "slow_decrease"
    return "irregular"

for tag in sys.argv[1:]:
    print(f"\n######## {tag}")
    rows = []
    for f in sorted(glob.glob(f"{HERE}/runs/{tag}/*.json")):
        d = json.load(open(f))
        if "crashed" in d:
            print(os.path.basename(f), "PROBE CRASHED", d["crashed"][-300:].replace("\n", " | ")); continue
        key = json.dumps([d["CMR2"], d["CMC"], d["light"], d["chi"]])
        c = cases_all.get(key, {})
        recs = d["recs"]; last = recs[-1]
        nok = sum(r["status"] == "ok" for r in recs)
        st = last["status"]
        extra = ""
        if st == "newton_detJ0" and last.get("J_last"):
            J = np.array(last["J_last"]); zc = [j for j in range(5) if np.all(J[:, j] == 0)]
            x = last["x_last"]; P = last.get("shoot_trace", {}).get("Picb_nd")
            e = 0.12 if d["light"] == "Si" else (eut(P * 3.5e10) if P else None)  # scale P ~ rhomean*a*g ~ 3.5e10? computed below if trace has it
            extra = f"zero_cols={zc} x4={x[4]:.4f} it={len(last['hist'])} nf_at_stop={last['hist'][-1]['nf']:.2e}"
        if st.startswith("newton_maxit"):
            extra = f"sig={signature(last['hist'])} nf_last={last['hist'][-1]['nf']:.2e} nf_min={min(h['nf'] for h in last['hist']):.2e} condJ={last['hist'][-1]['condJ']:.1e}"
        if st in ("singular_LU", "k2_grid_error", "runtime_error") or st.startswith("exception"):
            kt = last.get("k2_trace", {}); pt = last.get("pot_trace", {}); sh = last.get("shoot_trace", {})
            extra = f"it={len(last.get('hist',[]))} nrs={kt.get('nrs')} nonfiniteA={pt.get('nonfinite_in_A')} nonfin_rho={kt.get('n_nonfinite_rho')} nonfin_g={kt.get('n_nonfinite_g')} nan_yc={sh.get('nan_yc')} nan_rhof={sh.get('nan_rhof')} rcmb={sh.get('rcmb')} v={np.round(sh.get('v',[]),3).tolist()} exc={str(last.get('exc',''))[:80]}"
        if "newton_status" in last and last["newton_status"].get("n_clamped"):
            extra += f" clamped={last['newton_status'].get('n_clamped')} lstsq={last['newton_status'].get('n_lstsq')} best_nf={last['newton_status'].get('best_nf'):.2e}"
        pub_rows = (c.get("nrad", 0) - 1) if c.get("end") != "finish" else c.get("nrad", 0)
        rows.append((c.get("cls", "?"), pub_rows, nok, last["ricb_m"] / 1e3, st, extra))
    rows.sort()
    print(f"{'published class':40s} {'pub_rows':>8s} {'fresh_ok':>8s} {'stop_km':>8s} {'fresh_status':18s} detail")
    for r in rows:
        print(f"{r[0]:40s} {r[1]:8d} {r[2]:8d} {r[3]:8.0f} {r[4]:18s} {r[5]}")
    # aggregate
    agg = collections.Counter((r[0].split('/')[2] + '/' + r[0].split('/')[3], r[4]) for r in rows)
    print("aggregate (published end/where -> fresh status):")
    for k, v in sorted(agg.items()): print("  ", k, "->", v)
    same = sum(1 for r in rows if r[1] == r[2]); print(f"fresh row count == published row count: {same}/{len(rows)}; fresh more rows: {sum(1 for r in rows if r[2] > r[1])}; fewer: {sum(1 for r in rows if r[2] < r[1])}")
