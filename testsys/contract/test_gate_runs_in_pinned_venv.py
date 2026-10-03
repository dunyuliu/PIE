"""Contract tier: this suite actually runs under the required pinned venv.

2026-10-02 (py312 migration, owner ruling): `testsys/conftest.py` used to
filter `.local` entries out of `sys.path` before importing `src/`, to work
around a stray `pip --user` matplotlib install shadowing the apt one on the
dev box's default `/usr/bin/python3`. PROJECT_RULES.md rule 3b/3c now
requires every run of this suite to use the pinned, uv-managed venv
instead of that (or any other) ambient interpreter, and that venv has no
user-site packages and no apt dist-packages on `sys.path` by construction
-- so the filter's premise (a real interpreter can have both installs on
its path at once) can no longer happen on the one interpreter this suite
is run under. The filter was removed rather than narrowed.

This test is what makes that removal safe: it gates the CLAIM that drove
the removal (the required interpreter excludes user-site packages and the
apt dist-packages directory by construction), so if the gate is ever run
under the wrong interpreter -- not the pinned venv -- this fails loudly
instead of silently reintroducing the two-matplotlib-installs conflict
with no filter left to catch it.
"""
import site
import sys

import pytest

pytestmark = pytest.mark.contract


def test_running_interpreter_has_user_site_disabled():
    """The pinned venv is built with no --system-site-packages and uv venvs
    disable user-site by default; a run under any other interpreter (the
    old system /usr/bin/python3, a bare `python3.12 -m venv`, etc.) is not
    guaranteed to have this property, which is exactly the case this test
    must catch."""
    assert site.ENABLE_USER_SITE is False, (
        "site.ENABLE_USER_SITE is True -- this suite is not running under "
        "the required pinned venv (PROJECT_RULES.md rule 3b/3c); the "
        "two-matplotlib-installs conflict testsys/conftest.py's sys.path "
        "filter used to guard against is reachable again."
    )


def test_no_apt_dist_packages_on_sys_path():
    """Belt-and-braces: even if user-site were somehow enabled, the apt
    dist-packages directory (the OTHER half of the historical matplotlib
    conflict) must not be on sys.path either."""
    assert not any("dist-packages" in p for p in sys.path), (
        "an apt-style 'dist-packages' directory is on sys.path -- this "
        "suite is not running under the required pinned venv "
        "(PROJECT_RULES.md rule 3b/3c)."
    )


def test_interpreter_is_python_3_12():
    assert sys.version_info[:2] == (3, 12), (
        f"running under Python {sys.version_info.major}."
        f"{sys.version_info.minor}, expected 3.12 (PROJECT_RULES.md rule 3b/3c "
        "pinned environment)."
    )
