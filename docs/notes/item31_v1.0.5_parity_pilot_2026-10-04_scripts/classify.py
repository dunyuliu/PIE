"""Item 31 pilot: build the prestop-failing-radius population from the
run_pair.py outputs, independently verify each sampled v1.0.5 root with
verify_v105_root.py (v1.0.5's OWN shoot_mercmodel, separate legacy venv),
and classify HEAD-correctly-rejects / HEAD-over-constrains / inconclusive.
"""
import json, os, subprocess, sys, glob, random

HERE = os.path.dirname(os.path.abspath(__file__))
V105_SRC = os.path.join(HERE, "v105_src")
PYEXE_V105 = os.path.join(HERE, "v105_venv", "bin", "python3")
RM_A = 2439360.0
RESULTS = os.path.join(HERE, "results")

def load_runs():
    runs = []
    for f in sorted(glob.glob(os.path.join(RESULTS, "run_*.json"))):
        runs.append(json.load(open(f)))
    return runs


def prestop_candidates(runs):
    """For each run, match v1.0.5-converged radii to HEAD's csv rows at the
    same ricb and flag HEAD error_code != 0 (CONVERGED)."""
    cands = []
    for r in runs:
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
                cands.append(dict(run=r, ricb_m=ricb_m, v=c["v"], v105_normf=c["normf"],
                                  head_match="MISSING", head_error_code=None))
                continue
            ec = float(hrow["error_code"])
            if ec != 0.0:
                cands.append(dict(run=r, ricb_m=ricb_m, v=c["v"], v105_normf=c["normf"],
                                  head_match="FOUND", head_error_code=ec, head_row=hrow))
    return cands


def verify_one(cand, tmpdir, idx):
    r = cand["run"]
    task = dict(CMR2=r["CMR2"], CMC=r["CMC"], light=r["light"],
               chi_Si_icb=r["chi_Si_icb"] if r["light"] == "S+Si" else None,
               ricb_m=cand["ricb_m"], v=cand["v"])
    task_path = os.path.join(tmpdir, "task_%03d.json" % idx)
    out_path = os.path.join(tmpdir, "out_%03d.json" % idx)
    json.dump(task, open(task_path, "w"))
    env = dict(os.environ); env["PYTHONPATH"] = V105_SRC
    proc = subprocess.run([PYEXE_V105, os.path.join(V105_SRC, "verify_v105_root.py"), task_path, out_path],
                          cwd=tmpdir, env=env, timeout=120,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0 or not os.path.exists(out_path):
        return dict(task, status="harness_exception", message=proc.stdout[-500:])
    return json.load(open(out_path))


def classify(verify_out, v105_normf):
    if verify_out.get("status") != "ok":
        return "inconclusive/other", "v1.0.5 own residual recompute raised %s: %s" % (
            verify_out.get("exc"), verify_out.get("message"))
    normf = verify_out["normf"]
    admissible = verify_out["admissible"]
    # Sanity: recomputed residual must agree with the converged-flag's own
    # normf (both calls are the identical shoot_mercmodel on the identical v).
    if abs(normf - v105_normf) > 1e-6 and normf > 5e-5:
        return "inconclusive/other", "residual recompute %.3e disagrees with v1.0.5's own normf %.3e" % (normf, v105_normf)
    if not admissible:
        return "HEAD-correctly-rejects", ("v1.0.5 root INADMISSIBLE per HEAD's OWN mercmodel_box rule "
                                          "(pie/shootp.py:317-358, CHI_MIN=None so only chi<=chi_max and "
                                          "rcmb>ricb are enforced): chi_li_icb=%.4f (bound <=%.4f), "
                                          "rcmb_m=%.1f vs ricb_m=%.1f" %
                                          (verify_out["chi_li_icb"], verify_out["chi_max"],
                                           verify_out["rcmb_m"], verify_out["ricb_m"]))
    return "HEAD-over-constrains", ("v1.0.5 root ADMISSIBLE under HEAD's OWN mercmodel_box rule "
                                    "(chi_li_icb=%.4f <= %.4f, rcmb_m=%.1f > ricb_m=%.1f) "
                                    "and residual %.3e small, yet HEAD's csv row for this radius has "
                                    "error_code %s" %
                                    (verify_out["chi_li_icb"], verify_out["chi_max"], verify_out["rcmb_m"],
                                     verify_out["ricb_m"], normf, "?"))


if __name__ == "__main__":
    n_sample = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20261004
    runs = load_runs()
    cands = prestop_candidates(runs)
    print("total prestop-failing candidate radii across %d runs: %d" % (len(runs), len(cands)))
    by_code = {}
    for c in cands:
        by_code.setdefault(c["head_error_code"], []).append(c)
    for k, v in by_code.items():
        print("  head_error_code", k, ":", len(v))
    random.seed(seed)
    sample = []
    # stratify: take up to ceil(n_sample / n_codes) per code, then top up
    codes = sorted(by_code, key=lambda k: (k is None, k))
    per_code = max(1, n_sample // max(1, len(codes)))
    for k in codes:
        pool = by_code[k]
        random.shuffle(pool)
        sample += pool[:per_code]
    if len(sample) < n_sample:
        rest = [c for c in cands if c not in sample]
        random.shuffle(rest)
        sample += rest[:n_sample - len(sample)]
    sample = sample[:n_sample]
    print("sampled %d candidate radii for verification" % len(sample))

    tmpdir = os.path.join(HERE, "verify_work")
    os.makedirs(tmpdir, exist_ok=True)
    import shutil
    for datf in os.listdir(V105_SRC):
        if datf.endswith(".dat"):
            shutil.copy(os.path.join(V105_SRC, datf), tmpdir)
    out_rows = []
    for i, c in enumerate(sample):
        vout = verify_one(c, tmpdir, i)
        label, reason = classify(vout, c["v105_normf"])
        row = dict(moi=c["run"]["moi"], light=c["run"]["light"], chi_Si_icb=c["run"]["chi_Si_icb"],
                  CMR2=c["run"]["CMR2"], ricb_m=c["ricb_m"], head_error_code=c["head_error_code"],
                  v105_normf=c["v105_normf"], verify=vout, label=label, reason=reason)
        out_rows.append(row)
        print(i, row["moi"], row["light"], row["chi_Si_icb"], "ricb_m=%.0f" % row["ricb_m"],
              "head_ec=%s" % row["head_error_code"], "->", label)
    json.dump(dict(n_candidates_total=len(cands), by_head_error_code={str(k): len(v) for k, v in by_code.items()},
                   sample=out_rows), open(os.path.join(HERE, "classification.json"), "w"), indent=1, default=str)
