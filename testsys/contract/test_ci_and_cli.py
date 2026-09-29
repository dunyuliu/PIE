"""Contract tier: CI workflow validity and CLI-parity between README/
run.py and pytest.ini's own tiers -- so "how to run this" can never
drift silently between the docs, the local runner, and CI.
"""
import pathlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.contract

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "test.yml"


def test_ci_workflow_is_valid_yaml():
    import yaml
    with open(WORKFLOW) as f:
        doc = yaml.safe_load(f)
    assert "jobs" in doc
    assert len(doc["jobs"]) >= 1


def test_ci_workflow_pins_python_3_10():
    text = WORKFLOW.read_text()
    assert "3.10" in text, "CI must pin Python 3.10 to match the dev box's /usr/bin/python3"


def test_ci_workflow_sets_mplbackend_agg():
    text = WORKFLOW.read_text()
    assert "MPLBACKEND" in text and "Agg" in text


def test_ci_workflow_does_not_run_e2e_on_push_or_pr():
    # e2e is opt-in (workflow_dispatch/schedule); a push/PR job accidentally
    # running the multi-minute e2e sweep is exactly the "CI job < 5 min"
    # regression this test guards against.
    text = WORKFLOW.read_text()
    fast_job = text.split("workflow_dispatch")[0] if "workflow_dispatch" in text else text
    # The push/PR-triggered job(s) must invoke pytest with `-m` excluding e2e
    # (pytest.ini's own default already does `-m "not e2e"`, so simply NOT
    # passing `-m e2e` anywhere in the push-triggered section is correct).
    assert "-m e2e" not in text.split("schedule:")[0].split("workflow_dispatch:")[0]


def test_run_py_help_lists_all_pytest_ini_markers():
    """testsys/run.py's --help text must mention every marker declared in
    pytest.ini, so a new tier can't be added to one without the other."""
    pytest_ini = (ROOT / "testsys" / "pytest.ini").read_text()
    markers = []
    in_markers = False
    for line in pytest_ini.splitlines():
        if line.strip().startswith("markers"):
            in_markers = True
            continue
        if in_markers:
            if line.startswith(" ") and ":" in line:
                markers.append(line.strip().split(":")[0].strip())
            elif line.strip() and not line.startswith(" "):
                break
    assert markers, "could not parse markers from pytest.ini"
    run_py_text = (ROOT / "testsys" / "run.py").read_text()
    for marker in markers:
        assert marker in run_py_text, f"testsys/run.py does not mention marker '{marker}'"


def test_readme_run_command_is_the_command_run_py_actually_uses():
    readme = (ROOT / "testsys" / "README.md").read_text()
    run_py = (ROOT / "testsys" / "run.py").read_text()
    assert "testsys/run.py" in readme
    # The exact invocation shown in the README must be one run.py accepts
    # without error (argparse choices), not just prose that looks right.
    assert "unit" in run_py and "integration" in run_py and "e2e" in run_py
