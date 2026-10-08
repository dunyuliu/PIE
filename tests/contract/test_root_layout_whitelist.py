"""Contract tier: PROJECT_RULES.md rule 1c, the mechanical root-layout gate
(board item 39). Rule 1c specifies three checks; checks 1 and 2 are hard
assertions here, check 3 ("tidy") is explicitly report-only/non-asserting
per the rule's own text and is not implemented as a pytest assertion.
"""
import pathlib
import subprocess

import pytest

pytestmark = pytest.mark.contract

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Rule 1c check 1: the exact, enumerated whitelist of top-level tracked
# entries. An addition here must be a reviewable one-line diff to this
# list, not a silent `git add` at the root.
ROOT_WHITELIST = {
    "CHANGELOG.md",
    "CITATION.cff",
    "CLAUDE.md",
    "LICENSE",
    "PATHWAY_FORWARD.md",
    "PROJECT_RULES.md",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    ".githooks",
    ".github",
    ".gitignore",
    "docs",
    "pie",
    "scripts",
    "tests",
}

MAX_TRACKED_FILE_BYTES = 5 * 1024 * 1024  # 5 MB (rule 1c check 2)


def _tracked_root_entries():
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, stdout=subprocess.PIPE,
        text=True, check=True,
    )
    return {line.split("/", 1)[0] for line in result.stdout.split("\n") if line}


def test_tracked_root_entries_match_rule_1c_whitelist_exactly():
    tops = _tracked_root_entries()
    extra = tops - ROOT_WHITELIST
    missing = ROOT_WHITELIST - tops
    assert not extra, (
        f"untracked-by-whitelist root entr(y/ies) found: {sorted(extra)} -- "
        f"either add to ROOT_WHITELIST in this test (reviewable one-line "
        f"diff) or remove the entry (PROJECT_RULES.md rule 1c check 1)"
    )
    assert not missing, (
        f"rule 1c whitelist entr(y/ies) no longer tracked at root: "
        f"{sorted(missing)} -- update ROOT_WHITELIST in this test if the "
        f"removal was intentional (PROJECT_RULES.md rule 1c check 1)"
    )


def test_no_tracked_file_exceeds_5mb():
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, stdout=subprocess.PIPE, check=True,
    )
    rels = [p for p in result.stdout.split(b"\0") if p]
    oversized = []
    for rel in rels:
        path = ROOT / rel.decode()
        # A tracked path can be a symlink or (rarely) a gitlink; only a
        # regular file has a meaningful on-disk byte size for this check.
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_TRACKED_FILE_BYTES:
            oversized.append((rel.decode(), size))
    assert not oversized, (
        f"tracked file(s) exceed {MAX_TRACKED_FILE_BYTES} bytes: {oversized} "
        f"-- PROJECT_RULES.md rule 1c check 2"
    )
