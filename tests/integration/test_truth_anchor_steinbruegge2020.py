"""Truth anchor (PROJECT_RULES.md rule 5), NOT YET IMPLEMENTABLE: this
project's `liquidus_eq='Steinbruegge'` option is named for Steinbruegge
et al. (2020), Geophysical Research Letters, doi:10.1029/2020GL089895,
whose predecessor code (github.com/gregorsteinbruegge/MercuryInterior)
this repo's `src/coreEos.py`/`src/libCore.py` descend from (see
`tests/unit/test_truth_anchor_liquidus_table.py`'s docstring for the
attribution). `PATHWAY_FORWARD.md` item 3 names reproducing that
paper's PUBLISHED interior-structure values (e.g. a specific core
radius / light-element fraction reported in its tables or figures) as
one of the truth anchors for this project.

PROJECT_RULES.md rule 2 ("no silent fallbacks... or placeholder data")
and the task brief's own hard rule are explicit: without a reliable way
to pull the actual published numbers from doi:10.1029/2020GL089895 in
this session (no internet access assumed reliable here), inventing a
"looks right" number to assert against would be exactly the failure
mode rule 2 exists to prevent -- worse than not having this test at
all, because it would look like independent verification while
actually being unverified.

This is intentionally left as a SINGLE, clearly-dated xfail rather than
silently omitted (PATHWAY_FORWARD.md rule 12: every open item gets a
row, not a silent gap) -- picking it up requires one of:
  (a) a follow-up session with reliable access to the paper's tables
      (or its supplementary data / the predecessor repo's own
      committed reference output, if it has any), to fill in
      `EXPECTED_STEINBRUEGGE_2020_VALUE` below with a cited number
      (page/table/figure reference required, not just a float), or
  (b) the human supplying the specific published value(s) to check
      against directly.

Update 2026-09-29 (conductor session): the CrossRef abstract for this
DOI (`curl https://api.crossref.org/works/10.1029/2020GL089895`,
verified directly, not via a subagent's unverified claim) IS readable
without a paywall and gives the paper's title ("Challenges on Mercury's
Interior Structure Posed by the New Measurements of its Obliquity and
Tides", Steinbruegge et al., Geophysical Research Letters 48(3), 2021)
plus two quantitative abstract-level constraints:
  - normalized moment of inertia factor MoI = 0.333 +/- 0.005
    (their input constraint, from an obliquity measurement -- NOT a
    PIE-model prediction, since CMR2 is an input to scheduler.py, not
    an output; asserting PIE reproduces its own input would be
    tautological, not a truth anchor)
  - inner core radius mandatorily > 600 km (their model's OUTPUT/
    conclusion, given that MoI)
The `> 600 km` inner core radius claim IS a genuine candidate
truth-anchor assertion (an independent output, not an echoed input) --
but wiring it in requires confirming which PIE output field it
corresponds to. This repo's `pMetaData*.csv` has both `ricb` (held
fixed at 10 m in every sampled row seen this session -- looks like the
innermost integration start point, not a solved-for inner-core/outer-
core boundary) and `rcmb` (~2,000-2,020 km, reads like the core-mantle
boundary, not the inner-core boundary). Neither obviously IS "inner
core radius" as Steinbruegge means it (solid/liquid core split) without
a physicist's read of `src/shootp.py`/`src/driverp.py`'s radius
convention -- left un-wired rather than guessed at, per the same rule 2
concern as the original xfail (a wrong-field assertion that happens to
pass would be worse than this xfail, since it would look verified while
checking nothing). Full table/figure values (the actual best-fit
core-radius number, not just the ">600 km" abstract threshold) remain
paywalled (Wiley 403 on both VoR and AM; no arXiv preprint found).

Opened: 2026-09-29.
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Steinbruegge et al. (2020, doi:10.1029/2020GL089895) published "
        "interior-structure value(s) needed here (e.g. a specific core "
        "radius or light-element wt% reported in the paper's tables/"
        "figures) were not available in this session (no reliable "
        "internet access) -- PROJECT_RULES.md rule 2 forbids inventing a "
        "placeholder number instead. See this file's module docstring for "
        "what is needed to close this out."
    ),
)
def test_matches_steinbruegge_2020_published_value():
    raise NotImplementedError(
        "Needs the actual published Steinbruegge et al. (2020, "
        "doi:10.1029/2020GL089895) value(s) -- not fabricated here, see "
        "module docstring."
    )
