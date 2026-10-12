"""Contract tier: the standing no-personal-names rule (CLAUDE.md global
rule; see board item 45, closed 2026-10-11). Docs, release notes, status
boards, commit messages and code comments must not name a real person or
agent persona -- only role-descriptive phrases. This test fails CI if any
tracked file (other than this one) reintroduces one of the persona names
already purged from the tree.

Exempt by the rule's own stated exceptions: literature citations
(Author Year), LICENSE/copyright lines, and CITATION.cff authorship --
extended here to docs/user/citing.md's real maintainer contact (the
CITATION.cff-authorship equivalent for the human-readable citing page).
docs/user/gen_params.py's `INTERNAL_MARKERS` regex is also exempt: those
name fragments are functional filter data for a doc-generation tool, not
narrative prose (flagged, not edited, per board item 45).
"""
import pathlib
import re
import subprocess

import pytest

pytestmark = pytest.mark.contract

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
THIS_FILE = pathlib.Path(__file__).resolve().relative_to(ROOT).as_posix()

# The persona names purged by board item 45, plus bare first/last-name
# forms. Hyphenated full names only need the hyphenated form, since the
# bare first-name alternative already covers a standalone first-name use.
PERSONA_NAMES = [
    "anya-petrov", "anya", "petrov",
    "dunyu-liu", "dunyu",
    "elena-hartmann", "elena", "hartmann",
    "haruto-nakamura", "haruto", "nakamura",
    "ingrid-lindqvist", "ingrid", "lindqvist",
    "iris-vermeulen", "iris", "vermeulen",
    "jordan-kim", "jordan",
    "kai-fischer", "kai", "fischer",
    "lars-eriksson", "lars", "eriksson",
    "lian-zhao", "lian", "zhao",
    "marco-bianchi", "marco", "bianchi",
    "marta-silva", "marta", "silva",
    "mira-volkov", "mira", "volkov",
    "nadia-hadid", "nadia", "hadid",
    "priya-nair", "priya", "nair",
    "rafael-santos", "rafael", "santos",
    "selin-aydin", "selin", "aydin",
    "shu-han",
    "sophia-okafor", "sophia", "okafor",
    "victor-reyes", "victor", "reyes",
    "wei-lin",
    "ziyan-chen", "ziyan",
    "zofia-kaminska", "zofia", "kaminska",
]

NAME_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(n) for n in PERSONA_NAMES) + r")['’`]?s?\b",
    re.IGNORECASE,
)

# Files exempt per the rule's own citation/authorship exceptions, and the
# one file where the names are functional filter data, not prose.
EXEMPT_FILES = {
    "CITATION.cff",
    "docs/user/citing.md",
    "docs/user/gen_params.py",
}


def _tracked_files():
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, stdout=subprocess.PIPE,
        text=True, check=True,
    )
    return [line for line in result.stdout.split("\n") if line]


def test_no_tracked_file_contains_a_persona_name():
    hits = {}
    for rel in _tracked_files():
        if rel == THIS_FILE or rel in EXEMPT_FILES:
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError):
            continue  # binary file, not prose/code text
        matches = sorted(set(NAME_PATTERN.findall(text)))
        if matches:
            hits[rel] = matches
    assert not hits, (
        f"persona name(s) found in tracked file(s), violating the "
        f"no-personal-names rule (board item 45): {hits} -- replace with a "
        f"role-descriptive phrase, or add a documented exemption to "
        f"EXEMPT_FILES in this test if it is a literature citation, "
        f"LICENSE/copyright line, or CITATION.cff-equivalent authorship"
    )
