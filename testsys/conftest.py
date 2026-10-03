"""pytest requires a conftest.py to exist in testsys/ for two reasons that
have nothing to do with test logic: (1) it is how pytest's fixture
discovery finds session/autouse fixtures without every test file having to
import them explicitly, and (2) collecting it is what puts testsys/ itself
onto sys.path (default "prepend" import mode), which every test file's
`from pielib import ...` needs.

All actual logic -- the argv/import-time bootstrap, `PIE_WORKERS`
formula, `import_src()`-style loader, solved-model helpers, assertion
helpers -- lives in testsys/pielib.py (board item 28e/6: this file used to
hold all of that; there is no separate "testsys team", so moving it here
is in scope for the same packaging change that makes `pie` an installed
package instead of a sys.path-inserted `src/` directory). Importing those
names here re-exports them into this module's namespace, which is enough
for pytest to find the fixture-decorated ones (`sys_argv_p`, `cwd_src`,
`monkeypatch_session`) -- pytest looks for the fixture marker on whatever
object a conftest.py's namespace holds, not for where that object's code
was originally defined.
"""
from pielib import (  # noqa: F401
    sys_argv_p,
    cwd_src,
    monkeypatch_session,
)
