"""Contract tier: `docs/` stays lean (PROJECT_RULES.md rule 1b, board item
37). `docs/user/**` is the live MkDocs site and is unbounded; everything
else under `docs/` is a small, named, explicitly bounded allowlist of
dev/history docs -- not an open-ended dumping ground. Three checks:

1. Every tracked file under `docs/` outside `docs/user/` must be on the
   allowlist below, named one at a time (rule 1b: "name it in the
   allowlist test's own list first, or don't add it").
2. The total count of tracked files under `docs/` outside `docs/user/`
   stays under a fixed cap (currently 17; cap set to 20 -- enough
   headroom to add a couple of genuinely new dated notes one at a time
   without raising this cap, but tight enough that a new run-artifact
   tree (dozens to hundreds of files, per the rule's incident writeup)
   trips it immediately even if every individual file were somehow
   allowlisted first).
3. No directory or file anywhere under `docs/` (`docs/user/` included)
   matches `*_scripts`, `*_figs`, or `*_measurement` -- the exact shape of
   the run-artifact trees rule 1b's incident removed -- except the one
   documented, load-bearing exception:
   `docs/notes/item18b_paper_filter_recompute_2026-10-04_scripts/`, read
   at runtime by `tests/contract/test_item18b_isnow_filter.py`.
"""
import pathlib
import subprocess

import pytest

pytestmark = pytest.mark.contract

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Named one at a time per rule 1b. Paths are relative to the repo root,
# forward-slash, as returned by `git ls-files`.
ALLOWED_DOCS_FILES = frozenset({
    "docs/notes/evolution_design.md",
    "docs/notes/failure_analysis_2026-09-28.md",
    "docs/notes/failure_analysis_fig1_cmr2_by_endstate.png",
    "docs/notes/failure_analysis_fig2_death_radius.png",
    "docs/notes/failure_analysis_fig3_zero_rows_vs_chiSi.png",
    "docs/notes/item18b_paper_filter_recompute_2026-10-04.md",
    "docs/notes/item18_quantify_2026-10-01.md",
    "docs/notes/perf_v1.3.2.md",
    "docs/notes/perf_v1.3.3.md",
    "docs/notes/perf_v1.3.4.md",
    "docs/notes/solver_v1.3.0.md",
    "docs/notes/steinbruegge_anchor_2026-09-30.md",
    "docs/audits/AUDIT_2026-09-29_buglist.md",
    "docs/audits/AUDIT_2026-09-29_solver-failures.md",
})

# The one documented exception to the no-artifact-tree rule: this directory
# is load-bearing (read at runtime by test_item18b_isnow_filter.py), so any
# file tracked under it is allowed without being named individually above.
ALLOWED_ARTIFACT_TREE_PREFIX = (
    "docs/notes/item18b_paper_filter_recompute_2026-10-04_scripts/"
)

# Rule 1b: "the count ... stays under a fixed cap, so the allowlist can grow
# one named file at a time but can't quietly regrow into a second pile."
# Current count (ALLOWED_DOCS_FILES + the scripts-tree files) is 17; 20
# gives headroom for a couple of ad hoc additions without a rule change,
# while still being orders of magnitude below the ~537 the incident found.
MAX_NON_USER_DOCS_FILES = 20

ARTIFACT_TREE_PATTERNS = ("_scripts", "_figs", "_measurement")


def _tracked_docs_files():
    result = subprocess.run(
        ["git", "ls-files", "docs/"],
        cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _is_under_docs_user(rel_path):
    return rel_path == "docs/user" or rel_path.startswith("docs/user/")


def test_non_user_docs_files_are_all_on_the_named_allowlist():
    tracked = _tracked_docs_files()
    outside_user = [p for p in tracked if not _is_under_docs_user(p)]
    offenders = [
        p for p in outside_user
        if p not in ALLOWED_DOCS_FILES
        and not p.startswith(ALLOWED_ARTIFACT_TREE_PREFIX)
    ]
    assert not offenders, (
        "file(s) tracked under docs/ outside docs/user/ are not on "
        "test_docs_lean.py's ALLOWED_DOCS_FILES allowlist (PROJECT_RULES.md "
        "rule 1b: name a new file in the allowlist first, or put it in "
        f"results/ and cite it by SHA instead): {sorted(offenders)}"
    )


def test_non_user_docs_file_count_stays_under_the_cap():
    tracked = _tracked_docs_files()
    outside_user = [p for p in tracked if not _is_under_docs_user(p)]
    assert len(outside_user) <= MAX_NON_USER_DOCS_FILES, (
        f"docs/ outside docs/user/ has grown to {len(outside_user)} tracked "
        f"files (cap {MAX_NON_USER_DOCS_FILES}, PROJECT_RULES.md rule 1b) -- "
        "this is exactly the silent regrowth the rule exists to catch: "
        f"{sorted(outside_user)}"
    )


def test_no_run_artifact_trees_under_docs_except_the_documented_exception():
    tracked = _tracked_docs_files()
    offenders = []
    for rel_path in tracked:
        if rel_path.startswith(ALLOWED_ARTIFACT_TREE_PREFIX):
            continue
        parts = pathlib.PurePosixPath(rel_path).parts
        for part in parts:
            stem = part[:-len(pathlib.PurePosixPath(part).suffix)] if "." in part else part
            if any(stem.endswith(pat) or part.endswith(pat) for pat in ARTIFACT_TREE_PATTERNS):
                offenders.append(rel_path)
                break
    assert not offenders, (
        "path component(s) under docs/ match a run-artifact-tree pattern "
        "(*_scripts / *_figs / *_measurement) that PROJECT_RULES.md rule 1b "
        "forbids (the 2026-10-07 incident removed ~537 such files); the "
        "only allowed exception is "
        f"{ALLOWED_ARTIFACT_TREE_PREFIX!r}: {sorted(offenders)}"
    )
