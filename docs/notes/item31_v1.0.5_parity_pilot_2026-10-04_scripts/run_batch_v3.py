import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_pair_v3 import run_one

SAMPLE_PATH = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "item31c_trial_sample.json")
SAMPLE = json.load(open(SAMPLE_PATH))
TAG = sys.argv[3] if len(sys.argv) > 3 else "trial"
WORKDIR = os.path.join(HERE, "work_v3_%s" % TAG)
OUTDIR = os.path.join(HERE, "results_v3_%s" % TAG)
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
    return i, res.get("tag"), res.get("v105_returncode"), res.get("head_returncode"), res.get("v105_n_converged"), len(res.get("head_rows", [])), res["wall_s"]

if __name__ == "__main__":
    idxs = list(range(len(SAMPLE)))
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for f in as_completed([ex.submit(_task, i) for i in idxs]):
            print(f.result(), flush=True)
