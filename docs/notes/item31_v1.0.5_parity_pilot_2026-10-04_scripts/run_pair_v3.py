"""item31b: run_pair v2 -- same subprocess-isolated v1.0.5-vs-HEAD execution
as run_pair.py, extended to also capture (a) the full v1.0.5 debug.jsonl
(including the new per-iterate 'iterate' records added to
v105_src_instrumented/shootp.py for item31b) and (b) HEAD's own structured
solver log (pSolverLogFileName, written unconditionally by
pie/shootp.py::mynewtonSys's log_path, one JSON record per Newton solve
attempt with full per-iterate history: normf, normdx, alpha, condJ,
rejections). Needed to do the NEWTON_MAXIT trajectory comparison (item31b
task 3) without re-solving anything -- both logs are emitted naturally by
each sweep's own run.
"""
import json, os, subprocess, sys, time, shutil, csv as csvmod, glob

HERE = os.path.dirname(os.path.abspath(__file__))
V105_SRC = os.path.join(HERE, "v105_src_instrumented")
HEAD_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PYEXE = os.path.join(HEAD_ROOT, ".venv", "bin", "python3")
PYEXE_V105 = os.path.join(HERE, "v105_venv", "bin", "python3")
RM_A = 2439360.0


def run_one(run, workdir_base):
    moi = run["moi"]; CMR2 = run["CMR2"]; CMC = run["CMC"]; light = run["light"]
    chi = run["chi_Si_icb"]
    tag = "%s_%s_%s_%s" % (moi, light, chi, CMR2[-6:])
    out = dict(moi=moi, CMR2=CMR2, CMC=CMC, light=light, chi_Si_icb=chi, tag=tag)

    # ---- v1.0.5 ----
    v105_dir = os.path.join(workdir_base, "v105_" + tag)
    os.makedirs(os.path.join(v105_dir, "results"), exist_ok=True)
    for datf in os.listdir(V105_SRC):
        if datf.endswith(".dat"):
            shutil.copy(os.path.join(V105_SRC, datf), v105_dir)
    dbg_log = os.path.join(v105_dir, "debug.jsonl")
    env = dict(os.environ); env["PIE105_DEBUG_LOG"] = dbg_log
    env["MPLBACKEND"] = "Agg"; env["PYTHONPATH"] = V105_SRC
    env["OMP_NUM_THREADS"] = "1"; env["OPENBLAS_NUM_THREADS"] = "1"
    argv = ["p", CMR2, CMC, light, "Edmund"] + ([chi] if light == "S+Si" else [])
    t0 = time.time()
    proc = subprocess.run([PYEXE_V105, os.path.join(V105_SRC, "main.py")] + argv,
                          cwd=v105_dir, env=env, timeout=900,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out["v105_dt_s"] = time.time() - t0
    out["v105_returncode"] = proc.returncode
    out["v105_stdout_tail"] = proc.stdout[-2000:]
    converged = []
    debug_all = []
    if os.path.exists(dbg_log):
        for line in open(dbg_log):
            rec = json.loads(line)
            debug_all.append(rec)
            if rec.get("kind") == "converged":
                converged.append(dict(ricb_nd=rec["ricb"], v=rec["x"], normf=rec["normf"]))
    out["v105_n_converged"] = len(converged)
    out["v105_converged"] = converged
    out["v105_debug_all"] = debug_all  # includes new 'iterate'/'maxit' records (item31b)

    # ---- HEAD ----
    head_dir = os.path.join(workdir_base, "head_" + tag)
    os.makedirs(os.path.join(head_dir, "results"), exist_ok=True)
    env2 = dict(os.environ); env2["MPLBACKEND"] = "Agg"; env2["PYTHONPATH"] = HEAD_ROOT
    env2["OMP_NUM_THREADS"] = "1"; env2["OPENBLAS_NUM_THREADS"] = "1"
    t0 = time.time()
    proc2 = subprocess.run([PYEXE, "-m", "pie", "p", CMR2, CMC, light, "Edmund"] +
                           ([chi] if light == "S+Si" else []),
                          cwd=head_dir, env=env2, timeout=1200,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out["head_dt_s"] = time.time() - t0
    out["head_returncode"] = proc2.returncode
    out["head_stdout_tail"] = proc2.stdout[-2000:]

    model_dirs = [d for d in os.listdir(os.path.join(head_dir, "results"))] if os.path.isdir(os.path.join(head_dir, "results")) else []
    out["head_model_dirs"] = model_dirs
    head_rows = []
    head_solverlog = []
    if model_dirs:
        chi_tag = "%.2f" % float(chi if light == "S+Si" else 0.0)
        csv_path = os.path.join(head_dir, "results", model_dirs[0], "pMetaData_%s.csv" % chi_tag)
        if os.path.exists(csv_path):
            with open(csv_path) as fh:
                for row in csvmod.DictReader(fh):
                    head_rows.append(row)
        log_path = os.path.join(head_dir, "results", model_dirs[0], "solverLog_%s.jsonl" % chi_tag)
        if os.path.exists(log_path):
            for line in open(log_path):
                line = line.strip()
                if not line:
                    continue
                head_solverlog.append(json.loads(line))
    out["head_rows"] = head_rows
    out["head_solverlog"] = head_solverlog
    return out


if __name__ == "__main__":
    sample_path, idx, workdir, out_path = sys.argv[1:5]
    sample = json.load(open(sample_path))
    run = sample[int(idx)]
    res = run_one(run, workdir)
    json.dump(res, open(out_path, "w"), indent=1, default=str)
    print("DONE", res["tag"], res["v105_returncode"], res["head_returncode"],
          res["v105_n_converged"], len(res["head_rows"]), res["v105_dt_s"], res["head_dt_s"])
