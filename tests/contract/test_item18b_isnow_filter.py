"""Regression lock for PATHWAY_FORWARD.md item 32 / item 18(b)'s
missing-test gap: "no regression test locks the isnow in {1,3} predicate
or the stratified totals -- routed to iris-vermeulen, not yet dispatched."

Source of truth: `docs/dev/notes/item18b_paper_filter_recompute_2026-10-04_scripts/
analyze.py` (the live predicate, parsed from its own source -- not a
hand-copied reimplementation that could independently drift) and its
committed output `item18b_results.json` (the stratified population
estimates and published category totals the note's section 2 table
reports). Neither `analyze.py`'s `ZEN` (external, read-only Zenodo tree)
nor `RESULTS` (`PIE_ITEM18A_RAW_RESULTS`, an uncommitted worktree) inputs
are re-derived here (PROJECT_RULES.md rule 7) -- this test locks the
already-committed artifacts, not a fresh re-run.

Rule 16 statement:
- Population: the reduction already committed in `item18b_results.json`
  -- the paper's own published Zenodo `sort_models.py` output CSVs
  (`all_models_*MoI.csv` etc., all S+Si/chi_Si_icb>0 rows, both MOI
  configs) plus the stratified Horvitz-Thompson estimate of the item
  18(a) 1,131 S+Si/chi>0 recovered-row sample added on top.
- Question: (a) does `analyze.py`'s own row predicate for the paper's
  "snow layer" category still read `isnow in {1, 3}` (the paper's actual
  filter, confirmed against the read-only Zenodo `sort_models.py`) and
  not `isnow > 0` (item 18(a)'s predicate, which silently also counts
  `isnow == 2` and overstated published snow rows by +43%/+70%)? (b) do
  the published category totals, the stratified "+recovered" population
  estimates, and the Fig 2 (`goodTCMB_sl`, the paper's headline panel)
  delta still match what `item18b_results.json` -- and the note's own
  section 2 table -- report?
"""
import ast
import json
import pathlib
import re

import pytest

pytestmark = pytest.mark.contract

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = ROOT / "docs/dev/notes/item18b_paper_filter_recompute_2026-10-04_scripts"
ANALYZE_PY = SCRIPTS_DIR / "analyze.py"
RESULTS_JSON = SCRIPTS_DIR / "item18b_results.json"
NOTE_MD = ROOT / "docs/dev/notes/item18b_paper_filter_recompute_2026-10-04.md"

CATS = ["all", "sl", "goodTCMB", "goodTCMB_sl", "goodTCMB_goodchiS"]

# Published category totals, summed over all 12 S+Si chi_Si_icb values,
# per MOI config -- note section 2 table's "published" column.
PUBLISHED_TOTALS = {
    ("margot", "all"): 136840, ("margot", "sl"): 27817,
    ("margot", "goodTCMB"): 80731, ("margot", "goodTCMB_sl"): 10395,
    ("margot", "goodTCMB_goodchiS"): 22938,
    ("genova", "all"): 116214, ("genova", "sl"): 6698,
    ("genova", "goodTCMB"): 59827, ("genova", "goodTCMB_sl"): 4824,
    ("genova", "goodTCMB_goodchiS"): 28822,
}

# Stratified Horvitz-Thompson point estimate ("A") of the recovered-row
# addition, full ricb range -- note section 2 table's "+recovered (full
# range)" column, cross-checked exact (to float precision) against
# marta-silva's independently-computed population totals per the board
# row (+7,357 / +9,349 for the "all" category).
RECOVERED_FULL_A = {
    ("margot", "all"): 7357.197094949665, ("genova", "all"): 9349.24623928014,
    ("margot", "sl"): 255.46784016636957, ("genova", "sl"): 335.4168891360771,
    ("margot", "goodTCMB"): 732.4590017825311, ("genova", "goodTCMB"): 2108.2270545884135,
    ("margot", "goodTCMB_sl"): 14.333333333333334, ("genova", "goodTCMB_sl"): 0.0,
    ("margot", "goodTCMB_goodchiS"): 732.4590017825311,
    ("genova", "goodTCMB_goodchiS"): 2052.7368585099825,
}

# Same, restricted to heat-map-eligible rows (ricb <= 1800 km) -- note
# section 2 table's "+recovered (heat-map-eligible)" column.
RECOVERED_HM_A = {
    ("margot", "all"): 5835.072780375351, ("genova", "all"): 4649.826367742921,
    ("margot", "sl"): 159.44823232323233, ("genova", "sl"): 33.916666666666664,
    ("margot", "goodTCMB"): 147.64069264069263, ("genova", "goodTCMB"): 892.2798233882411,
    ("margot", "goodTCMB_sl"): 0.0, ("genova", "goodTCMB_sl"): 0.0,
    ("margot", "goodTCMB_goodchiS"): 147.64069264069263,
    ("genova", "goodTCMB_goodchiS"): 836.7896273098097,
}


