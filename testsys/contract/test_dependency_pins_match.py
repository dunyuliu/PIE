"""Contract tier: root requirements.txt and testsys/requirements.txt must
never drift apart on shared runtime packages. Owner decision (2026-09-29):
every dependency manifest pins exact versions, and root/testsys must agree
on the packages they share -- see PROJECT_RULES.md.
"""
import pathlib
import re

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
    testsys_pins = _parse_pins(ROOT / "testsys" / "requirements.txt")

    assert root_pins, "requirements.txt has no pins"
    assert testsys_pins, "testsys/requirements.txt has no pins"

    shared = set(root_pins) & set(testsys_pins)
    assert shared == set(root_pins), (
        "requirements.txt has package(s) not present in "
        f"testsys/requirements.txt: {set(root_pins) - set(testsys_pins)}"
    )
    mismatched = {
        pkg: (root_pins[pkg], testsys_pins[pkg])
        for pkg in shared
        if root_pins[pkg] != testsys_pins[pkg]
    }
    assert not mismatched, (
        f"requirements.txt and testsys/requirements.txt disagree on pinned "
        f"versions (root_version, testsys_version): {mismatched}"
    )
