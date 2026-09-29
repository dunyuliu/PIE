import os
S = os.path.dirname(os.path.abspath(__file__)) + "/src_instr"
s = open(S + "/shootp.py").read()
old_newton = """      J,f = eval(Jfun)(x,varargin)   #   Returns Jacobian matrix and f vector
      if np.linalg.det(J) == 0:
        print('Zero Determinant of J. Exit ... ...')
        sys.exit()
      dx = np.dot(np.linalg.inv(J),f)
      x = x - dx
      if verbose:
          end = time.time()
          print(k,np.linalg.norm(f),np.linalg.norm(dx),end-start)
      if (np.linalg.norm(f) < feps) or (np.linalg.norm(dx) < xeps):
          return x

    print('Solution not found within tolerance after_',k,'_iterations\\n')
    print('Exiting the code')
    sys. exit()"""
new_newton = """      J,f = eval(Jfun)(x,varargin)   #   Returns Jacobian matrix and f vector
      detJ = np.linalg.det(J); condJ = np.linalg.cond(J)
      if detJ == 0:
        NEWTON_HIST.append(dict(k=k,nf=float(np.linalg.norm(f)),ndx=None,detJ=0.0,condJ=float(condJ),x=list(map(float,x)),f=list(map(float,f))))
        NEWTON_STATUS['end']='detJ0'
        return None
      dx = np.dot(np.linalg.inv(J),f)
      lam = 1.0
      if NEWTON_OPTS.get('linesearch'):
          nf0 = np.linalg.norm(f)
          for _ in range(6):
              xt = x - lam*dx
              try:
                  ft = shoot_mercmodel(xt,*varargin)[0]
                  if np.all(np.isfinite(ft)) and np.linalg.norm(ft) < nf0: break
              except Exception:
                  pass
              lam *= 0.5
      x = x - lam*dx
      NEWTON_HIST.append(dict(k=k,nf=float(np.linalg.norm(f)),ndx=float(np.linalg.norm(dx)),detJ=float(detJ),condJ=float(condJ),lam=lam,x=list(map(float,x)),f=list(map(float,f))))
      if verbose:
          end = time.time()
          print(k,np.linalg.norm(f),np.linalg.norm(dx),end-start)
      if (np.linalg.norm(f) < feps) or (np.linalg.norm(dx) < xeps):
          NEWTON_STATUS['end']='converged'
          return x

    NEWTON_STATUS['end']='maxit'
    return None"""
i0 = s.index("      J,f = eval(Jfun)(x,varargin)")
i1 = s.index("    sys. exit()", i0) + len("    sys. exit()")
s = s[:i0] + new_newton + s[i1:]
s = s.replace("def mynewtonSys(Jfun,x0,varargin,",
              "NEWTON_HIST=[]\nNEWTON_STATUS={}\nNEWTON_OPTS={}\nK2_GUARD=True\nK2_TRACE={}\n\nclass K2GridError(Exception):\n    pass\n\ndef mynewtonSys(Jfun,x0,varargin,")
assert "    eps=1.e-6\n    for j in range(n):" in s
s = s.replace("    eps=1.e-6\n    for j in range(n):", "    eps=NEWTON_OPTS.get('eps',1.e-6)\n    for j in range(n):")
old = "    nrs=int(round(nr*(rs/rf)))\n    nrf=nr-nrs\n"
assert old in s
s = s.replace(old, old + """    if K2_GUARD and (nrs<0 or nrs>=nr):
        raise K2GridError('getk2: nrs=%d out of range (ricb=%g rcmb=%g nd)'%(nrs,rs,rf))
    if NEWTON_OPTS.get('k2_min_nrs') and nrs<NEWTON_OPTS['k2_min_nrs']:
        nrs=NEWTON_OPTS['k2_min_nrs']; nrf=nr-nrs
""")
old = "    r = np.empty(nr)\n    rho = np.empty(nr)\n    g = np.empty(nr)\n"
assert old in s
s = s.replace(old, """    fill = NEWTON_OPTS.get('k2_fill', None)   # None = np.empty (as shipped); else np.full(fill)
    if fill is None:
        r = np.empty(nr); rho = np.empty(nr); g = np.empty(nr)
    else:
        r = np.full(nr,float(fill)); rho = np.full(nr,float(fill)); g = np.full(nr,float(fill))
    K2_TRACE.clear(); K2_TRACE.update(nrs=nrs, g_last_garbage=float(g[-1]), g0_garbage=float(g[0]))
""")
old = "    pot = getpotvsr(nr,bigGnd,r,rho,g)\n"
assert old in s
s = s.replace(old, "    K2_TRACE.update(g0=float(g[0]),g1=float(g[1]),rho0=float(rho[0]),r0=float(r[0]))\n" + old)
open(S + "/shootp.py", "w").write(s)

L = open(S + "/libCore.py").read()
old = "    A = csc_matrix(A)\n    #print(A)\n    b = inv(A)*rhs\n"
assert old in L
L = L.replace(old, """    POT_TRACE.clear()
    POT_TRACE['nonfinite_in_A']=int((~np.isfinite(A)).sum()); POT_TRACE['zero_rows']=int((np.abs(A).sum(1)==0).sum()); POT_TRACE['zero_cols']=int((np.abs(A).sum(0)==0).sum())
    POT_TRACE['A00']=float(A[0,0]); POT_TRACE['A10']=float(A[1,0])
    if POT_OPTS.get('cond'):
        try: POT_TRACE['condA']=float(np.linalg.cond(A))
        except Exception as e: POT_TRACE['condA']=repr(e)
    if POT_OPTS.get('dense'):
        b = np.linalg.solve(A,rhs)
    else:
        Ad = A
        A = csc_matrix(A)
        try:
            b = inv(A)*rhs
        except RuntimeError as e:
            POT_TRACE['singular']=True
            try: POT_TRACE['condA']=float(np.linalg.cond(Ad))
            except Exception: pass
            if POT_OPTS.get('dump'): np.save(POT_OPTS['dump'],Ad)
            raise
""")
L = L.replace("def getpotvsr(nr,bigGnd,rnd,rhond,gnd):", "POT_TRACE={}\nPOT_OPTS={}\n\ndef getpotvsr(nr,bigGnd,rnd,rhond,gnd):")
open(S + "/libCore.py", "w").write(L)
print("patched OK")
