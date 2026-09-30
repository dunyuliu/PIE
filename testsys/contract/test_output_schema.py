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

SRC = pathlib.Path(__file__).resolve().parents[2] / "src"

pytestmark = pytest.mark.contract

REF_ROOT = pathlib.Path(__file__).resolve().parent.parent / "reference"


def test_presentday_columns_matches_written_csv_header(sys_argv_p):
    globalvar = import_src("globalvar")
    csv_path = (REF_ROOT / "zenodo_v1.0.5" / "CMR2_0.346_CMC_0.426_S+Si_Edmund"
                / "pMetaData_0.01.csv")
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
    # v1.3.0 appended start/newton_iters/resid_norm; the published v1.0.5
    # files carry the first 19 columns, in the same order.
    assert header == globalvar.presentday_columns[:len(header)]
    assert len(header) == 19


def test_v1_3_0_columns_are_appended_not_inserted(sys_argv_p):
    globalvar = import_src("globalvar")
    assert globalvar.presentday_columns[-3:] == ["start", "newton_iters", "resid_norm"]
    assert globalvar.presentday_columns[:19] == [
        "chi_Si_icb", "rhom", "mass", "moi", "cmc", "Picb", "Tcmb", "isnow", "isnowcmb",
        "chi_li_in", "chi_S_bulk", "Pcmb", "chi_li_eut_icb", "chi_li_eut_cmb", "ricb", "rcmb",
        "core_mass", "chi_li_icb", "error_code"]


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
    assert header == globalvar.presentday_columns[:len(header)]


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


def test_src_does_not_use_removed_scipy_interp2d():
    """scipy.interpolate.interp2d raises NotImplementedError from scipy 1.14.
    src/coreEos.py was ported to RectBivariateSpline in v1.1.1 (bit-for-bit,
    testsys/unit/test_melting_interp_port.py); keep it from coming back."""
    import re
    offenders = [str(f.relative_to(SRC.parent)) for f in SRC.glob("*.py")
                 if re.search(r"^[^#\n]*\binterp2d\b", f.read_text(), re.M)]
    assert not offenders, f"interp2d used in: {offenders}"
