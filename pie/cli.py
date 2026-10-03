"""Console entry point for the `pie` command (board item 28e).

`pie.main` is a script, not a function (it runs its whole simulation at
module import time, same as the pre-28e `main.py` always has) -- so the
entry point re-executes it via `runpy.run_module` with `run_name="__main__"`
rather than importing it, which would only run once per process and which
would also leave `__name__` as `"pie.main"` instead of `"__main__"`.
`run_module` on a dotted name keeps `__package__` set to `"pie"`, so
`pie/main.py`'s own `from .globalvar import ...` style relative imports
still resolve. `sys.argv` is left untouched here -- it is the real
process argv, read by `pie/globalvar.py` at import time, same contract as
`python main.py p CMR2 CMC light_element liquidus_eq [chi_Si_icb]` before
this change (CLAUDE.md "Running").
"""
import runpy


def main():
    runpy.run_module("pie.main", run_name="__main__")


if __name__ == "__main__":
    main()
