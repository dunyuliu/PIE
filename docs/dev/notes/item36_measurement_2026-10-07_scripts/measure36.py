import glob, os, sys
import numpy as np
import pandas as pd

ROOTS = {
    "published_v1.0.5_full": os.path.expanduser("~/shared_dataset/zenodo.16459292/extracted/PIE/work.*/results/*"),
    "mc_wide_curated": "tests/reference/zenodo_v1.0.5/mc_wide/*/*",
    "self_v1.0.5": "tests/reference/self_v1.0.5/*",
}

MAX_SI_EDMUND = 0.12
MAX_SI_STEINBRUEGGE = 0.15

def light_el_from_dirname(name):
    if name.endswith("_S+Si_Edmund") or name.endswith("_S+Si_Steinbruegge"):
        return "S+Si"
    if name.endswith("_Si_Edmund") or name.endswith("_Si_Steinbruegge"):
        return "Si"
    if name.endswith("_S_Edmund") or name.endswith("_S_Steinbruegge"):
        return "S"
    return None

def liquidus_from_dirname(name):
    return "Steinbruegge" if name.endswith("Steinbruegge") else "Edmund"

results = {}
for label, pattern in ROOTS.items():
    case_dirs = sorted(d for d in glob.glob(pattern) if os.path.isdir(d))
    n_total_rows = 0
    n_converged = 0
    n_fail_finite = 0
    n_fail_rcmb = 0
    n_fail_chi = 0
    n_fail_any = 0
    n_files = 0
    n_no_error_code_col = 0
    max_ricb_converged = 0.0
    examples = []
    for cdir in case_dirs:
        le = light_el_from_dirname(os.path.basename(cdir))
        if le is None:
            continue
        liq = liquidus_from_dirname(os.path.basename(cdir))
        for csv_path in glob.glob(os.path.join(cdir, "pMetaData_*.csv")):
            try:
                df = pd.read_csv(csv_path)
            except Exception:
                continue
            if df.empty:
                continue
            n_files += 1
            n_total_rows += len(df)
            if "error_code" not in df.columns:
                n_no_error_code_col += len(df)
                conv = df  # assume all rows are converged results (no error_code column schema)
            else:
                conv = df[df["error_code"] == 0]
            n_converged += len(conv)
            if len(conv) == 0:
                continue
            if "ricb" in conv.columns:
                max_ricb_converged = max(max_ricb_converged, conv["ricb"].max())
            finite_cols = [c for c in ["rcmb", "ricb", "chi_li_icb", "Picb", "Tcmb"] if c in conv.columns]
            fail_finite = ~np.isfinite(conv[finite_cols]).all(axis=1) if finite_cols else pd.Series(False, index=conv.index)
            if "rcmb" in conv.columns and "ricb" in conv.columns:
                fail_rcmb = conv["rcmb"] <= conv["ricb"]
            else:
                fail_rcmb = pd.Series(False, index=conv.index)
            if le == "Si":
                chi_max_val = MAX_SI_STEINBRUEGGE if liq == "Steinbruegge" else MAX_SI_EDMUND
                fail_chi = conv["chi_li_icb"] > chi_max_val if "chi_li_icb" in conv.columns else pd.Series(False, index=conv.index)
            else:
                if "chi_li_icb" in conv.columns and "chi_li_eut_icb" in conv.columns:
                    fail_chi = conv["chi_li_icb"] > conv["chi_li_eut_icb"]
                else:
                    fail_chi = pd.Series(False, index=conv.index)
            fail_any = fail_finite | fail_rcmb | fail_chi
            n_fail_finite += int(fail_finite.sum())
            n_fail_rcmb += int(fail_rcmb.sum())
            n_fail_chi += int(fail_chi.sum())
            n_fail_any += int(fail_any.sum())
            if fail_any.any() and len(examples) < 5:
                bad = conv[fail_any].iloc[0]
                examples.append((csv_path, bad.to_dict()))
    results[label] = dict(n_files=n_files, n_total_rows=n_total_rows, n_converged=n_converged,
                           n_no_error_code_col=n_no_error_code_col,
                           n_fail_finite=n_fail_finite, n_fail_rcmb=n_fail_rcmb,
                           n_fail_chi=n_fail_chi, n_fail_any=n_fail_any,
                           max_ricb_converged=max_ricb_converged, examples=examples)

for label, r in results.items():
    print(f"=== {label} ===")
    print(f"  files={r['n_files']} total_rows={r['n_total_rows']} converged={r['n_converged']} "
          f"(no_error_code_col_rows={r['n_no_error_code_col']})")
    print(f"  box_fun failures among converged: finite={r['n_fail_finite']} rcmb<=ricb={r['n_fail_rcmb']} "
          f"chi>chi_max={r['n_fail_chi']} ANY={r['n_fail_any']}")
    print(f"  max ricb among converged rows: {r['max_ricb_converged']:.1f} m")
    for ex in r['examples']:
        print("  EXAMPLE:", ex)

print("\n=== detail on published_v1.0.5_full chi failures ===")
import glob as _glob
rows = []
for cdir in sorted(d for d in _glob.glob(os.path.expanduser("~/shared_dataset/zenodo.16459292/extracted/PIE/work.*/results/*")) if os.path.isdir(d)):
    base = os.path.basename(cdir)
    le = light_el_from_dirname(base)
    if le != "Si":
        continue
    liq = liquidus_from_dirname(base)
    chi_max_val = MAX_SI_STEINBRUEGGE if liq == "Steinbruegge" else MAX_SI_EDMUND
    for csv_path in _glob.glob(os.path.join(cdir, "pMetaData_*.csv")):
        df = pd.read_csv(csv_path)
        if df.empty or "error_code" not in df.columns:
            continue
        conv = df[df["error_code"] == 0]
        bad = conv[conv["chi_li_icb"] > chi_max_val]
        for _, r in bad.iterrows():
            rows.append({"dir": base, "chi_li_icb": r["chi_li_icb"], "chi_max": chi_max_val,
                         "excess": r["chi_li_icb"] - chi_max_val, "ricb": r["ricb"]})
if rows:
    d = pd.DataFrame(rows)
    print(f"n={len(d)}  excess min/median/max: {d.excess.min():.5g} / {d.excess.median():.5g} / {d.excess.max():.5g}")
    print(f"distinct compositions affected: {d['dir'].nunique()}")
    print(f"ricb range of affected rows: {d.ricb.min():.0f} - {d.ricb.max():.0f} m")
