"""Item 31 pilot: run v1.0.5 (scratch-instrumented copy) and HEAD (pie package)
on the same composition, each in its own subprocess/cwd. Returns a result dict."""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
V105_SRC = os.path.join(HERE, "v105_src")
HEAD_ROOT = "/home/utig5/dliu/PIE/.claude/worktrees/agent-ac348a4ee8c2b6362"
PYEXE = "/home/utig5/dliu/PIE/.venv/bin/python3"  # HEAD: the pinned/supported env (PROJECT_RULES rule 3c)
PYEXE_V105 = os.path.join(HERE, "v105_venv", "bin", "python3")  # v1.0.5: scipy<1.14 (has interp2d, which
                                                   # v1.0.5's coreEos.meltingDataFromFile calls directly --
                                                   # removed in scipy>=1.14, so the pinned HEAD venv cannot
                                                   # even IMPORT v1.0.5's code; using HEAD's own already-
                                                   # verified-bit-identical RectBivariateSpline port here
                                                   # would substitute a library call inside the very code
                                                   # we are differential-testing, so a separate legacy venv
                                                   # is used instead, scoped to this scratch dir only)
RM_A = 2439360.0  # scale['a'], constant across all compositions (model_generic['rm'])


def run_one(run, workdir_base):
    moi = run["moi"]; CMR2 = run["CMR2"]; CMC = run["CMC"]; light = run["light"]
    chi = run["chi_Si_icb"]
    tag = "%s_%s_%s_%s" % (moi, light, chi, CMR2[-6:])
    out = dict(moi=moi, CMR2=CMR2, CMC=CMC, light=light, chi_Si_icb=chi, tag=tag)

    # ---- v1.0.5 ----
    v105_dir = os.path.join(workdir_base, "v105_" + tag)
    os.makedirs(os.path.join(v105_dir, "results"), exist_ok=True)
    import shutil
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
    if os.path.exists(dbg_log):
        for line in open(dbg_log):
            rec = json.loads(line)
            if rec.get("kind") == "converged":
                converged.append(dict(ricb_nd=rec["ricb"], v=rec["x"], normf=rec["normf"]))
    out["v105_n_converged"] = len(converged)
    out["v105_converged"] = converged

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
    if model_dirs:
        import csv as csvmod
        chi_tag = "%.2f" % float(chi if light == "S+Si" else 0.0)
        csv_path = os.path.join(head_dir, "results", model_dirs[0], "pMetaData_%s.csv" % chi_tag)
        if os.path.exists(csv_path):
            with open(csv_path) as fh:
                for row in csvmod.DictReader(fh):
                    head_rows.append(row)
    out["head_rows"] = head_rows
    return out


if __name__ == "__main__":
    sample_path, idx, workdir, out_path = sys.argv[1:5]
    sample = json.load(open(sample_path))
    run = sample[int(idx)]
    res = run_one(run, workdir)
    json.dump(res, open(out_path, "w"), indent=1, default=str)
    print("DONE", res["tag"], res["v105_returncode"], res["head_returncode"],
          res["v105_n_converged"], len(res["head_rows"]), res["v105_dt_s"], res["head_dt_s"])
