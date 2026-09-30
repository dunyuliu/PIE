# Changelog

Version source of truth: git tags (`vX.Y.Z`) and GitHub releases; `CITATION.cff` `version:` is bumped in each release PR. This file holds the per-release change list (moved from `src/VERSION` in v1.1.0; history unchanged below). Pre-v1.0.5 development notes: `update_log` (frozen).

* v1.2.0; 20260930; failures are recorded instead of silently dropped. Converged outputs unchanged (all published-parity tests identical); output additions only.
    1. No more sys.exit() or uncaught crashes in the present-day solve: mynewtonSys and shoot_mercmodel raise SolverError; driverp.py records it per radius and stops that sweep at the same point as before (bugs B1, B2).
    2. error_code column now meaningful (schema unchanged): 0 converged, 1 Newton maxit, 2 singular Jacobian, 3 non-finite shoot (NaN, SuperLU singular, getk2 index), 4 chi outside admissible range, 5 ricb >= rcmb, 6 Si above liquidus max (by design). Previously always 0. Restored the discarded err flag and the (chi_li<0).any() check (B3).
    3. New per-run structured solver log solverLog_<chi_Si>.jsonl next to the pMetaData csv: Newton iterations and failure context (item 15).
    4. Dependencies: root requirements.txt with exact pins, contract test keeping it equal to testsys/requirements.txt; rule 3b (exact pins).
    5. testsys: truth anchors (homogeneous sphere, S+Si limits, Margot fit, liquidus table) and v1.0.3 regression history; placeholder for Steinbruegge et al. 2020 values.
    6. docs: README launcher filename fixed; Steinbruegge code assessed as an independent anchor (docs/notes/steinbruegge_anchor_2026-09-30.md).
* v1.1.1; 20260929; scipy compatibility patch. Converged outputs unchanged.
    1. Port src/coreEos.py meltingDataFromFile from scipy interp2d (removed in scipy 1.14) to RectBivariateSpline(kx=3, ky=3, s=0): same FITPACK fit and evaluation, bit-for-bit on the pinned environment (testsys/unit/test_melting_interp_port.py).
    2. CI: new fast-latest job on Python 3.12 with current numpy/scipy (pins stripped); pinned job unchanged.
    3. Contract test: src/ must not use interp2d (replaces the interp2d canary).
* v1.1.0; 20260929; first tested baseline. src/ physics code byte-identical to v1.0.5 (the code archived for Dunnigan et al. 2026, JGR Planets, doi:10.1029/2025JE009368).
    1. Add testsys/: unit, contract, integration, e2e tiers; parity vs published Zenodo v1.0.5 output (10.5281/zenodo.16459292) for S, Si, S+Si; full radial-profile guards; runner testsys/run.py.
    2. Add CI (.github/workflows/test.yml): fast tiers on push/PR, e2e weekly and on demand.
    3. Add CITATION.cff and README citation; PROJECT_RULES.md, PATHWAY_FORWARD.md, CLAUDE.md.
    4. Move src/VERSION to CHANGELOG.md (git tags = version source of truth); pin CI requirements (scipy 1.8.0: interp2d removed in 1.14).
    5. Add docs/notes/failure_analysis_2026-09-28.md and docs/audits/: solver-failure analysis and audits (fixes scheduled for v1.1.1).
* v1.0.5; 20250708; publication release (all changes since v1.0.4 tag, 20230214)
    1. Add read_plot_datah5.py, which will read and plot *data.h5 results. For Hao's calculation of BV frequency. (20230403)
    2. Use eos.liquidNonIdaFeS; take alpha and C_p from eos function. (20230607)
    3. Add Monte Carlo wrapper for CMR2 (monteCarlo.run.py). (20250122)
    4. Add S mass calculation in driverp and shootp. (20250225)
    5. Fix missing pi in get_mass_core; fix missing column head for chi_S_bulk. (20250303)
    6. Fix iron snow layer classification to include 3 for deep snow+layers. (20250707)
    7. Merge 1.0.4.dev into src; rename TACC LS6 launcher/slurm scripts; remove runAll.sh. (20250707)
* v1.0.4; 20230127; 
	1. explore CMR2 and CmC parameter space.
	2. Add scheduler.py to run models over the CMR2, CMC, liquidus equation,  light element, and Si%wt parameter space.
	3. Generate as many models as possible and discard models negative light element weight ones at the end. 
	
* v1.0.3 committed on 20221026 and zipped under D:\3.Krista_Soderlund\GitHub\Committed_Mercury_present_evolution\Mercury_present_evolution_v1.0.3_committed_20221026