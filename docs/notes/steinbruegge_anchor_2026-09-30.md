# Steinbruegge 2020 code as PIE truth anchor — 2026-09-29

## Verdict
Works for Fe-S (all outputs, all ricb tested, 1e-9 relative) and for Fe-Si at ricb→0; Fe-Si with a finite inner core disagrees up to 1 % for a fully attributed reason (inner-core EOS); core_mass/chi_S_bulk expose a 0.3 % quadrature bias in PIE that the anchor catches.

## Provenance
- Anchor code: github.com/gregorsteinbruegge/MercuryInterior @ `8dc64663c574bc9dc1b3ecbb74252fbb3b1a2383` (2021-08-09, MIT). Clone: `scratchpad/MercuryInterior` (unmodified; the FeSi-inner-core variant is monkey-patched in `run_stb.py`, not edited in the clone).
- Ran unmodified with `PYTHONNOUSERSITE=1 MPLBACKEND=Agg /usr/bin/python3` (3.10.12, scipy 1.8.0, numpy 1.21.5). No undeclared deps for libcore/coreEos (`visualization.py` needs matplotlib — not imported). No removed-scipy-API problems (it never used interp2d).
- PIE: ~/PIE @ 70506bd, imported read-only from `src/`; `TmFeSmelt.dat` copied to scratch cwd. Nothing under PIE written.
- Inputs matched to run_models.py: CMR2=0.333, CmC=0.148/0.333, rm=2439360 m, GM=22031.86e9, c22=0.804151e-5, rhocr=2974, hcr=26 km, v0=[0.8,1,0.8,0.7,0.05], liquidus=Steinbruegge; ricb = 10 m then 50..1000 km step 50 km (PIE's dr=50 km), continuation in ricb as both drivers do.
- Newton: STB xtol=ftol=1e-5 maxit=6; PIE 1e-6/12. Final |f| both ≤3e-9.
- Host: shared 64-core box, load ~36–47 during runs (contended; no timing claims). nice -n 19, 5 processes.
- Scripts/results: `run_stb.py`, `run_pie.py`, `compare.py`, `out/*.npy`, `out/compare.txt`, `out/compare2.txt`.

## Physics diff (Steinbruegge coreEos.py/libcore.py vs PIE coreEos.py/libCore.py/shootp.py/solver.py)
Identical (verbatim or algebraically): Vinet compression + AndersonGrueneisen EOS class (pMax=200, 10001 nodes, dT=1), Gibbs fcc/liquid Fe, Margules Vex(FeS), Vex(FeSi), wt→mol conversion, all EOS constants (fccFe, liquidFe, liquidFeS, liquidFeSi), solidFccFeSi (rho·xx, gamma/xx²), Anzellini Fe melting + DR2015 FeS eutectic (Te0/b1/Pe0 table, chiSeut=0.11+0.187exp(-0.065P)), Si liquidus Tm=(x/0.15)Tm15+(1-x/0.15)TmFe (PIE writes it as TmFe−(TmFe−Tm15)x/0.15), snow chi update (root of Tm=T, clamp to eutectic), hydrostatic/g/adiabat ODEs, stratified layer rst=(ricb+rcmb)/2 with 0.95 factor, RK4 51 nodes, LSODA rtol 5e-5 in inner core, r0=1e-4 m, getPgcmb_crust, cubic polyfit MoI, (1+xi) factor on Cm/C (present in BOTH; not a PIE change), getk2/getpotvsr (PIE adds SuperLU/NaN guards only), simpsonDat, chiSin=3/rcmb³∫chi r²dr, isnowcmb test, Newton (PIE adds error codes/logging only).
Differences:
1. Inner-core EOS (S i only): STB uses pure fcc-Fe in the inner-core ODE and r0 density but FeSi density for the MoI polynomial (internally inconsistent). PIE uses `eos.eosInnerCore` = solidFccFeSi(chi_Si) everywhere (comment dated 20220302; predates git history, first appears in aa86375 2022-05-20). For li_el='S' identical (chi_Si=0).
2. Liquid EOS: PIE always calls 3-component `liquidNonIdalFeSSi`/`margules3Solution`/`VexFeFeSFeSi` (transferred 20220331, `a49c938` 2023-06-07 for read_plot only). Reduces exactly to STB's 2-component forms when xS=0 or xSi=0 (verified algebraically and numerically to 1e-10).
3. liquidFeS deltaT: STB 5.92217679116356, PIE 5.9221767911635 (1e-15 relative; noise).
4. Snow classification (`2a9d576` 2025-07-07): deep-snow test at fluid node i=1 (PIE) vs i=0 (STB; node 0 always satisfies T=Tm, so STB's isnow=2 test is tautological once isnow=1). Observed: ricb=850 km Fe-S → STB 2, PIE 1; ≥900 km both 2.
5. Liquidus abstraction: PIE `param['liquidus']` = `TmFeSSi_Steinbruegge2020` (S+Si additive depression) or `TmFeSSi` (Edmund, uses TmFeSmelt.dat). Steinbruegge branch equals STB's getmelt_anzellini for single elements. Edmund/S+Si have no STB counterpart.
6. PIE-only outputs: core_mass (`get_mass_core`, pi fix `bb37b0a` 2025-03-03), chi_S_bulk (mass-weighted), err/error_code, Tad/h5 dumps. STB has no mass output.
7. Newton tolerances/maxit (see above); PIE mynewtonSys raises SolverError instead of returning None.

## Results (fresh, this session)
Fe-S, 21 ricb (10 m–1000 km): |Δrcmb| ≤ 4.8e-4 m, rel Δrhom ≤ 6.8e-10, rel ΔPcmb ≤ 2.2e-8, rel ΔPicb ≤ 4.7e-10, |ΔTcmb| ≤ 1.3e-5 K, Δchi_icb, Δchi_in ≤ 1.8e-9, fluid-core node-wise profiles rho/P/T/g ≤ 7e-10, chi ≤ 1e-8. isnow identical except 850 km (diff 4). → identical physics; residual = Newton tolerance.
Fe-Si as published vs PIE: grows with ricb: at 500 km Δrcmb=−528 m, ΔTcmb=+1.85 K, Δchi_icb=−1.5e-3; at 1000 km Δrcmb=−7.6 km, ΔTcmb=+30 K, Δchi_icb=−0.022 (STB 0.0615 vs PIE 0.0396), profiles up to 2 %. At ricb=10 m: Δrcmb=0.24 m, ΔTcmb=1e-3 K (inner core negligible).
Fe-Si STB with FeSi inner-core ODE (2-line patch) vs PIE, ≤800 km (STB Newton maxit=6 fails at 850 km): |Δrcmb| ≤ 0.38 m, |ΔTcmb| ≤ 1.4e-3 K, rel ≤ 1e-6, node-wise profiles ≤ 2e-6 (chi 2.5e-5). → diff 1 explains 100 % of Fe-Si disagreement. Fully attributed; not a bug in either sense, but STB's published Fe-Si is internally inconsistent and PIE's is the consistent one.
Core mass (independent check of PIE-only output): PIE get_mass_core is a right-endpoint shell sum; vs trapz(4πρr²) of the same profile it is low by 3.2e-3 (10 m), 2.3e-3 (500 km), 2.2e-3 (1000 km); midpoint-shell sum sits within 1e-4–5e-4 of trapz. chi_S_bulk = Simpson(chi ρ r²)/get_mass_core inherits +0.3 % bias (0.015555 vs 0.015507 at 10 m). Also first term `rho[0]*r[0]**3/r[-1]**3` is dimensionally inconsistent (non-dimensional, no 4π/3; numerically negligible at r0=1e-4 m). Candidate fix, not done here: midpoint rule or np.trapz.
Interp-based profile comparison across the sparse LSODA inner-core grid is a comparison artifact (up to 1e-3 when Newton solutions differ at 1e-7); compare at the 51 RK4 fluid nodes and at ICB/CMB instead.

## Recommended testsys anchors (hard, non-tautological)
Fetch: `git clone --depth 1 https://github.com/gregorsteinbruegge/MercuryInterior && git checkout 8dc64663c574bc9dc1b3ecbb74252fbb3b1a2383` in a CI step (or vendor the 4 files, 41 kB, MIT, under testsys/reference/steinbruegge2020_8dc6466/ with LICENSE and SHA). Import in a subprocess (module name `coreEos` clashes with PIE's). Never import its `visualization.py`.
Cases (CMR2=0.333, CmC=0.148/0.333, Steinbruegge liquidus, default crust; 3 ricb suffice: 10 m, 500 km, 1000 km; ~1 min each niced on a loaded box; or precompute once and commit STB outputs as a frozen JSON with SHA — still independent code, but then re-run only on demand):
- Fe-S: rcmb atol 0.01 m; rhom rtol 1e-8; Pcmb, Picb rtol 1e-7; Tcmb atol 1e-3 K; chi_li_icb, chi_li_in atol 1e-7; fluid-node rho/P/T/g rtol 1e-7, chi atol 1e-6; isnow equal for ricb∉{onset}; isnowcmb equal.
- Fe-Si at ricb=10 m only: rcmb atol 1 m, Tcmb atol 0.01 K, chi atol 1e-5 (the residual is the 10 m Fe vs FeSi inner core).
- Fe-Si with inner core: assert PIE == STB-with-FeSi-IC patch (tolerances as Fe-S ×10) **and** assert PIE − STB-published has the documented sign/size (e.g. rcmb lower by 400–650 m at 500 km) so the attribution stays on record; or skip with an explicit reason pointing to diff 1.
- core_mass: assert |PIE core_mass − 4π∫ρr²dr(trapz)|/M < 4e-3 today (documents the bias); tighten to 1e-4 after quadrature fix.
Cannot anchor (no STB counterpart): Edmund liquidus, S+Si, chi_S_bulk absolute value (only via my independent integral), err/error_code, evolution model (drivere/shoote), CMR2/CmC (inputs — tautological), Margot 0.346/0.424 published fit.
Snow onset radius: anchorable only with the classification difference (i=0→1) accounted for; assert isnow∈{1,2} agreement where STB=2, or compare (chi_cmb−chi_icb)>1e-10 (isnow≥1), which is identical.
