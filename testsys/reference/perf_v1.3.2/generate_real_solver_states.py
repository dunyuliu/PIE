import sys, os
sys.path[:] = [p for p in sys.path if "/.local/" not in p]
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src")  # repo src/
os.chdir(SRC)
sys.path.insert(0, SRC)
sys.argv[:] = ["main.py", "p", "0.346", "0.424", "S", "Edmund"]
import numpy as np
import globalvar as gv
import planet_input
import libCore as lcore
import shootp as lc
from scipy.sparse import csc_matrix

captured_A = []
captured_rhs = []
orig_getpotvsr = lcore.getpotvsr
def spy_getpotvsr(nr, bigGnd, rnd, rhond, gnd):
    # Rebuild A, rhs exactly like getpotvsr does, to snapshot them (read-only
    # capture; does not change control flow -- just records real inputs).
    l = 2
    ndim = 2*nr-1
    row = np.zeros(3191, dtype=int); col = np.zeros(3191, dtype=int); s = np.zeros(3191)
    kk=0; k=0
    row[kk]=k; col[kk]=k; s[kk]=rnd[0]**(2*l+1)
    kk+=1; row[kk]=k; col[kk]=k+1; s[kk]=-1
    kk+=1; row[kk]=k; col[kk]=k+2; s[kk]=-rnd[0]**(2*l+1)
    alpha = 4.0*np.pi*bigGnd*rnd[0]*(rhond[0]-rhond[1])/gnd[0]
    kk+=1; row[kk]=k+1; col[kk]=k; s[kk]=(l-alpha)*rnd[0]**(2*l+1)
    kk+=1; row[kk]=k+1; col[kk]=k+1; s[kk]=l+1
    kk+=1; row[kk]=k+1; col[kk]=k+2; s[kk]=-l*rnd[0]**(2*l+1)
    for j in range(1,nr-1):
        k=2*(j+1)-2
        kk+=1; row[kk]=k; col[kk]=k; s[kk]=rnd[j]**(2*l+1)
        kk+=1; row[kk]=k; col[kk]=k-1; s[kk]=1
        kk+=1; row[kk]=k; col[kk]=k+1; s[kk]=-1
        kk+=1; row[kk]=k; col[kk]=k+2; s[kk]=-rnd[j]**(2*l+1)
        alpha = 4.0*np.pi*bigGnd*rnd[j]*(rhond[j]-rhond[j+1])/gnd[j]
        kk+=1; row[kk]=k+1; col[kk]=k-1; s[kk]=-(l+1+alpha)
        kk+=1; row[kk]=k+1; col[kk]=k; s[kk]=(l-alpha)*rnd[j]**(2*l+1)
        kk+=1; row[kk]=k+1; col[kk]=k+1; s[kk]=l+1
        kk+=1; row[kk]=k+1; col[kk]=k+2; s[kk]=-l*rnd[j]**(2*l+1)
    k=2*nr-2
    kk+=1; row[kk]=k; col[kk]=k; s[kk]=rnd[nr-1]**l
    A = np.zeros([ndim, ndim]); A[row,col]=s
    rhs = np.zeros(2*nr-1); rhs[2*nr-2]=1.0
    A = csc_matrix(A)
    if len(captured_A) < 3:
        captured_A.append(A.copy())  # keep sparse (csc) -- dense would be ~5MB each
        captured_rhs.append(rhs.copy())
    return orig_getpotvsr(nr, bigGnd, rnd, rhond, gnd)
lcore.getpotvsr = spy_getpotvsr
lc.getpotvsr = spy_getpotvsr  # shootp imported it via `from libCore import *`

captured_J = []
captured_f = []
orig_Jfunc = lc.J_mercmodel
def spy_J(v, args):
    J, f = orig_Jfunc(v, args)
    if len(captured_J) < 5:
        captured_J.append(np.array(J, dtype=float).copy())
        captured_f.append(np.array(f, dtype=float).copy())
    return J, f

lc.J_mercmodel = spy_J

param = planet_input.planet("p", 0.346, "S", "Edmund")
scale = param["scale"]
ricb_nd = 500_010.0 / scale["a"]
v = lc.mynewtonSys('J_mercmodel', param["v0"],
                    [ricb_nd, param["rhocr"], param["rh"], param, scale],
                    xtol=gv.xtol, ftol=gv.ftol, maxit=gv.maxit, verbose=False)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_solver_states.npz")
save_kwargs = {}
for i, (Ai, rhsi) in enumerate(zip(captured_A, captured_rhs)):
    save_kwargs[f"A{i}_data"] = Ai.data
    save_kwargs[f"A{i}_indices"] = Ai.indices
    save_kwargs[f"A{i}_indptr"] = Ai.indptr
    save_kwargs[f"A{i}_shape"] = np.array(Ai.shape)
    save_kwargs[f"rhs{i}"] = rhsi
for i, (Ji, fi) in enumerate(zip(captured_J, captured_f)):
    save_kwargs[f"J{i}"] = Ji
    save_kwargs[f"f{i}"] = fi
save_kwargs["n_A"] = np.array(len(captured_A))
save_kwargs["n_J"] = np.array(len(captured_J))
np.savez(out, **save_kwargs)
print("captured A count:", len(captured_A), "J count:", len(captured_J))
print("saved to", out)
