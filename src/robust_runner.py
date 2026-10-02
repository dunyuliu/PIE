#!/usr/bin/env python3
"""Robust batch runner for PIE present-day ('p') jobs (PATHWAY_FORWARD.md item 22).

One runner for knox (local) and TACC Lonestar6, replacing the ad-hoc knox
`xargs` recipe and the TACC LAUNCHER recipe (README "Large ensemble Monte
Carlo simulation"). A job is one `main.py p CMR2 CMC light_element
liquidus_eq [chi_Si_icb]` call -- one pMetaData_<chi>.csv, one ricb sweep.

1. Manifest: an explicit CSV, read from a file, never hard-coded:

       CMR2,CMC,light_element,liquidus_eq,chi_Si_icb,seed
       0.346,0.424,S,Edmund,,
       0.346,0.424,S+Si,Edmund,0.05,

   `chi_Si_icb` is required for S+Si and must be blank otherwise
   (src/globalvar.py ignores it and uses 0.0 for S/Si). `seed` is
   optional provenance: the RNG seed that drew this row's CMR2/CMC
   (`make-mc-manifest`). The ricb grid is NOT a manifest column: it is
   fixed in src/main.py (`np.arange(1e1, 2e6, dr)`, dr in globalvar.py)
   and changing that is a src/ change, out of this runner's scope.

2. Resumable: a job is done iff its completion sentinel
   `results/<model dir>/.runner_done_<chi>.json` exists. The sentinel is
   written (atomic rename) only after main.py exits 0 and its csv reads
   back with >=1 data row. Not "csv exists": main.py writes the csv
   header before the sweep starts, so a killed job leaves a csv behind.

3. Status: a finished job's status is an `ErrorCode` name from
   src/globalvar.py (item 16, imported, not copied) -- CONVERGED if every
   radius converged, else the most frequent failure code -- with the full
   per-code row counts alongside. A job that never finished gets a
   `RunnerStatus` (PROCESS_CRASHED / INCOMPLETE_OUTPUT) instead.

4. Parallelism: `PIE_WORKERS` cap, same formula as
   testsys/conftest.py:pie_workers() (copied, since production must not
   import testsys; a unit test pins the two together); every job runs
   under `nice -n 10` with one BLAS thread (PROJECT_RULES.md rule 15).

5. Provenance, per job (not per run, so TACC jobs on many hosts are each
   self-describing): git SHA + whether src/ is dirty, root requirements.txt
   pins + the versions actually installed, host, interpreter, run_id,
   start/end time. Written to every status-log record and to the sentinel.

6. Backends: `--backend local` runs a capped thread pool, each thread
   driving one `main.py` subprocess. `--backend tacc` writes
   src/commands_launcher (the file src/TACC.LS6.parallel.run.slurm already
   reads) with one `robust_runner.py run-one <manifest> --index i` line per
   not-yet-done job, so TACC jobs get the same status records/sentinels.

CLI (run from anywhere; results/ goes under --src-dir, default src/):

    python3 src/robust_runner.py make-mc-manifest mc.csv --n 1024 --seed-base 20260930
    python3 src/robust_runner.py run mc.csv                       # knox
    python3 src/robust_runner.py run mc.csv --backend tacc        # LS6: then
    (cd src && sbatch TACC.LS6.parallel.run.slurm)

Status log: append-only JSONL, default src/results/runner_status.jsonl
(`--status-log`), one `start` and one `end` record per job attempt.
"""
import argparse
import csv
import dataclasses
import enum
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
REPO_ROOT = SRC_DIR.parent


