#!/usr/bin/env python3
"""Replicates driverp.py's radius loop (warm-started Newton) on the instrumented
scratch copy of src/, without any file I/O, and records per-radius outcome +
Newton history + k2/potential-solve traces to JSON.
usage: probe.py CMR2 CMC light liquidus chi_Si out.json [--opts k=v ...]
"""
import sys, os, json, time, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = HERE + "/src_instr"
sys.path[:] = [p for p in sys.path if "/.local/" not in p]
sys.path.insert(0, SRC)
ORIG_CWD = os.getcwd()
os.chdir(SRC)
os.environ.setdefault("MPLBACKEND", "Agg")

def main():
    a = sys.argv[1:]
    CMR2, CMC, light, liq, chi = float(a[0]), float(a[1]), a[2], a[3], float(a[4])
    outf = os.path.join(ORIG_CWD, a[5])
    opts = {}
    for kv in a[6:]:
        k, v = kv.split("=")
        try: v = json.loads(v)
        except Exception: pass
        opts[k] = v
    sys.argv[:] = ["main.py", "p", str(CMR2), str(CMC), light, liq, str(chi)]
    import numpy as np
    _stdout=sys.stdout; sys.stdout=open(os.devnull,"w")
    import globalvar as gv, planet_input, shootp as lc, libCore
    lc.NEWTON_OPTS.update({k: v for k, v in opts.items() if k in ("eps", "linesearch", "k2_fill", "k2_min_nrs", "clamp_chi")})
    libCore.POT_OPTS.update({k: v for k, v in opts.items() if k in ("cond", "dense", "dump")})
    maxit = int(opts.get("maxit", gv.maxit))
    param = planet_input.planet("p", CMR2, light, liq)
    scale = param["scale"]; rhocr, rh = param["rhocr"], param["rh"]
    rs = np.arange(1e1, 2e6, gv.dr)
    if "start_ricb" in opts:
        rs = np.array([float(opts["start_ricb"])] + [x for x in rs if x > float(opts["start_ricb"])])
    if "max_ricb" in opts:
        rs = rs[rs <= float(opts["max_ricb"])]
    if "only_ricb" in opts:
        rs = np.array([float(opts["only_ricb"])])
    ricb = rs / scale["a"]
    v0 = list(param["v0"])
    recs = []
    stop = None
    for k in range(len(ricb)):
        lc.NEWTON_HIST.clear(); lc.NEWTON_STATUS.clear(); lc.K2_TRACE.clear(); libCore.POT_TRACE.clear()
        t0 = time.time()
        rec = dict(ricb_m=float(rs[k]), k=k)
        try:
            v = lc.mynewtonSys("J_mercmodel", list(v0) if opts.get("cold") else v0, [ricb[k], rhocr, rh, param, scale],
                               xtol=gv.xtol, ftol=gv.ftol, maxit=maxit, verbose=False)
            rec["newton_end"] = lc.NEWTON_STATUS.get("end"); rec["newton_status"] = dict(lc.NEWTON_STATUS)
            rec["hist"] = [dict(k=h["k"], nf=h["nf"], ndx=h["ndx"], detJ=h["detJ"], condJ=h["condJ"], lam=h.get("lam")) for h in lc.NEWTON_HIST]
            rec["x_last"] = lc.NEWTON_HIST[-1]["x"] if lc.NEWTON_HIST else None
            rec["f_last"] = lc.NEWTON_HIST[-1]["f"] if lc.NEWTON_HIST else None
            rec["J_last"] = lc.NEWTON_HIST[-1].get("J") if lc.NEWTON_HIST else None
            if v is None:
                rec["status"] = "newton_" + rec["newton_end"]
                stop = rec["status"]
            else:
                f, r, yy, fout, err = lc.shoot_mercmodel(v, ricb[k], rhocr, rh, param, scale)
                rec["status"] = "ok"
                rec["v"] = list(map(float, v)); rec["f"] = list(map(float, f))
                rec["rcmb_m"] = float(v[2] * scale["a"]); rec["isnow"] = float(fout[2]); rec["chi_li_in"] = float(fout[4])
                rec["err_code1"] = bool(err)
                if not opts.get("cold"):
                    v0 = v
        except lc.K2GridError as e:
            rec["status"] = "k2_grid_error"; rec["exc"] = str(e)
            rec["hist"] = [dict(k=h["k"], nf=h["nf"], ndx=h["ndx"], detJ=h["detJ"], condJ=h["condJ"]) for h in lc.NEWTON_HIST]
            rec["x_last"] = lc.NEWTON_HIST[-1]["x"] if lc.NEWTON_HIST else None
            stop = rec["status"]
        except RuntimeError as e:
            rec["status"] = "singular_LU" if "singular" in str(e) else "runtime_error"; rec["exc"] = str(e)
            rec["hist"] = [dict(k=h["k"], nf=h["nf"], ndx=h["ndx"], detJ=h["detJ"], condJ=h["condJ"]) for h in lc.NEWTON_HIST]
            stop = rec["status"]
        except Exception as e:
            rec["status"] = "exception:" + type(e).__name__; rec["exc"] = traceback.format_exc()[-800:]
            stop = rec["status"]
        rec["k2_trace"] = dict(lc.K2_TRACE); rec["pot_trace"] = dict(libCore.POT_TRACE); rec["shoot_trace"] = dict(lc.SHOOT_TRACE)
        rec["dt"] = time.time() - t0
        recs.append(rec)
        if stop and not opts.get("continue_after_fail"):
            break
        if stop and opts.get("continue_after_fail"):
            stop = None
    sys.stdout=_stdout
    json.dump(dict(CMR2=CMR2, CMC=CMC, light=light, liq=liq, chi=chi, opts=opts, recs=recs), open(outf, "w"))
    print(outf, [(r["ricb_m"], r["status"]) for r in recs][-3:])

if __name__ == "__main__":
    main()
