"""Truth anchor (PROJECT_RULES.md rule 5), NOT YET IMPLEMENTABLE: this
project's `liquidus_eq='Steinbruegge'` option is named for Steinbruegge
et al. (2020), Geophysical Research Letters, doi:10.1029/2020GL089895,
whose predecessor code (github.com/gregorsteinbruegge/MercuryInterior)
this repo's `src/coreEos.py`/`src/libCore.py` descend from (see
`testsys/unit/test_truth_anchor_liquidus_table.py`'s docstring for the
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
