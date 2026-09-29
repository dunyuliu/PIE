# Audit Report — PIE v1.0.5 — 2026-09-29

## Verification Results

| ID | Verdict | File:Line | Proof | Effect Verdict |
|---|---|---|---|---|
| B1 | TRUE | shootp.py:298-300, 311 | sys.exit() in mynewtonSys on det(J)==0 and maxit; driverp.py:38 `if v is None: break` unreachable since function never returns None | Process terminates on singular J; remaining radii loop lost silently |
| B2 | TRUE | driverp.py:30 commented out; libCore.py:266 | try/except block commented (line 30 driverp.py); inv(A) at libCore:266 can raise RuntimeError; getpotvsr calls inv on sparse matrix | Uncaught SuperLU/IndexError crashes process |
| B3 | TRUE | shootp.py:131, 251; driverp.py:111 | shootp.py:131 sets `err0=False` hardcoded; driverp.py:111 uses `chi_li.any()<0` (compares bool to int, always False) | error_code never set to 1 from negative chi; error propagation dead |
| B4 | TRUE | shootp.py:301-302; libCore.py:146 | Newton step `x = x - dx` undamped (no line search); libCore:146 clamps `chi_li = min(sol.x[0], chi_li_eut)` from above only | chi_li_icb overshoots past eutectic or below 0; zero Jacobian column or NaN propagation |
| B5 | TRUE | shootp.py:421, 456-460 | nrs=int(round(400*10m/3100km))=0; loop `for k in range(0,nrf)` uses `r[k+0-1]` and `g[k+0-1]` = `r[-1]`, `g[-1]` | Reads uninitialized/CMB-end array elements; wrong g values propagate |
| B6 | TRUE | planet_input.py:119 | Function takes `code_mode` (line 6 arg), but line 119 references undefined `mod_type` | planet('e', ...) raises NameError; evolution mode unreachable |
| B7 | TRUE | shootp.py:298 | `if np.linalg.det(J) == 0:` exact float comparison; determinant 1e-16 returns False | Near-singular J (det~1e-16) not caught; produces huge/NaN step |
| L1 | TRUE | libCore.py:285 | First term: `rho[0]*r[0]**3/r[-1]**3` has dimension [kg/m³], rest have [kg] | Accumulates inconsistent units; r[0]≈0 masks error but equation incorrect |
| L2 | TRUE | libCore.py:67 | Function parameter `chi_Si_constant` ignored; uses module-global `chi_Si_icb` instead | Callers passing parameter for 'S+Si' mode ignored; silently uses global value |
| L3 | TRUE | shootp.py:202, 214; globalvar.py:67-68 | Classification abs(T1-Tm)<1e-8 vs solver xtol/ftol=1e-6; tolerance 100x tighter | isnow flips between 1 and 2 across cold/warm starts; non-deterministic classification |

## Adjacent Issues Found

### A1: getk2 loop bounds unsafe
- **Location**: shootp.py:445, 450-460
- **Bug**: Loop indices `k+nrs` (line 445-448, 450-460) assume nrs > 0; when nrs=0, both loops overlap and re-initialize same array cells
- **Impact**: Gravity field g built incorrectly when inner core tiny
- **Reproducer**: ricb=10m, nrs=0 → lines 450-460 overwrite g[0:nrf] computed by 445-448

### A2: SuperLU dense matrix construction defeats sparsity
- **Location**: libCore.py:256-266
- **Bug**: Builds sparse matrix A at line 264, then calls `inv(A)*rhs` at line 266; scipy sparse inv is only stable/efficient if A remains sparse
- **Impact**: Dense inversion on large matrices; if A singular, RuntimeError unhanded (B2)
- **Note**: Could use sparse solve (spsolve) instead

