"""item31c: build the matched-prestop candidate population from run_pair_v3.py
outputs (results_v3_<tag>/), filter to head_error_code in {1,2} (NOT 4 --
this phase targets NEWTON_MAXIT/SINGULAR_JACOBIAN directly, per owner GO),
independently re-verify each sampled v1.0.5 root with verify_v105_root_v3.py
(per-row liquidus_eq, item31c's fix over v2's hardcoded Edmund), classify
HEAD-over-constrains(a) / HEAD-correctly-rejects(b) / tuning-only(c), and
report each row's survival of the paper's sort_models.py predicates (quoted
verbatim from the Zenodo bundle, see item31c note section on this).
"""
import json, os, subprocess, sys, glob, random

HERE = os.path.dirname(os.path.abspath(__file__))
V105_SRC = os.path.join(HERE, "v105_src_instrumented")
PYEXE_V105 = os.path.join(HERE, "v105_venv", "bin", "python3")
RM_A = 2439360.0


def load_runs(results_dirs):
    runs = []
    for d in results_dirs:
        for f in sorted(glob.glob(os.path.join(d, "run_*.json"))):
            runs.append(json.load(open(f)))
    return runs


def prestop_candidates(runs):
    cands = []
    for r in runs:
        if r.get("status") == "exception" or "head_rows" not in r:
            continue
        head_by_ricb = {}
        for row in r.get("head_rows", []):
            try:
                ricb = float(row["ricb"])
            except (KeyError, ValueError, TypeError):
                continue
            head_by_ricb[round(ricb)] = row
        for c in r.get("v105_converged", []):
            ricb_m = c["ricb_nd"] * RM_A
            hrow = head_by_ricb.get(round(ricb_m))
            if hrow is None:
                continue
            ec = float(hrow["error_code"])
            if ec != 0.0:
                cands.append(dict(run=r, ricb_m=ricb_m, v=c["v"], v105_normf=c["normf"],
                                  head_error_code=ec, head_row=hrow))
    return cands


