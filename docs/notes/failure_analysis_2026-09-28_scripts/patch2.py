import os
HERE = os.path.dirname(os.path.abspath(__file__))
f = HERE + "/src_instr/shootp.py"
s = open(f).read()
if "LAST_FOUT" not in s:
    s = s.replace("    fout        = [P*ys[0,-1],T*yc[nc-1,2],isnow,isnowcmb,chi_li_in,gradTa,chisbulk]\n",
                  "    fout        = [P*ys[0,-1],T*yc[nc-1,2],isnow,isnowcmb,chi_li_in,gradTa,chisbulk]\n    LAST_FOUT[:] = fout\n")
    s = s.replace("NEWTON_HIST=[]\n", "NEWTON_HIST=[]\nLAST_FOUT=[]\nSHOOT_TRACE={}\n")
if "clamp_chi" not in s:
    i0 = s.index("      if detJ == 0:")
    tail = "      dx = np.dot(np.linalg.inv(J),f)\n"
    i1 = s.index(tail, i0) + len(tail)
    new = """      if detJ == 0 and not NEWTON_OPTS.get('clamp_chi'):
        NEWTON_HIST.append(dict(k=k,nf=float(np.linalg.norm(f)),ndx=None,detJ=0.0,condJ=float(condJ),x=list(map(float,x)),f=list(map(float,f)),J=J.tolist()))
        NEWTON_STATUS['end']='detJ0'
        return None
      if detJ == 0:
        dx = np.linalg.lstsq(J,f,rcond=None)[0]   # zero column (saturated variable): minimum-norm step
        NEWTON_STATUS['n_lstsq']=NEWTON_STATUS.get('n_lstsq',0)+1
      else:
        dx = np.dot(np.linalg.inv(J),f)
"""
    s = s[:i0] + new + s[i1:]
    step = "      x = x - lam*dx\n"
    i0 = s.index(step); i1 = i0 + len(step)
    new = """      x = x - lam*dx
      if NEWTON_OPTS.get('clamp_chi') and LAST_FOUT:
          li_el = varargin[3]['li_el']
          eut = 0.12 if li_el=='Si' else 0.11+0.187*np.exp(-0.065*LAST_FOUT[0]*1e-9)
          if x[4] > 0.999*eut:
              x[4] = 0.999*eut; NEWTON_STATUS['n_clamped']=NEWTON_STATUS.get('n_clamped',0)+1
          if x[4] < 0.0:
              x[4] = 1e-4; NEWTON_STATUS['n_clamped_neg']=NEWTON_STATUS.get('n_clamped_neg',0)+1
      NEWTON_STATUS['best_nf']=min(NEWTON_STATUS.get('best_nf',1e99),float(np.linalg.norm(f)))
"""
    s = s[:i0] + new + s[i1:]
if "SHOOT_TRACE.update" not in s:
    old = "    solf      = np.polyfit(rc,rhof,3)\n"
    assert old in s
    s = s.replace(old, old + "    SHOOT_TRACE.update(nan_ys=int((~np.isfinite(ys)).sum()), nan_yc=int((~np.isfinite(yc)).sum()), nan_rhof=int((~np.isfinite(rhof)).sum()), nan_rhos=int((~np.isfinite(rhos)).sum()), nan_solf=int((~np.isfinite(solf)).sum()), rcmb=float(rcmb), ricb=float(ricb), v=list(map(float,v)), Tmicb=float(Tmicb), Picb_nd=float(ys[0,-1]))\n")
    old = "    K2_TRACE.update(g0=float(g[0]),g1=float(g[1]),rho0=float(rho[0]),r0=float(r[0]))\n"
    assert old in s
    s = s.replace(old, old + "    K2_TRACE.update(n_nonfinite_rho=int((~np.isfinite(rho)).sum()), n_nonfinite_g=int((~np.isfinite(g)).sum()), n_nonfinite_r=int((~np.isfinite(r)).sum()), n_zero_g=int((g==0).sum()))\n")
open(f, "w").write(s)
p = open(HERE + "/probe.py").read()
p = p.replace('rec["k2_trace"] = dict(lc.K2_TRACE); rec["pot_trace"] = dict(libCore.POT_TRACE)\n',
              'rec["k2_trace"] = dict(lc.K2_TRACE); rec["pot_trace"] = dict(libCore.POT_TRACE); rec["shoot_trace"] = dict(lc.SHOOT_TRACE)\n')
p = p.replace('if k in ("eps", "linesearch", "k2_fill", "k2_min_nrs")', 'if k in ("eps", "linesearch", "k2_fill", "k2_min_nrs", "clamp_chi")')
p = p.replace('            rec["newton_end"] = lc.NEWTON_STATUS.get("end")\n', '            rec["newton_end"] = lc.NEWTON_STATUS.get("end"); rec["newton_status"] = dict(lc.NEWTON_STATUS)\n')
open(HERE + "/probe.py", "w").write(p)
print("patch2 ok")