def _load_error_code():
    """Import `src/globalvar.py`'s `ErrorCode` enum without re-deriving its
    vocabulary (requirement 3: reuse, don't invent a parallel one).

    `globalvar.py` parses `sys.argv` as main.py's (code_mode, CMR2, CMC,
    ...) at import time -- the obstacle `testsys/conftest.py` also works
    around with a placeholder argv. Here the placeholder is ALWAYS
    substituted for the first import (not only when argv is short): this
    runner's own CLI argv (`run m.csv --workers 2 ...`) is long enough to
    pass a length check and then crash on `float(sys.argv[2])`. Only
    ErrorCode is used from the module, which does not depend on argv.
    `sys.argv`/`sys.path` are restored in `finally`. An already-imported
    globalvar (e.g. inside main.py or a test) is reused as is.
    """
    saved_argv = sys.argv[:]
    saved_path = sys.path[:]
    try:
        if str(SRC_DIR) not in sys.path:
            sys.path.insert(0, str(SRC_DIR))
        if "globalvar" not in sys.modules:
            sys.argv[:] = ["main.py", "p", "0.346", "0.424", "S", "Edmund"]
        # globalvar.py does `print(len(sys.argv))` at import; keep that out
        # of this CLI's machine-readable (JSON) stdout.
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            import globalvar
        return globalvar.ErrorCode
    finally:
        sys.argv[:] = saved_argv
        sys.path[:] = saved_path


ErrorCode = _load_error_code()


class RunnerStatus(str, enum.Enum):
    """Statuses for a job that never produced a usable `ErrorCode` --
    strictly a complement to `ErrorCode`, not a replacement (requirement 3
    says reuse the existing table; this only covers what it structurally
    cannot: process-level outcomes). A job that finished reports an
    `ErrorCode` name instead (see `job_status_from_codes`)."""
    PROCESS_CRASHED = "PROCESS_CRASHED"      # nonzero exit / signal / timeout
    INCOMPLETE_OUTPUT = "INCOMPLETE_OUTPUT"  # exited 0 but csv missing / no data rows


