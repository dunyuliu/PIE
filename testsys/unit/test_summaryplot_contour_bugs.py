"""Regression tests for util/plot/summaryPlot.py (PATHWAY_FORWARD.md item 24,
diagnosed by lars-eriksson, fixed here): three bugs that raised/would raise
NameError the moment the relevant code path ran, because this file is a
flat top-level script (no functions), so every line executes unconditionally
(or on whichever branch contourcond takes) the moment it is imported/run:

  (a) `contourplot_file` was referenced (lines ~116/141/187) but never
      defined -- only a commented-out formula existed in the old
      globalvar.py:52 (now pie/globalvar.py). This is on the file's
      UNCONDITIONAL path (reached regardless of `contourcond`), so every
      real invocation hit it. Fixed by uncommenting+fixing the formula in
      pie/globalvar.py and importing it into summaryPlot.py.
  (b) `contour_scale` was referenced (line ~101, the `else` branch taken
      when `contourcond` is neither 'isnow' nor 'isnowcmb') but never
      assigned -- only a commented-out `#contour_scale = int(np.log10(sample))`
      existed. Fixed by uncommenting that line.
  (c) `contourdond` (line ~96) is a typo for `contourcond` -- confirmed by
      comparing against the file's OWN later, correctly-spelled check at
      line ~131 (`contourcond == 'isnow' or contourcond == 'isnowcmb'`).
      Currently unreachable in production (globalvar.py hard-codes
      contourcond='isnow', so the `or` short-circuits before evaluating
      `contourdond`), but a real bug/landmine, not a deliberate name.

This test runs the actual script as a subprocess (mutation-verified: with
each fix reverted individually, the script crashes with exactly the
NameError the bug predicts; see PR description). It supplies a minimal
synthetic csv under the directory pie/globalvar.py computes from a fixed
argv, so no real physics solve is needed.
"""
import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "util" / "plot" / "summaryPlot.py"

ARGV_TAIL = ["plot", "0.346", "0.424", "S", "Edmund"]

# presentday_columns, pie/globalvar.py -- kept in sync by hand (same risk
# accepted elsewhere in this suite, e.g. test_robust_runner.py's literal
# argv-shape assertions).
COLUMNS = [
    "chi_Si_icb", "rhom", "mass", "moi", "cmc", "Picb", "Tcmb", "isnow",
    "isnowcmb", "chi_li_in", "chi_S_bulk", "Pcmb", "chi_li_eut_icb",
    "chi_li_eut_cmb", "ricb", "rcmb", "core_mass", "chi_li_icb",
    "error_code", "start", "newton_iters", "resid_norm",
]

ROW_SNOW = [0.0, 3300, 1.0, 0.3, 0.4, 1e9, 2000, 2, 1, 0.05, 0.05, 5e9,
            0.15, 0.15, 1_000_000, 2_000_000, 5.8e22, 0.05, 0, 0, 5, 1e-7]
ROW_NO_SNOW = [0.0, 3300, 1.0, 0.3, 0.4, 1e9, 1900, 0, 0, 0.03, 0.03, 5e9,
               0.15, 0.15, 900_000, 2_000_000, 5.8e22, 0.03, 0, 0, 5, 1e-7]


def _write_fixture_csv(tmp_path):
    """Create the results/<model dir>/ csv summaryPlot.py reads, computed
    the same way pie/globalvar.py does from ARGV_TAIL, under tmp_path."""
    env = dict(os.environ)
    env["MPLBACKEND"] = "Agg"
    # Query globalvar's own model_path formula for this argv, in a fresh
    # subprocess (importing pie.globalvar in-process would leave argv/
    # module-cache contamination for other tests in this file's session).
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.argv=['x']+%r\n"
         "import pie.globalvar as gv\n"
         # board item 28f: parsing is an explicit call now, not an
         # import-time side effect -- same call pie/main.py (and this
         # script's own fix, util/plot/summaryPlot.py) make.
         "gv.parse_argv(sys.argv)\n"
         "print(gv.csvfiles_path)" % ARGV_TAIL],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )
    assert out.returncode == 0, out.stderr
    csvfiles_path = out.stdout.strip().splitlines()[-1]
    data_dir = tmp_path / csvfiles_path
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / "data1.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerow(ROW_SNOW)
        w.writerow(ROW_NO_SNOW)
    return data_dir


def _run_summary_plot(tmp_path):
    env = dict(os.environ)
    env["MPLBACKEND"] = "Agg"
    return subprocess.run(
        [sys.executable, str(SCRIPT)] + ARGV_TAIL,
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
    )


def test_summary_plot_runs_without_nameerror(tmp_path):
    """Bug (a): contourplot_file is used on summaryPlot.py's unconditional
    path (reached for ANY contourcond value, including the production
    default 'isnow') -- every real invocation hit `NameError:
    contourplot_file`. Also exercises bug (b)'s sibling fix path being a
    no-op here (contourcond=='isnow' takes the `if` branch, never reaching
    contour_scale) -- see the dedicated test below for that branch.
    """
    _write_fixture_csv(tmp_path)
    result = _run_summary_plot(tmp_path)
    assert result.returncode == 0, (
        f"summaryPlot.py failed (stdout+stderr below):\n{result.stdout}\n{result.stderr}")
    assert "NameError" not in result.stderr
    # contourplot_file must actually have produced output under the model
    # directory it's derived from, not an empty/undefined name.
    produced = list(tmp_path.rglob("*.tiff")) + list(tmp_path.rglob("*.png"))
    assert produced, "expected at least one figure written under tmp_path"


def test_non_isnow_contourcond_reaches_contour_scale_without_nameerror(tmp_path, monkeypatch):
    """Bugs (b) and (c): force contourcond to something other than
    'isnow'/'isnowcmb' so the script's `else` branch (line ~101,
    `contour_scale`) and the `if` condition itself (line ~96,
    `contourdond`) are actually evaluated. Patches pie/globalvar.py's
    contourcond via PIE_TEST_CONTOURCOND, read at the top of a tiny shim
    pie/globalvar.py does NOT otherwise support -- so this patches the
    subprocess's pie.globalvar module directly via -c, matching
    production's actual import path (`from pie.globalvar import
    contourcond`), rather than editing the installed file.
    """
    data_dir = _write_fixture_csv(tmp_path)

    env = dict(os.environ)
    env["MPLBACKEND"] = "Agg"
    # Monkeypatch contourcond to a non-isnow/isnowcmb field by importing
    # globalvar first, overwriting its attribute, then runpy-executing the
    # script under the patched module -- this is exactly what would happen
    # if contourcond were ever configured to something else (it is a
    # plain module attribute, not argv-driven, so this is the only way to
    # reach this branch without editing pie/globalvar.py itself).
    driver = (
        "import sys, runpy\n"
        f"sys.argv = ['x'] + {ARGV_TAIL!r}\n"
        "import pie.globalvar as gv\n"
        # board item 28f: parsing is an explicit call now, not an
        # import-time side effect.
        "gv.parse_argv(sys.argv)\n"
        "gv.contourcond = 'chi_li_icb'\n"
        f"runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", driver],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        f"summaryPlot.py (contourcond='chi_li_icb') failed:\n{result.stdout}\n{result.stderr}")
    assert "NameError" not in result.stderr