def _extract_is_sl_predicate():
    """Parse analyze.py's actual source and return a compiled function
    isnow -> bool reproducing its `is_sl = ...` assignment, by lifting
    and evaluating that one expression node out of the real script --
    not a hand-copied truth table that could independently drift from
    what analyze.py actually executes."""
    tree = ast.parse(ANALYZE_PY.read_text())
    expr_node = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "is_sl"):
            expr_node = node.value
            break
    assert expr_node is not None, (
        "analyze.py no longer assigns an 'is_sl' variable -- the paper's "
        "snow-layer predicate was renamed or restructured; update this "
        "test's extraction logic, do not just delete the lock"
    )
    expr = ast.Expression(body=expr_node)
    ast.fix_missing_locations(expr)
    code = compile(expr, filename=str(ANALYZE_PY) + ":is_sl", mode="eval")
    return lambda isnow: eval(code, {}, {"isnow": isnow})


def test_analyze_py_is_sl_predicate_is_isnow_in_1_3_not_isnow_gt_0():
    """The paper's own filter (Zenodo sort_models.py, re-derived in item
    18b section 0) counts isnow in {1, 3} as "snow layer"; isnow == 2
    ("deep snow", no layers) does NOT count. item 18(a) used isnow > 0,
    which silently also counted isnow == 2 and overstated published snow
    rows by +43% (margot) / +70% (genova) -- see section 2 of the note.
    This locks the predicate actually executing in analyze.py today,
    evaluated at every isnow class {-1, 0, 1, 2, 3, 4} the real data use
    (not just a single True/False check, so a sign flip or an off-by-one
    boundary -- e.g. isnow >= 1 -- is caught too)."""
    predicate = _extract_is_sl_predicate()
    expected = {-1: False, 0: False, 1: True, 2: False, 3: True, 4: False}
    actual = {v: bool(predicate(v)) for v in expected}
    assert actual == expected, (
        f"analyze.py's is_sl predicate truth table is {actual}, expected "
        f"{expected} (isnow in {{1,3}}) -- if isnow==2 now maps to True "
        f"this regressed to item 18(a)'s overstating isnow>0 predicate"
    )


def _load_results():
    assert RESULTS_JSON.exists(), (
        f"{RESULTS_JSON} is missing -- it is analyze.py's committed output "
        f"and this test's only source for the stratified totals (analyze.py "
        f"itself cannot be re-run here: it needs an external read-only "
        f"Zenodo tree and an uncommitted item-18a raw-results worktree)"
    )
    return json.loads(RESULTS_JSON.read_text())


def _sum_published(results):
    totals = {}
    for key, cats in results["published"].items():
        moi = key.split("|")[0]
        for cat, n in cats.items():
            totals[(moi, cat)] = totals.get((moi, cat), 0) + n
    return totals


def _sum_estimates(results, suffix):
    totals = {}
    for cat in CATS:
        field = f"{cat}_{suffix}"
        for key, est in results["estimates"][field].items():
            moi = key.split("|")[0]
            totals[(moi, cat)] = totals.get((moi, cat), 0.0) + est["A"]
    return totals


def test_published_category_totals_match_the_note():
    """Published (Zenodo sort_models.py output) row counts per category,
    summed over all 12 S+Si chi_Si_icb values and both MOI configs --
    locks the note's section 2 table "published" column against the
    committed item18b_results.json."""
    results = _load_results()
    totals = _sum_published(results)
    for key, expected in PUBLISHED_TOTALS.items():
        assert totals.get(key) == expected, (
            f"published total for {key} is {totals.get(key)}, "
            f"note reports {expected}"
        )


def test_recovered_full_range_estimates_match_the_note():
    """Stratified Horvitz-Thompson population-addition estimate (full
    ricb range), summed over chi_Si_icb -- note section 2's "+recovered
    (full range)" column."""
    results = _load_results()
    totals = _sum_estimates(results, "full")
    for key, expected in RECOVERED_FULL_A.items():
        got = totals.get(key)
        assert got == pytest.approx(expected, rel=1e-9), (
            f"recovered-full estimate for {key} is {got}, note reports {expected}"
        )


def test_recovered_heatmap_eligible_estimates_match_the_note():
    """Same, restricted to ricb <= 1,800,010 m (heat-map-eligible rows) --
    note section 2's "+recovered (heat-map-eligible)" column."""
    results = _load_results()
    totals = _sum_estimates(results, "hm")
    for key, expected in RECOVERED_HM_A.items():
        got = totals.get(key)
        assert got == pytest.approx(expected, rel=1e-9), (
            f"recovered-heatmap estimate for {key} is {got}, note reports {expected}"
        )


