"""Contract tier: root requirements.txt, tests/requirements.txt and
pyproject.toml must never drift apart on shared runtime packages. Owner
decision (2026-09-29): every dependency manifest pins exact versions, and
root/tests must agree on the packages they share -- see PROJECT_RULES.md.

pyproject.toml (board item 28e) joined this contract the day it was
added: requirements.txt stays the source of truth (PROJECT_RULES.md rule
3b), pyproject.toml's `[project.dependencies]` must pin the exact same
versions for every package it lists.
"""
import pathlib
import re
import tomllib

import pytest

pytestmark = pytest.mark.contract

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

PIN_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.-]+)")


def _parse_pins(path):
    pins = {}
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        m = PIN_RE.match(line)
        if m:
            pins[m.group(1).lower()] = m.group(2)
        else:
            pytest.fail(
                f"{path}: line {line!r} is not an exact pin "
                f"(PROJECT_RULES.md: every manifest pins exact versions)"
            )
    return pins


def test_root_and_testsys_requirements_pin_exact_versions_and_agree():
    root_pins = _parse_pins(ROOT / "requirements.txt")
    testsys_pins = _parse_pins(ROOT / "tests" / "requirements.txt")

    assert root_pins, "requirements.txt has no pins"
    assert testsys_pins, "tests/requirements.txt has no pins"

    shared = set(root_pins) & set(testsys_pins)
    assert shared == set(root_pins), (
        "requirements.txt has package(s) not present in "
        f"tests/requirements.txt: {set(root_pins) - set(testsys_pins)}"
    )
    mismatched = {
        pkg: (root_pins[pkg], testsys_pins[pkg])
        for pkg in shared
        if root_pins[pkg] != testsys_pins[pkg]
    }
    assert not mismatched, (
        f"requirements.txt and tests/requirements.txt disagree on pinned "
        f"versions (root_version, testsys_version): {mismatched}"
    )


def _parse_pyproject_pins(path):
    data = tomllib.loads(path.read_text())
    deps = data.get("project", {}).get("dependencies", [])
    pins = {}
    for dep in deps:
        dep = dep.strip()
        m = PIN_RE.match(dep)
        if m:
            pins[m.group(1).lower()] = m.group(2)
        else:
            pytest.fail(
                f"{path}: dependency {dep!r} is not an exact pin "
                f"(PROJECT_RULES.md: every manifest pins exact versions)"
            )
    return pins


def test_pyproject_dependencies_pin_exact_versions_and_agree_with_requirements():
    root_pins = _parse_pins(ROOT / "requirements.txt")
    pyproject_pins = _parse_pyproject_pins(ROOT / "pyproject.toml")

    assert root_pins, "requirements.txt has no pins"
    assert pyproject_pins, "pyproject.toml has no [project.dependencies] pins"

    # requirements.txt remains the source of truth (PROJECT_RULES.md rule
    # 3b): every package pyproject.toml lists must match requirements.txt
    # exactly, and pyproject.toml must not be missing any of them (it may
    # not add extra packages requirements.txt doesn't have either, so the
    # two sets must be equal, not just pyproject subset-of-root).
    assert set(pyproject_pins) == set(root_pins), (
        "pyproject.toml's [project.dependencies] and requirements.txt list "
        f"different packages: pyproject-only={set(pyproject_pins) - set(root_pins)}, "
        f"requirements-only={set(root_pins) - set(pyproject_pins)}"
    )
    mismatched = {
        pkg: (root_pins[pkg], pyproject_pins[pkg])
        for pkg in root_pins
        if root_pins[pkg] != pyproject_pins[pkg]
    }
    assert not mismatched, (
        f"requirements.txt and pyproject.toml disagree on pinned versions "
        f"(root_version, pyproject_version): {mismatched}"
    )
