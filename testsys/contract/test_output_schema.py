"""Contract tier: the on-disk output schema main.py/driverp.py promise.

No model solve here -- these check that the SCHEMA globalvar.py declares
(presentday_columns) is what actually gets written to a real pMetaData
CSV and to the 'misc' key of a real per-radius .h5 (both read by
downstream plotting/analysis scripts, in this repo and in the published
"Plotting and Analysis Scripts" archive), using the committed reference
fixtures as the ground truth for "what gets written", not a re-run.
"""
import pathlib

import h5py
import pandas as pd
import pytest

from conftest import import_src

pytestmark = pytest.mark.contract

REF_ROOT = pathlib.Path(__file__).resolve().parent.parent / "reference"


def test_presentday_columns_matches_written_csv_header(sys_argv_p):
    globalvar = import_src("globalvar")
    csv_path = (REF_ROOT / "zenodo_v1.0.5" / "CMR2_0.346_CMC_0.426_S+Si_Edmund"
                / "pMetaData_0.01.csv")
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
    assert header == globalvar.presentday_columns


def test_self_golden_csv_also_matches_schema(sys_argv_p):
    # The self-generated (S, Edmund, CMR2=0.346/CMC=0.424) e2e reference
    # predates neither of bb37b0a's two fixes, so both columns
    # (chi_S_bulk's header, core_mass's corrected values) must be
    # present -- this is a schema check, not a value check (that's
    # e2e's job).
    globalvar = import_src("globalvar")
    csv_path = (REF_ROOT / "self_v1.0.5" / "CMR2_0.346_CMC_0.424_S_Edmund"
                / "pMetaData_0.00.csv")
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
    assert header == globalvar.presentday_columns


def test_h5_misc_key_columns_are_a_subset_of_presentday_columns(sys_argv_p):
    # The published archive's h5 files predate the chi_S_bulk column
    # (added f06b395, after this Zenodo record's data was generated) --
    # this asserts subset, not equality, and says so.
    globalvar = import_src("globalvar")
    h5_path = (REF_ROOT / "zenodo_v1.0.5" / "CMR2_0.346_CMC_0.426_S+Si_Edmund"
               / "DataSi%wt0.01_R0500.0.h5")
    df = pd.read_hdf(h5_path, key="misc")
    missing = set(df.columns) - set(globalvar.presentday_columns)
    assert not missing, f"h5 'misc' columns not in current schema: {missing}"


def test_h5_data_keys_present(sys_argv_p):
    # driverp.py writes r/rho/T/P/g/Tad/chi_li/misc as separate keys to
    # the same file (see src/driverp.py ~L133-146) -- every downstream
    # plotting script reads all of these, not just 'misc', so a schema
    # test that only checked 'misc' would miss half the contract.
    h5_path = (REF_ROOT / "zenodo_v1.0.5" / "CMR2_0.346_CMC_0.426_S+Si_Edmund"
               / "DataSi%wt0.01_R0500.0.h5")
    with h5py.File(h5_path, "r") as f:
        keys = set(f.keys())
    for expected in ("r", "rho", "T", "P", "g", "Tad", "chi_li", "misc"):
        assert any(k == expected or k.startswith(expected + "/") for k in keys), (
            f"expected h5 key '{expected}' not found among {sorted(keys)}"
        )


def test_scipy_interp2d_still_callable():
    """src/coreEos.py does `from scipy.interpolate import interp2d` at
    MODULE level (used by meltingDataFromFile, which libCore.py
    instantiates at ITS OWN import time) -- interp2d is deprecated
    upstream and scheduled for removal from scipy. When scipy removes
    it, EVERY src/ module import breaks (coreEos -> libCore -> almost
    everything), not just the one call site that uses it. This is a
    canary, not a fix: it fails specifically and first, rather than
    letting every other test fail with a confusing downstream
    ImportError. Since scipy 1.14 the name still IMPORTS but raises
    NotImplementedError when CALLED, so this canary calls it. Fix
    tracked on PATHWAY_FORWARD.md item 14; testsys/requirements.txt pins
    scipy==1.8.0 until then.
    """
    import numpy as np
    from scipy.interpolate import interp2d
    f = interp2d([0.0, 1.0], [0.0, 1.0], np.array([[0.0, 1.0], [1.0, 2.0]]))
    assert float(f(0.5, 0.5)[0]) == 1.0