def pie_workers():
    """Same cap formula as `testsys/conftest.py:pie_workers()`
    (PROJECT_RULES.md rule 15) -- duplicated rather than imported, since
    this module runs standalone in production (no `testsys/` on a TACC
    compute node). Keep these two in sync; a contract test diffs them.
    """
    env = os.environ.get("PIE_WORKERS")
    if env:
        return max(1, int(env))
    try:
        cpu = os.cpu_count() or 4
        load1 = os.getloadavg()[0]
        free_cores = max(0, cpu - 1 - load1)
        return min(24, max(4, int(free_cores // 2)))
    except (OSError, AttributeError):
        return 4


def _fmt_float(x):
    # Python's str(float) is the shortest round-trip repr (float(str(x))
    # == x always since 3.1) -- safe to hand straight to argv/sys.argv
    # parsing in src/globalvar.py (`float(sys.argv[2])`).
    return repr(float(x))


@dataclasses.dataclass(frozen=True)
class Job:
    CMR2: float
    CMC: float
    light_element: str
    liquidus_eq: str
    chi_Si_icb: float = None  # None for S/Si; required for S+Si
    seed: int = dataclasses.field(default=None, compare=False)  # provenance only

    def __post_init__(self):
        if self.light_element not in ("S", "Si", "S+Si"):
            raise ValueError(f"light_element must be S, Si or S+Si (got {self.light_element!r})")
        if self.liquidus_eq not in ("Edmund", "Steinbruegge"):
            raise ValueError(f"liquidus_eq must be Edmund or Steinbruegge (got {self.liquidus_eq!r})")
        if self.light_element == "S+Si" and self.chi_Si_icb is None:
            raise ValueError("S+Si job requires chi_Si_icb (got None)")
        if self.light_element != "S+Si" and self.chi_Si_icb is not None:
            raise ValueError(f"chi_Si_icb is only used for S+Si (got {self.chi_Si_icb} for "
                             f"{self.light_element}; globalvar.py would silently use 0.0)")

    @property
    def job_id(self):
        chi = "" if self.chi_Si_icb is None else _fmt_float(self.chi_Si_icb)
        key = "|".join([
            _fmt_float(self.CMR2), _fmt_float(self.CMC),
            self.light_element, self.liquidus_eq, chi,
        ])
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]

    def model_path(self, src_dir=SRC_DIR):
        # Mirrors src/globalvar.py's model_path string formula
        # byte-for-byte -- this is the resumability oracle, so any drift
        # here silently breaks "skip already-completed jobs".
        return (Path(src_dir) / "results" /
                ("CMR2_{:.17f}_CMC_{:.17f}_{}_{}".format(
                    self.CMR2, self.CMC, self.light_element, self.liquidus_eq)))

    def pmetadata_file(self, src_dir=SRC_DIR):
        chi = 0.0 if self.chi_Si_icb is None else self.chi_Si_icb
        return self.model_path(src_dir) / "pMetaData_{:.2f}.csv".format(chi)

    def argv(self):
        args = ["main.py", "p", _fmt_float(self.CMR2), _fmt_float(self.CMC),
                self.light_element, self.liquidus_eq]
        if self.light_element == "S+Si":
            args.append(_fmt_float(self.chi_Si_icb))
        return args

    def as_record(self):
        return {
            "CMR2": self.CMR2, "CMC": self.CMC,
            "light_element": self.light_element, "liquidus_eq": self.liquidus_eq,
            "chi_Si_icb": self.chi_Si_icb, "seed": self.seed,
        }


def load_manifest(path):
    """Parse the manifest CSV into a list of `Job`s. Raises (no silent
    fallback, PROJECT_RULES.md rule 2) on a missing required column or an
    S+Si row with no chi_Si_icb."""
    jobs = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"CMR2", "CMC", "light_element", "liquidus_eq"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"manifest {path} missing required column(s): {sorted(missing)}")
        for i, row in enumerate(reader):
            chi_raw = (row.get("chi_Si_icb") or "").strip()
            seed_raw = (row.get("seed") or "").strip()
            try:
                jobs.append(Job(
                    CMR2=float(row["CMR2"]), CMC=float(row["CMC"]),
                    light_element=row["light_element"].strip(),
                    liquidus_eq=row["liquidus_eq"].strip(),
                    chi_Si_icb=float(chi_raw) if chi_raw else None,
                    seed=int(seed_raw) if seed_raw else None,
                ))
            except ValueError as e:
                raise ValueError(f"manifest {path} data row {i + 1}: {e}") from None
    ids = [j.job_id for j in jobs]
    if len(set(ids)) != len(ids):
        dup = sorted({x for x in ids if ids.count(x) > 1})
        raise ValueError(f"manifest {path} has duplicate jobs (job_id {dup}): two rows "
                         "would write the same output files")
    return jobs


MANIFEST_FIELDS = ["CMR2", "CMC", "light_element", "liquidus_eq", "chi_Si_icb", "seed"]


def write_manifest(path, jobs):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(MANIFEST_FIELDS)
        for j in jobs:
            w.writerow([_fmt_float(j.CMR2), _fmt_float(j.CMC), j.light_element, j.liquidus_eq,
                        "" if j.chi_Si_icb is None else _fmt_float(j.chi_Si_icb),
                        "" if j.seed is None else j.seed])


def mc_jobs(n, seed_base, mean_cmr2=0.346, std_cmr2=0.014, cmc0=0.426,
            liquidus_eq="Edmund", chi_si_values=None):
    """The Monte Carlo ensemble that TACC.LS6.create.parallel.launcher.py
    + monteCarlo.run.py + scheduler.py produce today, as an explicit job
    list: draw i uses seed `seed_base + i` and the same draw as
    monteCarlo.run.py (default_rng(seed).normal(mean, std, 1); CMC =
    cmc0*mean/CMR2), then scheduler.py's compositions -- S+Si at each
    chi_Si_icb in linspace(0, 0.15, 16), then S and Si."""
    import numpy as np
    if chi_si_values is None:
        chi_si_values = np.linspace(0.0, 0.15, 16)
    jobs = []
    for k in range(n):
        seed = seed_base + k
        cmr2 = float(np.random.default_rng(seed).normal(mean_cmr2, std_cmr2, 1)[0])
        cmc = cmc0 * mean_cmr2 / cmr2
        for chi in chi_si_values:
            jobs.append(Job(cmr2, cmc, "S+Si", liquidus_eq, float(chi), seed=seed))
        for el in ("S", "Si"):
            jobs.append(Job(cmr2, cmc, el, liquidus_eq, seed=seed))
    return jobs


def _git(args, repo_root=REPO_ROOT):
    try:
        out = subprocess.run(["git"] + args, cwd=str(repo_root),
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"git unavailable: {e}"
    if out.returncode != 0:
        return None, out.stderr.strip()
    return out.stdout, None


def provenance(repo_root=REPO_ROOT):
    """Run-level provenance (requirement 5), computed ONCE per runner
    process and stamped onto every status-log record and every completion
    sentinel -- so each job line is self-contained even when a TACC
    allocation spreads jobs over many hosts.

    Nothing is silently dropped (PROJECT_RULES.md rule 2): a value that
    cannot be determined is recorded as null together with the reason
    (`*_error`), never omitted or guessed.
    """
    prov = {"host": socket.gethostname(), "python": sys.executable,
            "python_version": sys.version.split()[0]}
    sha, err = _git(["rev-parse", "HEAD"], repo_root)
    prov["git_sha"] = sha.strip() if sha else None
    if err:
        prov["git_sha_error"] = err
    porcelain, err = _git(["status", "--porcelain", "--", "src"], repo_root)
    # A dirty src/ means the SHA alone does not identify the code that ran.
    prov["git_src_dirty"] = bool(porcelain.strip()) if porcelain is not None else None

    pins = {}
    req = Path(repo_root) / "requirements.txt"
    try:
        for line in req.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if "==" in line:
                pkg, ver = line.split("==", 1)
                pins[pkg.strip()] = ver.strip()
    except OSError as e:
        prov["dependency_pins_error"] = str(e)
    prov["dependency_pins"] = pins

    # What is actually installed in the interpreter that will run the
    # jobs -- the pins say what SHOULD be there; this says what is.
    try:
        from importlib import metadata
    except ImportError:  # pragma: no cover (py<3.8)
        metadata = None
    installed = {}
    for pkg in pins:
        try:
            installed[pkg] = metadata.version(pkg) if metadata else None
        except Exception as e:  # PackageNotFoundError
            installed[pkg] = None
    prov["installed_versions"] = installed
    prov["pins_match_installed"] = all(installed.get(k) == v for k, v in pins.items()) if pins else None
    return prov


def git_sha(repo_root=REPO_ROOT):
    return provenance(repo_root)["git_sha"]


def dependency_pins(repo_root=REPO_ROOT):
    return provenance(repo_root)["dependency_pins"]


def sentinel_path(job, src_dir=SRC_DIR):
    chi = 0.0 if job.chi_Si_icb is None else job.chi_Si_icb
    return job.model_path(src_dir) / ".runner_done_{:.2f}.json".format(chi)


def already_done(job, src_dir=SRC_DIR):
    """Resumability oracle: the job's completion sentinel exists.

    NOT "the pMetaData csv exists" (the oracle monteCarlo.run.py and the
    README knox recipe use): src/main.py opens pMetaData_<chi>.csv with
    'w' and writes its header row BEFORE the ricb sweep starts
    (main.py:146-149), so a job killed mid-sweep leaves the csv on disk
    and that check would skip it forever. The sentinel is written by
    this runner only after main.py exits 0 and its csv has been read
    back, via an atomic rename -- it exists iff the job finished.
    """
    return sentinel_path(job, src_dir).exists()


def summarize_error_codes(csv_path):
    """Per-job status in item 16's vocabulary: count the pMetaData csv's
    per-radius `error_code` column by `ErrorCode` name. A code that is not
    in the enum is reported as UNRECOGNIZED_<n> (loud, not dropped)."""
    counts = {}
    n_rows = 0
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        if "error_code" not in (reader.fieldnames or []):
            raise ValueError(f"{csv_path}: no error_code column (pre-v1.3.0 output?)")
        for row in reader:
            n_rows += 1
            raw = row["error_code"]
            try:
                name = ErrorCode(int(float(raw))).name
            except (ValueError, TypeError):
                name = f"UNRECOGNIZED_{raw}"
            counts[name] = counts.get(name, 0) + 1
    return n_rows, counts


def job_status_from_codes(counts):
    """One headline ErrorCode name per job: CONVERGED if every radius
    converged, else the most frequent non-CONVERGED code (ties broken by
    the lower ErrorCode value). The full per-code counts are always
    recorded next to it -- this is a label, not a loss of information."""
    bad = {k: v for k, v in counts.items() if k != ErrorCode.CONVERGED.name}
    if not bad:
        return ErrorCode.CONVERGED.name

    def order(name):
        return ErrorCode[name].value if name in ErrorCode.__members__ else 99
    return sorted(bad, key=lambda k: (-bad[k], order(k)))[0]


class StatusLog:
    """Append-only JSONL status log, one line per job-attempt event
    (`start`, `end`). Never rewrites or truncates (resumed runs append)."""

    def __init__(self, path, prov=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prov = prov if prov is not None else provenance()

    def _write(self, record):
        # One os.write on an O_APPEND fd per record: concurrent writers
        # (local worker threads, or many TACC `run-one` processes sharing
        # one log) each land a whole line, never an interleaved one.
        line = (json.dumps(record, default=str) + "\n").encode("utf-8")
        fd = os.open(str(self.path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)

    def _base(self, event, job, run_id):
        return {"event": event, "run_id": run_id, "job_id": job.job_id,
                **job.as_record(), "ts": time.time(),
                "iso_time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "runner_pid": os.getpid(), **self.prov}

    def start(self, job, run_id):
        self._write(self._base("start", job, run_id))

    def end(self, job, run_id, status, returncode, duration_s, extra=None):
        record = self._base("end", job, run_id)
        record.update({"status": status, "returncode": returncode,
                       "duration_s": duration_s})
        if extra:
            record.update(extra)
        self._write(record)


def _child_env():
    # One BLAS thread per worker (PROJECT_RULES.md rule 15) -- a worker
    # pool of N processes each spawning a multi-threaded BLAS would
    # oversubscribe a shared box far past N.
    env = dict(os.environ)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[var] = "1"
    env.setdefault("MPLBACKEND", "Agg")
    return env


def _write_sentinel(path, payload):
    tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
    with open(tmp, "w") as f:
        json.dump(payload, f, default=str, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)  # atomic: the sentinel is either absent or whole


def run_one_job(job, src_dir=SRC_DIR, status_log=None, run_id=None,
                python_exe=None, timeout=None):
    """Run one job as `nice -n 10 <python> main.py p ...` (rule 15: nice
    10, one BLAS thread). Returns a dict describing the outcome; never
    raises on a job failure -- that failure IS the result, recorded.

    status (end record):
      * an ErrorCode name (CONVERGED, NEWTON_MAXIT, ...) when main.py
        exited 0 and its csv was read back -> sentinel written, job done;
      * RunnerStatus.PROCESS_CRASHED when it exited nonzero / by signal /
        timed out -> no sentinel, re-run on resume;
      * RunnerStatus.INCOMPLETE_OUTPUT when it exited 0 but its csv is
        missing or has no data rows -> no sentinel, re-run on resume.
    """
    python_exe = python_exe or sys.executable
    src_dir = Path(src_dir)
    # job.argv()[0] is the literal 'main.py' placeholder (the sys.argv
    # shape src/globalvar.py expects); the subprocess uses the real path.
    cmd = ["nice", "-n", "10", python_exe, str(src_dir / "main.py")] + job.argv()[1:]
    # results/ is relative to main.py's cwd (globalvar.model_path) and
    # nothing in src/ creates it (CLAUDE.md "Running").
    (src_dir / "results").mkdir(exist_ok=True)

    if status_log is not None:
        status_log.start(job, run_id)

    start = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(src_dir), env=_child_env(),
                              capture_output=True, text=True, timeout=timeout)
        returncode = proc.returncode
        stderr_tail = proc.stderr[-4000:] if proc.stderr else ""
    except subprocess.TimeoutExpired:
        returncode = None
        stderr_tail = f"TIMEOUT after {timeout}s"
    end = time.time()

    csv_path = job.pmetadata_file(src_dir)
    n_rows, counts, read_error = 0, {}, None
    if returncode == 0:
        try:
            n_rows, counts = summarize_error_codes(csv_path)
        except (OSError, ValueError) as e:
            read_error = str(e)

    if returncode != 0:
        status = RunnerStatus.PROCESS_CRASHED.value
    elif read_error or n_rows == 0:
        status = RunnerStatus.INCOMPLETE_OUTPUT.value
    else:
        status = job_status_from_codes(counts)

    extra = {"n_rows": n_rows, "error_code_counts": counts,
             "stderr_tail": stderr_tail, "start_time": start, "end_time": end}
    if read_error:
        extra["read_error"] = read_error
    done = status not in (RunnerStatus.PROCESS_CRASHED.value,
                          RunnerStatus.INCOMPLETE_OUTPUT.value)
    if done:
        prov = status_log.prov if status_log is not None else provenance()
        _write_sentinel(sentinel_path(job, src_dir), {
            "job_id": job.job_id, **job.as_record(), "run_id": run_id,
            "status": status, "n_rows": n_rows, "error_code_counts": counts,
            "start_time": start, "end_time": end, "output_csv": str(csv_path),
            **prov,
        })
    if status_log is not None:
        status_log.end(job, run_id, status, returncode, end - start, extra=extra)
    return {"job_id": job.job_id, "status": status, "returncode": returncode,
            "duration_s": end - start, "done": done, "n_rows": n_rows,
            "error_code_counts": counts, "stderr_tail": stderr_tail}


def run_local(jobs, src_dir=SRC_DIR, status_log_path=None, workers=None,
              run_id=None, python_exe=None, force=False, timeout=None):
    """Local backend: a capped worker pool (PIE_WORKERS, rule 15) running
    jobs via `subprocess`. Skips any job already done unless `force`."""
    import concurrent.futures

    run_id = run_id or str(int(time.time()))
    status_log_path = status_log_path or (Path(src_dir) / "results" / "runner_status.jsonl")
    status_log = StatusLog(status_log_path)
    workers = workers or pie_workers()

    todo = [j for j in jobs if force or not already_done(j, src_dir)]
    skipped = len(jobs) - len(todo)
    results = []
    if not todo:
        return {"run_id": run_id, "total": len(jobs), "skipped": skipped, "results": []}

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, len(todo))) as pool:
        # ThreadPoolExecutor, not ProcessPoolExecutor: each job IS already
        # a separate OS process (subprocess.run); a thread pool here just
        # bounds how many are in flight at once without adding a second
        # layer of process forking on top (rule 15: never multiply
        # parallelism layers).
        futs = {pool.submit(run_one_job, j, src_dir, status_log, run_id,
                             python_exe, timeout): j for j in todo}
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())

    return {"run_id": run_id, "total": len(jobs), "skipped": skipped, "results": results}


def write_tacc_launcher(jobs, manifest_path, src_dir=SRC_DIR,
                        launcher_out="commands_launcher", status_log_path=None,
                        python_exe=None, force=False):
    """TACC backend: writes the `commands_launcher` file that the existing
    `src/TACC.LS6.parallel.run.slurm` (LAUNCHER_JOB_FILE=commands_launcher,
    run from src/) consumes unchanged. Each line is one job routed back
    through this runner (`robust_runner.py run-one <manifest> --index i`),
    so a TACC job gets the same per-job status record + provenance as a
    local one. Already-done jobs are left out (same oracle as the local
    backend) unless `force`, so resubmitting after a partial allocation
    only redoes missing work; `run-one` re-checks at run time too.
    """
    python_exe = python_exe or sys.executable
    manifest_path = Path(manifest_path).resolve()
    status_log_path = Path(status_log_path or (Path(src_dir) / "results" / "runner_status.jsonl")).resolve()
    runner = Path(__file__).resolve()
    lines = []
    for idx, job in enumerate(jobs):
        if not force and already_done(job, src_dir):
            continue
        lines.append(" ".join([
            python_exe, str(runner), "run-one", str(manifest_path),
            "--index", str(idx), "--status-log", str(status_log_path),
            "--src-dir", str(Path(src_dir).resolve()),
        ] + (["--force"] if force else [])) + "\n")
    out_path = Path(src_dir) / launcher_out
    with open(out_path, "w") as f:
        f.writelines(lines)
    return {"launcher_path": str(out_path), "total": len(jobs),
            "written": len(lines), "skipped": len(jobs) - len(lines)}


def run_one(jobs, index, src_dir=SRC_DIR, status_log_path=None, run_id=None,
            python_exe=None, force=False, timeout=None):
    """Run manifest row `index` (0-based, header excluded) -- the unit a
    TACC LAUNCHER line executes. Skips if already done unless `force`."""
    job = jobs[index]
    if not force and already_done(job, src_dir):
        return {"job_id": job.job_id, "status": "SKIPPED_ALREADY_DONE"}
    status_log_path = status_log_path or (Path(src_dir) / "results" / "runner_status.jsonl")
    return run_one_job(job, src_dir, StatusLog(status_log_path),
                       run_id or os.environ.get("SLURM_JOB_ID") or str(int(time.time())),
                       python_exe, timeout)


def _parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run a manifest (local) or write a TACC launcher file")
    run_p.add_argument("manifest")
    run_p.add_argument("--backend", choices=["local", "tacc"], default="local")
    run_p.add_argument("--status-log", default=None)
    run_p.add_argument("--launcher-out", default="commands_launcher")
    run_p.add_argument("--workers", type=int, default=None,
                       help="default: PIE_WORKERS cap (PROJECT_RULES.md rule 15)")
    run_p.add_argument("--force", action="store_true", help="re-run jobs whose output exists")
    run_p.add_argument("--timeout", type=float, default=None, help="per-job seconds")
    run_p.add_argument("--src-dir", default=str(SRC_DIR),
                       help="directory holding main.py; results/ goes under it (default: this file's dir)")

    mc_p = sub.add_parser("make-mc-manifest",
                          help="write the seeded Monte Carlo ensemble as a manifest")
    mc_p.add_argument("out")
    mc_p.add_argument("--n", type=int, required=True, help="number of CMR2/CMC draws")
    mc_p.add_argument("--seed-base", type=int, required=True)
    mc_p.add_argument("--liquidus-eq", default="Edmund", choices=["Edmund", "Steinbruegge"])

    one_p = sub.add_parser("run-one", help="run one manifest row (one TACC LAUNCHER line)")
    one_p.add_argument("manifest")
    one_p.add_argument("--index", type=int, required=True)
    one_p.add_argument("--status-log", default=None)
    one_p.add_argument("--force", action="store_true")
    one_p.add_argument("--timeout", type=float, default=None)
    one_p.add_argument("--src-dir", default=str(SRC_DIR))
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.command == "make-mc-manifest":
        jobs = mc_jobs(args.n, args.seed_base, liquidus_eq=args.liquidus_eq)
        write_manifest(args.out, jobs)
        print(json.dumps({"manifest": args.out, "draws": args.n, "jobs": len(jobs)}))
        return 0
    jobs = load_manifest(args.manifest)
    if args.command == "run-one":
        result = run_one(jobs, args.index, src_dir=args.src_dir,
                         status_log_path=args.status_log,
                         force=args.force, timeout=args.timeout)
        print(json.dumps({k: v for k, v in result.items() if k != "stderr_tail"}))
        return 0 if result.get("done") or result["status"] == "SKIPPED_ALREADY_DONE" else 1
    if args.backend == "local":
        result = run_local(jobs, src_dir=args.src_dir, status_log_path=args.status_log,
                           workers=args.workers, force=args.force,
                           timeout=args.timeout)
        statuses = {}
        for r in result["results"]:
            statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        print(json.dumps({"run_id": result["run_id"], "total": result["total"],
                          "skipped": result["skipped"], "ran": len(result["results"]),
                          "statuses": statuses}, indent=2))
        return 0 if all(r["done"] for r in result["results"]) else 1
    result = write_tacc_launcher(jobs, args.manifest, src_dir=args.src_dir,
                                 launcher_out=args.launcher_out,
                                 status_log_path=args.status_log, force=args.force)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
