import json, collections, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/home/utig5/dliu/PIE/docs/notes"
inv = json.load(open(HERE + "/inventory.json"))
ENDS = [("detJ0", True, "det(J)=0 at 10 m (zero rows)"), ("crash_stderr", True, "singular-LU crash at 10 m (zero rows)"), ("newton_maxit", True, "Newton maxit at 10 m (zero rows)"),
        ("detJ0", False, "det(J)=0 at later radius"), ("crash_stderr", False, "crash at later radius"), ("newton_maxit", False, "Newton maxit at later radius"), ("finish", False, "finished all 40 radii")]
COL = ["tab:red", "tab:orange", "tab:pink", "tab:blue", "tab:cyan", "tab:purple", "tab:green"]

# Fig 1: CMR2 histograms coloured by end state, per MOI x composition
labs = ["S_0.00", "Si_0.00", "S+Si_0.05", "S+Si_0.10"]
fig, axes = plt.subplots(2, 4, figsize=(18, 7), sharex="row")
for i, moi in enumerate(("margot", "genova")):
    for j, lab in enumerate(labs):
        data = collections.defaultdict(list)
        for key, v in inv[moi]["logs"].items():
            c1 = float(key.split(",")[0])
            for s in v["segs"]:
                if s["label"] == lab:
                    data[(s["end"], s["last_r"] == 10.0 and s["end"] != "finish")].append(c1)
        ax = axes[i, j]
        allc = np.concatenate([np.array(x) for x in data.values()])
        bins = np.linspace(allc.min(), allc.max(), 36)
        ax.hist([data.get((e, a), []) for e, a, _ in ENDS], bins=bins, stacked=True, color=COL, label=[t for _, _, t in ENDS])
        ax.set_title(f"{moi} / {lab.replace('_0.00','').replace('_',' chi_Si=')}"); ax.set_xlabel("CMR2")
        if j == 0: ax.set_ylabel("MC draws")
axes[0, 0].legend(fontsize=7)
plt.tight_layout(); plt.savefig(OUT + "/failure_analysis_fig1_cmr2_by_endstate.png", dpi=130); plt.close()

# Fig 2: radius at which the run died, by end state
fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
for i, moi in enumerate(("margot", "genova")):
    data = collections.defaultdict(list)
    for v in inv[moi]["logs"].values():
        for s in v["segs"]:
            if s["end"] in ("finish", "si_exceed") or s["last_r"] == 10.0: continue
            data[s["end"]].append(s["last_r"] / 1e3)
    ax = axes[i]
    ax.hist([data["detJ0"], data["crash_stderr"], data["newton_maxit"]], bins=np.arange(25, 2000, 50), stacked=True,
            color=["tab:blue", "tab:cyan", "tab:purple"], label=["det(J)=0 (chi_li_icb hits eutectic)", "crash (singular LU / getk2 IndexError)", "Newton maxit"])
    ax.set_title(f"{moi}: radius at which the sweep died (excluding 10 m)"); ax.set_xlabel("first failed inner-core radius [km]"); ax.set_ylabel("runs"); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(OUT + "/failure_analysis_fig2_death_radius.png", dpi=130); plt.close()

# Fig 3: zero-row fraction vs chi_Si for S+Si, by end state
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for i, moi in enumerate(("margot", "genova")):
    chis = np.linspace(0, 0.12, 13)
    frac = {e: [] for e, a, _ in ENDS[:3]}
    for c in chis:
        lab = f"S+Si_{c:.2f}"; n = 0; cnt = collections.Counter()
        for v in inv[moi]["logs"].values():
            for s in v["segs"]:
                if s["label"] == lab:
                    n += 1
                    if s["last_r"] == 10.0 and s["end"] != "finish": cnt[s["end"]] += 1
        for e in frac: frac[e].append(cnt[e] / n)
    ax = axes[i]; bottom = np.zeros(len(chis))
    for (e, a, t), col in zip(ENDS[:3], COL[:3]):
        ax.bar(chis * 100, frac[e], width=0.8, bottom=bottom, color=col, label=t); bottom += np.array(frac[e])
    ax.set_title(f"{moi} S+Si: fraction of draws with ZERO rows"); ax.set_xlabel("chi_Si at ICB [wt%]"); ax.set_ylabel("fraction of 1024 draws"); ax.set_ylim(0, 1); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(OUT + "/failure_analysis_fig3_zero_rows_vs_chiSi.png", dpi=130); plt.close()
print("figures written")
