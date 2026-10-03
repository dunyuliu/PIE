"""Contract tests for src/robust_runner.py (PATHWAY_FORWARD.md item 22): the
manifest CSV schema, the completion-sentinel resumability oracle, the
TACC commands_launcher format, and the status-log/provenance record
shape. File I/O only; no physics solve, no subprocess of main.py.

New file for a new module; edits no existing src/*.py or testsys/*.py.
"""
import csv
import json

import pytest

pytestmark = pytest.mark.contract

from pie import robust_runner as rr  # pie is installed via pyproject.toml (board item 28e)

HEADER = ("CMR2", "CMC", "light_element", "liquidus_eq", "chi_Si_icb")


def _write(path, rows, header=HEADER):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def test_load_manifest_parses_all_compositions(tmp_path):
    jobs = rr.load_manifest(_write(tmp_path / "m.csv", [
        ("0.346", "0.424", "S", "Edmund", ""),
        ("0.346", "0.424", "Si", "Steinbruegge", ""),
        ("0.346", "0.424", "S+Si", "Edmund", "0.05"),
    ]))
    assert [(j.light_element, j.chi_Si_icb) for j in jobs] == [("S", None), ("Si", None), ("S+Si", 0.05)]


def test_manifest_round_trips_through_write_manifest(tmp_path):
    jobs = rr.mc_jobs(3, seed_base=5)
    rr.write_manifest(tmp_path / "mc.csv", jobs)
    back = rr.load_manifest(tmp_path / "mc.csv")
    assert back == jobs  # exact float round trip (repr) -> same output paths
    assert [j.seed for j in back] == [j.seed for j in jobs]


@pytest.mark.parametrize("rows,header,match", [
    ([("0.346", "0.424", "S", "")], ("CMR2", "CMC", "light_element", "chi_Si_icb"), "missing required column"),
    ([("0.346", "0.424", "S+Si", "Edmund", "")], HEADER, "row 1: S\\+Si job requires chi_Si_icb"),
    ([("0.346", "0.424", "S", "Edmund", ""), ("0.346", "0.424", "S", "Edmund", "")], HEADER, "duplicate jobs"),
    ([("abc", "0.424", "S", "Edmund", "")], HEADER, "row 1"),
])
def test_load_manifest_rejects_bad_input_loudly(tmp_path, rows, header, match):
    with pytest.raises(ValueError, match=match):
        rr.load_manifest(_write(tmp_path / "bad.csv", rows, header))


def test_header_only_csv_is_not_done(tmp_path):
    # Regression for the oracle monteCarlo.run.py / README knox recipe use:
    # src/main.py writes the pMetaData csv HEADER before the ricb sweep
    # starts, so "csv exists" is true for a job killed mid-sweep. Only the
    # runner's sentinel counts.
    job = rr.Job(0.346, 0.424, "S", "Edmund")
    csv_path = job.pmetadata_file(tmp_path)
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text("chi_Si_icb,ricb,error_code\n0.0,10.0,0\n")
    assert not rr.already_done(job, tmp_path)
    rr.sentinel_path(job, tmp_path).write_text("{}")
    assert rr.already_done(job, tmp_path)


def test_summarize_error_codes_reads_pmetadata_csv(tmp_path):
    p = _write(tmp_path / "pMetaData_0.00.csv",
               [("0.0", "10.0", "0"), ("0.0", "50010.0", "0"), ("0.0", "100010.0", "5.0"),
                ("0.0", "150010.0", "9")],
               header=("chi_Si_icb", "ricb", "error_code"))
    n, counts = rr.summarize_error_codes(p)
    assert n == 4
    assert counts == {"CONVERGED": 2, "RICB_GE_RCMB": 1, "UNRECOGNIZED_9": 1}
    p2 = _write(tmp_path / "old.csv", [("0.0", "10.0")], header=("chi_Si_icb", "ricb"))
    with pytest.raises(ValueError, match="no error_code column"):
        rr.summarize_error_codes(p2)


def test_tacc_launcher_lists_only_pending_jobs_as_run_one_lines(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    manifest = _write(tmp_path / "m.csv", [
        ("0.346", "0.424", "S", "Edmund", ""),
        ("0.333", "0.437", "Si", "Edmund", ""),
        ("0.333", "0.437", "S+Si", "Edmund", "0.02"),
    ])
    jobs = rr.load_manifest(manifest)
    done = rr.sentinel_path(jobs[0], src)
    done.parent.mkdir(parents=True)
    done.write_text("{}")

    res = rr.write_tacc_launcher(jobs, manifest, src_dir=src, python_exe="/opt/py",
                                 status_log_path=tmp_path / "log.jsonl")
    assert (res["total"], res["written"], res["skipped"]) == (3, 2, 1)
    lines = (src / "commands_launcher").read_text().splitlines()
    assert len(lines) == 2
    for line, idx in zip(lines, (1, 2)):
        tok = line.split()
        assert tok[0] == "/opt/py" and tok[1].endswith("pie/robust_runner.py")
        assert tok[2:4] == ["run-one", str(manifest.resolve())]
        assert tok[tok.index("--index") + 1] == str(idx)
        assert tok[tok.index("--src-dir") + 1] == str(src.resolve())
        assert tok[tok.index("--status-log") + 1] == str((tmp_path / "log.jsonl").resolve())

    forced = rr.write_tacc_launcher(jobs, manifest, src_dir=src, force=True)
    assert forced["written"] == 3


def test_status_log_records_carry_provenance(tmp_path):
    log = rr.StatusLog(tmp_path / "status.jsonl")
    job = rr.Job(0.346, 0.424, "S", "Edmund", seed=11)
    log.start(job, run_id="r1")
    log.end(job, run_id="r1", status="CONVERGED", returncode=0, duration_s=1.5)
    start, end = [json.loads(l) for l in (tmp_path / "status.jsonl").read_text().splitlines()]
    assert (start["event"], end["event"]) == ("start", "end")
    assert start["job_id"] == end["job_id"] == job.job_id and end["seed"] == 11
    for rec in (start, end):
        for key in ("git_sha", "git_src_dirty", "dependency_pins", "installed_versions",
                    "pins_match_installed", "host", "python", "runner_pid", "ts", "run_id"):
            assert key in rec, key
    assert len(start["git_sha"]) == 40
    assert start["dependency_pins"]["numpy"]  # parsed from root requirements.txt


def test_runner_imports_with_its_own_long_cli_argv():
    # Regression: the first version only padded a SHORT argv before importing
    # globalvar, so `robust_runner.py run m.csv --workers 2 ...` crashed at
    # import (float('m.csv')). Fresh interpreter, realistic argv.
    import subprocess, sys
    r = subprocess.run([sys.executable, rr.__file__, "run", "/nonexistent.csv",
                        "--workers", "2", "--status-log", "/tmp/x"],
                       capture_output=True, text=True, timeout=60)
    assert "could not convert string to float" not in r.stderr
    assert "No such file or directory: '/nonexistent.csv'" in r.stderr
    assert r.stdout == ""  # globalvar.py's import-time print(len(argv)) is suppressed