def test_fig2_headline_panel_delta_is_near_zero():
    """Fig 2 (`goodTCMB_sl`, the paper's headline snow-probability heat
    map) is the panel that jointly requires goodTCMB AND snow -- the
    note's central finding is that the row-recovery exercise moves it by
    essentially nothing (margot +0.14%, genova +0.00%), unlike the
    isnow-predicate error itself (+43%/+70%, a pure labeling bug, not a
    sampling effect). This locks that delta stays small, computed fresh
    from the committed JSON's published total and recovered estimate (not
    copied from the note's own rounded percentage)."""
    results = _load_results()
    published = _sum_published(results)
    recovered = _sum_estimates(results, "full")
    margot_pct = 100.0 * recovered[("margot", "goodTCMB_sl")] / published[("margot", "goodTCMB_sl")]
    genova_pct = 100.0 * recovered[("genova", "goodTCMB_sl")] / published[("genova", "goodTCMB_sl")]
    assert margot_pct == pytest.approx(0.14, abs=0.02), (
        f"Fig 2 (goodTCMB_sl) margot delta is {margot_pct:.4f}%, "
        f"note reports +0.14% -- the headline 'barely moves' finding regressed"
    )
    assert genova_pct == pytest.approx(0.0, abs=0.02), (
        f"Fig 2 (goodTCMB_sl) genova delta is {genova_pct:.4f}%, "
        f"note reports +0.00%"
    )


# --- Doc-integrity tripwire -------------------------------------------
#
# The isnow-mismatch magnitudes (+43.3%/+70.5%, driven by isnow==2 alone
# contributing 12,036/4,722 published rows) are reported only as prose in
# the .md note -- no committed JSON breaks the published counts down by
# individual isnow value (item18b_results.json only has the 5 post-filter
# CATS, not a raw isnow>0 vs isnow-in-{1,3} comparison). This cannot be a
# byte-exact numeric lock against a committed artifact; it is a weaker
# tripwire that (a) ties the prose number to the independently-locked
# published `sl` total above via internal arithmetic, and (b) catches an
# accidental hand-edit of the note's own figures. It does NOT re-verify
# the 12,036/4,722 isnow==2 counts against raw data -- see this test
# file's module docstring and the session report for that gap.
def test_note_isnow_mismatch_prose_is_internally_consistent():
    text = NOTE_MD.read_text()
    m = re.search(
        r"margot ([\d,]+) vs ([\d,]+) rows \(\+([\d.]+)% relative, because\s*\n"
        r"\s*`isnow==2` alone contributes ([\d,]+) published rows\) and genova "
        r"([\d,]+) vs\s*\n\s*([\d,]+) \(\+([\d.]+)% relative, `isnow==2` contributes ([\d,]+)\)",
        text,
    )
    assert m is not None, (
        "could not find the isnow>0-vs-isnow-in-{1,3} mismatch paragraph in "
        f"{NOTE_MD} -- it may have been reworded; update this test's regex, "
        "don't delete the check"
    )
    margot_gt0, margot_sl, margot_pct, margot_is2, genova_gt0, genova_sl, genova_pct, genova_is2 = (
        int(m.group(1).replace(",", "")), int(m.group(2).replace(",", "")), float(m.group(3)),
        int(m.group(4).replace(",", "")), int(m.group(5).replace(",", "")), int(m.group(6).replace(",", "")),
        float(m.group(7)), int(m.group(8).replace(",", "")),
    )
    results = _load_results()
    published = _sum_published(results)

    # The note's own "isnow in {1,3}" (sl) figure must agree with the
    # independently-locked published sl total above (not just with itself).
    assert margot_sl == published[("margot", "sl")] == PUBLISHED_TOTALS[("margot", "sl")]
    assert genova_sl == published[("genova", "sl")] == PUBLISHED_TOTALS[("genova", "sl")]
    # isnow>0 total = isnow-in-{1,3} total + isnow==2 total (arithmetic
    # the note asserts but never spells out as a sum).
    assert margot_gt0 == margot_sl + margot_is2, (
        f"margot isnow>0 total {margot_gt0} != sl {margot_sl} + isnow==2 {margot_is2}"
    )
    assert genova_gt0 == genova_sl + genova_is2, (
        f"genova isnow>0 total {genova_gt0} != sl {genova_sl} + isnow==2 {genova_is2}"
    )
    assert margot_pct == pytest.approx(100.0 * (margot_gt0 - margot_sl) / margot_sl, abs=0.1)
    assert genova_pct == pytest.approx(100.0 * (genova_gt0 - genova_sl) / genova_sl, abs=0.1)
    # The headline magnitude claim itself: both relative overstatements
    # are large (>=40%), i.e. not a rounding-noise-sized effect.
    assert margot_pct >= 40.0 and genova_pct >= 40.0
