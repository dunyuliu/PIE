# PIE: Planetary Interior Evolution

PIE inverts Mercury's present-day interior structure -- an iron core
carrying sulfur and/or silicon as light elements -- against geodetic
(CMR2, CMC) constraints, and is developing a companion model of how that
interior evolves over time. All code is serial Python, packaged as the
installable `pie` package.

Full documentation -- installing, running a case or a sweep, what PIE
physically models, parameters, output files, how results are checked, and
what each error code means -- is at **https://dunyuliu.github.io/PIE/**.

## Quickstart

Requires Python 3.12 with the exact pins in `requirements.txt` -- the one
supported environment (unpinned/"latest" packages are untested here).
Install with [`uv`](https://docs.astral.sh/uv/) (absolute path shown
because `uv` is not on default `PATH` on most hosts):

```
git clone https://github.com/dunyuliu/PIE.git
cd PIE
~/.local/bin/uv venv --python 3.12 .venv
~/.local/bin/uv pip install --python .venv/bin/python3.12 -e .
```

`pie` is an installed package: run it as the `pie` console script, or via
`python -m pie`, from anywhere. Outputs are written to `./results/`,
relative to whatever directory the command runs in:

```
mkdir -p results
pie p 0.346 0.424 S Edmund
```

This solves a single present-day case at the Margot et al. CMR2/CMC fit,
with sulfur as the only light element, writing `pMetaData_0.00.csv`,
`solverLog_0.00.jsonl`, and one `Data*_R<ricb>.h5` profile per converged
radius under `results/CMR2_..._CMC_..._S_Edmund/`. See
[Getting Started](https://dunyuliu.github.io/PIE/getting-started/) and
[Running a Case](https://dunyuliu.github.io/PIE/running-a-case/) for
composition sweeps, Monte Carlo ensembles, and the resumable
large-ensemble runner.

## Citation

If you use PIE, please cite:

Dunnigan, A. H., Liu, D., Steinbrügge, G. B., Rivoldini, A., Dumberry, M., Cao, H., & Soderlund, K. M. (2026). Interior models of Mercury and conditions for iron snow formation in a Fe-S-Si core. *Journal of Geophysical Research: Planets*, 131(4), e2025JE009368. https://doi.org/10.1029/2025JE009368

See [Citing](https://dunyuliu.github.io/PIE/citing/) for archived code/data
releases and machine-readable citation metadata (`CITATION.cff`).

## License

GNU General Public License v3.0 -- see [`LICENSE`](LICENSE).
