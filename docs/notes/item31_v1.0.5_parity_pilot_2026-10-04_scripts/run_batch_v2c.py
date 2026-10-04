import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_pair_v2 import run_one

SAMPLE = json.load(open(os.path.join(HERE, "item31b_sample_v2c.json")))
WORKDIR = os.path.join(HERE, "work_v2c")
OUTDIR = os.path.join(HERE, "results_v2c")
os.makedirs(OUTDIR, exist_ok=True)
WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 4

def _task(i):
    run = SAMPLE[i]
    t0 = time.time()
    try:
        res = run_one(run, WORKDIR)
    except Exception as e:
        res = dict(run, status="exception", exc=repr(e))
    res["wall_s"] = time.time() - t0
    json.dump(res, open(os.path.join(OUTDIR, "run_%02d.json" % i), "w"), indent=1, default=str)
    return i, res.get("tag"), res.get("v105_returncode"), res.get("head_returncode"), res.get("v105_n_converged"), len(res.get("head_rows", []))

if __name__ == "__main__":
    idxs = list(range(len(SAMPLE)))
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for f in as_completed([ex.submit(_task, i) for i in idxs]):
            print(f.result(), flush=True)
