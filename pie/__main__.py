"""`python -m pie` entry point -- same semantics as the `pie` console
script (see `pie/cli.py`); kept as a one-line delegation so there is a
single implementation of the run_module trick.
"""
from .cli import main

if __name__ == "__main__":
    main()