def verify_one(cand, tmpdir, idx):
    r = cand["run"]
    liquidus_eq = r.get("liquidus_eq", "Edmund")
    task = dict(CMR2=r["CMR2"], CMC=r["CMC"], light=r["light"], liquidus_eq=liquidus_eq,
               chi_Si_icb=r["chi_Si_icb"] if r["light"] == "S+Si" else None,
               ricb_m=cand["ricb_m"], v=cand["v"])
    task_path = os.path.join(tmpdir, "task_%03d.json" % idx)
    out_path = os.path.join(tmpdir, "out_%03d.json" % idx)
    json.dump(task, open(task_path, "w"))
    env = dict(os.environ); env["PYTHONPATH"] = V105_SRC
    proc = subprocess.run([PYEXE_V105, os.path.join(V105_SRC, "verify_v105_root_v3.py"), task_path, out_path],
                          cwd=tmpdir, env=env, timeout=120,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0 or not os.path.exists(out_path):
        return dict(task, status="harness_exception", message=proc.stdout[-500:])
    return json.load(open(out_path))


def classify(verify_out, v105_normf, head_row):
    if verify_out.get("status") != "ok":
        return "inconclusive/other", "v1.0.5 own residual recompute raised %s: %s" % (
            verify_out.get("exc"), verify_out.get("message"))
    normf = verify_out["normf"]
    residual_disagrees = abs(normf - v105_normf) > 1e-6 and normf > 5e-5
    if residual_disagrees:
        return "inconclusive/other", "residual recompute %.3e disagrees with v1.0.5's own normf %.3e" % (normf, v105_normf)
    if not verify_out.get("si_gate_pass", True):
        return "HEAD-correctly-rejects(b)", ("fails driverp.py:137-149 pre-sweep SI_ABOVE_LIQUIDUS_MAX gate: "
                                            "chi_Si_icb > si_max=%s (%s)" % (verify_out.get("si_max_gate"), verify_out.get("liquidus_eq")))
    if not verify_out["box_pass"]:
        reasons = []
        if not verify_out["box_finite_ok"]:
            reasons.append("non-finite f/fout")
        if not verify_out["box_rcmb_ok"]:
            reasons.append("rcmb<=ricb (mercmodel_box)")
        if not verify_out["box_chimax_ok"]:
            reasons.append("chi_li_icb=%.4f > chi_max=%.4f" % (verify_out["chi_li_icb"], verify_out["chi_max"]))
        return "HEAD-correctly-rejects(b)", "fails mercmodel_box: " + "; ".join(reasons)
    if verify_out["chi_profile_negative"]:
        return "HEAD-correctly-rejects(b)", ("fails driverp.py:287-288 post-convergence chi>=0 check: "
                                         "chi_li profile min=%.4f" % verify_out["chi_li_profile_min"])
    if verify_out["ricb_ge_rcmb_final"]:
        return "HEAD-correctly-rejects(b)", ("fails driverp.py:252 rs[k]>=rcmb check: ricb_m=%.1f >= rcmb_m=%.1f" %
                                         (verify_out["ricb_m"], verify_out["rcmb_m"]))
    # full_head_accept True -- over-constrains(a), unless the solver log gives
    # positive evidence this is a tuning artifact (c). Conservative default: (a).
    newton_iters = head_row.get("newton_iters")
    tuning_note = ("newton_iters=%s on the HEAD row at this radius (no per-iterate "
                  "trajectory captured for this batch -- (c) not claimed without "
                  "that evidence, per task instructions)" % newton_iters)
    return "HEAD-over-constrains(a)", ("v1.0.5 root passes ALL of HEAD's own checks "
                                      "(si-gate, mercmodel_box, driverp.py:287-288 chi>=0, "
                                      "driverp.py:252 rs>=rcmb) yet HEAD's csv row for this radius "
                                      "has a non-zero error_code. " + tuning_note)


SORT_MODELS_MINCHISI = 1.0  # wt%, sort_models.py "only want chiSi = 1 wt% and above"


def sort_models_survival(head_row, light):
    chi_S_bulk = float(head_row["chi_S_bulk"])
    chi_Si_icb_pct = float(head_row["chi_Si_icb"]) * 100.0  # csv stores fraction; sort_models.py compares vs wt%
    isnow = float(head_row["isnow"])
    Tcmb = float(head_row["Tcmb"])
    # sort_models.py's "all" row filter glob-selects ONLY '*S+Si_Edmund' folders,
    # so chi_Si_icb>0 is structurally required -- S-only/Si-only rows cannot
    # pass the paper's own "all" predicate by construction, noted explicitly.
    applicable = (light == "S+Si")
    all_pass = applicable and (chi_S_bulk > 0) and (chi_Si_icb_pct > 0)
    sl_pass = isnow in (1.0, 3.0)
    goodTCMB_pass = (1700.0 <= Tcmb <= 2100.0)
    goodTCMB_sl_pass = sl_pass and goodTCMB_pass
    goodTCMB_goodchiS_pass = goodTCMB_pass and (chi_S_bulk < 0.02)
    return dict(applicable_all_filter=applicable, all=all_pass, sl=sl_pass,
               goodTCMB=goodTCMB_pass, goodTCMB_sl=goodTCMB_sl_pass,
               goodTCMB_goodchiS=goodTCMB_goodchiS_pass,
               chi_S_bulk=chi_S_bulk, chi_Si_icb_pct=chi_Si_icb_pct, isnow=isnow, Tcmb=Tcmb)


if __name__ == "__main__":
    results_dirs = sys.argv[1].split(",")
    n_per_code = dict(e1=int(sys.argv[2]) if len(sys.argv) > 2 else 30,
                      e2=int(sys.argv[3]) if len(sys.argv) > 3 else 30)
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 20261004331
    out_name = sys.argv[5] if len(sys.argv) > 5 else "classification_v3.json"

    runs = load_runs(results_dirs)
    cands = prestop_candidates(runs)
    print("total prestop-failing candidate radii across %d runs: %d" % (len(runs), len(cands)))
    by_code = {}
    for c in cands:
        by_code.setdefault(c["head_error_code"], []).append(c)
    for k, v in sorted(by_code.items()):
        print("  head_error_code", k, ":", len(v))
    random.seed(seed)
    sample = []
    for code_key, n in [(1.0, n_per_code['e1']), (2.0, n_per_code['e2'])]:
        pool = list(by_code.get(code_key, []))
        random.shuffle(pool)
        taken = pool[:n]
        print("code %s: %d candidates available, sampling %d" % (code_key, len(pool), len(taken)))
        sample += taken
    print("sampled %d candidate radii for verification" % len(sample))

    tmpdir = os.path.join(HERE, "verify_work_v3")
    os.makedirs(tmpdir, exist_ok=True)
    import shutil
    for datf in os.listdir(V105_SRC):
        if datf.endswith(".dat"):
            shutil.copy(os.path.join(V105_SRC, datf), tmpdir)
    out_rows = []
    for i, c in enumerate(sample):
        vout = verify_one(c, tmpdir, i)
        label, reason = classify(vout, c["v105_normf"], c["head_row"])
        sm = sort_models_survival(c["head_row"], c["run"]["light"])
        row = dict(moi=c["run"]["moi"], light=c["run"]["light"], chi_Si_icb=c["run"]["chi_Si_icb"],
                  liquidus_eq=c["run"].get("liquidus_eq", "Edmund"),
                  CMR2=c["run"]["CMR2"], CMC=c["run"]["CMC"], ricb_m=c["ricb_m"],
                  head_error_code=c["head_error_code"], v105_normf=c["v105_normf"],
                  verify=vout, label=label, reason=reason, sort_models=sm)
        out_rows.append(row)
        print(i, row["moi"], row["light"], row["chi_Si_icb"], "ricb_m=%.0f" % row["ricb_m"],
              "head_ec=%s" % row["head_error_code"], "->", label)
    json.dump(dict(n_candidates_total=len(cands),
                   by_head_error_code={str(k): len(v) for k, v in sorted(by_code.items())},
                   sample=out_rows), open(os.path.join(HERE, out_name), "w"), indent=1, default=str)
