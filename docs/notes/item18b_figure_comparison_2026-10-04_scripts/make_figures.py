"""
Item 18(b) -- BEFORE/AFTER figure comparison, using the paper's own
`paper_figures.py` binning/filter logic (Zenodo 10.5281/zenodo.16459292,
read-only reference, re-implemented here, not imported/edited) applied to
two row sets:

  BEFORE = published Zenodo CSVs only (weight = 1 per row, i.e. exact
           population counts, as the paper itself used).
  AFTER  = BEFORE + item 18(a)'s recovered rows (`build_rowsets.py`'s
           cache), each recovered row weighted by its stratified
           N_h/n_h (Horvitz-Thompson weight), so a bin's AFTER count is
           the same population point-estimate jordan-kim's analyze.py
           reports in aggregate (cross-checked against her totals below).

Output: one PNG per paper figure/panel family x MoI range, each a
BEFORE | AFTER side-by-side comparison with a shared color scale, saved
under `docs/notes/item18b_figure_comparison_2026-10-04_figs/`.

INTERNAL DRAFT -- item 18b comparison, not for publication. UNAUDITED,
owner (dunyu-liu) only, not for coauthor communication.

Print target: these are owner-facing comparison figures, not manuscript
inserts -- sized for on-screen/PDF review at a nominal 190 mm (Elsevier
full-width) print reference so the font-size rules still apply exactly;
k = canvas_width_in / (190 mm / 25.4). Each multi-panel canvas states its
own k in a corner annotation.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import os
ZEN = Path(os.path.expanduser(
    "~/shared_dataset/zenodo.16459292/extracted/Plotting and Analysis Scripts/For Monte Carlo Study"))
SCRIPT_DIR = Path(__file__).parent
CACHE = SCRIPT_DIR / "cache"
FIGDIR = SCRIPT_DIR.parent / "item18b_figure_comparison_2026-10-04_figs"
FIGDIR.mkdir(exist_ok=True)

PRINT_WIDTH_IN = 190.0 / 25.4  # mm -> in, Elsevier full width reference
FONT_LABEL = 10
FONT_TICK = 8
FONT_TITLE = 10
FONT_LEGEND = 8
FONT_SUPTITLE = 11

HEATMAP_MAX_RICB_KM = 1800.0  # paper_figures.py's heat-map ricb grid cap
RICB_VALS = np.linspace(0, 1800, 37)   # km, 50 km steps
CHISI_VALS = np.linspace(1, 12, 12)    # wt%
N_RICB, N_CHISI = len(RICB_VALS), len(CHISI_VALS)

MOI_TAGS = {"high": dict(mean=0.346, sigma=0.014, hist_range=(0.323, 0.361), bins=19),
            "low": dict(mean=0.333, sigma=0.005, hist_range=(0.324, 0.352), bins=14)}

CSV_NAMES = {
    "all": "all_models_{}MoI.csv",
    "sl": "snowlayer_{}MoI.csv",
    "goodTCMB": "goodTCMB_{}MoI.csv",
    "goodTCMB_sl": "goodTCMB_snowlayer_{}MoI.csv",
    "goodTCMB_goodchiS": "goodTCMB_goodchiS_{}MoI.csv",
}

WATERMARK = "INTERNAL DRAFT -- item 18b comparison, not for publication (UNAUDITED)"


def load_published(tag):
    out = {}
    for cat, pattern in CSV_NAMES.items():
        df = pd.read_csv(ZEN / pattern.format(tag))
        df["weight"] = 1.0
        out[cat] = df
    return out


def load_recovered(tag):
    df = pd.read_csv(CACHE / f"recovered_all_{tag}MoI.csv")
    is_sl = df["isnow"].astype(int).isin([1, 3])
    is_goodT = (df["Tcmb"] >= 1700) & (df["Tcmb"] <= 2100)
    is_goodT_sl = is_goodT & is_sl
    is_goodT_chiS = is_goodT & (df["chi_S_bulk"] < 0.02)
    return {
        "all": df,
        "sl": df[is_sl],
        "goodTCMB": df[is_goodT],
        "goodTCMB_sl": df[is_goodT_sl],
        "goodTCMB_goodchiS": df[is_goodT_chiS],
    }


def after_df(pub_cat_df, rec_cat_df):
    return pd.concat([pub_cat_df, rec_cat_df], ignore_index=True)


def bin_counts(df):
    counts = np.zeros((N_RICB, N_CHISI))
    for ricb in RICB_VALS:
        rowi = int(ricb / 50)
        ricb_exact = ricb * 1000 + 10
        for chiSi in CHISI_VALS:
            colj = int(chiSi - 1)
            chiSi_exact = chiSi / 100
            sel = df[(df["ricb"] == ricb_exact) & (np.isclose(df["chi_Si_icb"], chiSi_exact))]
            counts[rowi, colj] = sel["weight"].sum()
    return np.flipud(counts)


def bin_meanstd_chiS(df):
    mean = np.zeros((N_RICB, N_CHISI))
    std = np.zeros((N_RICB, N_CHISI))
    for ricb in RICB_VALS:
        rowi = int(ricb / 50)
        ricb_exact = ricb * 1000 + 10
        for chiSi in CHISI_VALS:
            colj = int(chiSi - 1)
            chiSi_exact = chiSi / 100
            sel = df[(df["ricb"] == ricb_exact) & (np.isclose(df["chi_Si_icb"], chiSi_exact))]
            if len(sel) == 0 or sel["weight"].sum() == 0:
                continue
            w = sel["weight"].to_numpy()
            x = sel["chi_S_bulk"].to_numpy() * 100
            m = np.average(x, weights=w)
            v = np.average((x - m) ** 2, weights=w)
            mean[rowi, colj] = m
            std[rowi, colj] = np.sqrt(v)
    return np.flipud(mean), np.flipud(std)


def ricb_axis_labels():
    yticks = list(np.linspace(0, 1800, 37).astype(int))
    for y in range(len(yticks)):
        if y % 4 != 0:
            yticks[y] = ""
    return np.flip(yticks)


def draw_heatmap(ax, arr, vmin, vmax, cmap, cbar_label, mask_zero=False):
    plot_arr = np.ma.masked_equal(arr, 0) if mask_zero else arr
    im = ax.imshow(plot_arr, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto",
                    extent=[0.5, N_CHISI + 0.5, 0, N_RICB])
    ax.set_xticks(np.arange(1, N_CHISI + 1))
    ax.set_xticklabels(np.arange(1, N_CHISI + 1), fontsize=FONT_TICK)
    yt = ricb_axis_labels()
    ax.set_yticks(np.arange(N_RICB) + 0.5)
    ax.set_yticklabels(yt, fontsize=FONT_TICK)
    ax.set_xlabel("wt % Si", fontsize=FONT_LABEL)
    ax.set_ylabel("ICB radius (km)", fontsize=FONT_LABEL)
    cbar = plt.colorbar(im, ax=ax, aspect=20, fraction=0.06)
    cbar.set_label(cbar_label, fontsize=FONT_LABEL)
    cbar.ax.tick_params(labelsize=FONT_TICK)
    # rule 4: colorbars always ticked at endpoints + midpoint/zero
    ticks = sorted(set([vmin, (vmin + vmax) / 2, vmax]))
    cbar.set_ticks(ticks)
    return im


def heatmap_ineligible_note(ax):
    # Folded into the x-axis label (layout-aware) rather than a floating
    # annotation, so constrained_layout reserves space for it and it
    # cannot collide with the row below.
    xl = ax.get_xlabel()
    ax.set_xlabel(xl + "\n[heat map: ricb<=1800 km only;\nrecovered rows to ~1950 km excluded -- see S6/Fig5]",
                  fontsize=FONT_LABEL - 2)


def add_watermark(fig):
    fig.text(0.5, 0.005, WATERMARK, ha="center", va="bottom", fontsize=7, color="gray", style="italic")


def savefig(fig, name, k):
    fig.text(0.01, 0.995, f"k={k:.2f}x print (190 mm ref)", ha="left", va="top", fontsize=6, color="gray")
    add_watermark(fig)
    outp = FIGDIR / name
    fig.savefig(outp, dpi=300)
    plt.close(fig)
    print("wrote", outp)


def heatmap_counts_panel(tag, cat, title, paper_fig):
    """Fig1 (goodTCMB) / Fig2 (goodTCMB_sl) / Fig4 (goodTCMB_goodchiS) style: counts heat map + MoI histogram."""
    pub = load_published(tag)
    rec = load_recovered(tag)
    before_df = pub[cat]
    after = after_df(pub[cat], rec[cat])
    cb = bin_counts(before_df)
    ca = bin_counts(after)
    vmax = max(cb.max(), ca.max())
    width_in = PRINT_WIDTH_IN * 2.2
    fig, axes = plt.subplots(2, 2, figsize=(width_in, width_in * 0.95), constrained_layout=True)
    k = width_in / PRINT_WIDTH_IN
    for col, (label, arr, df) in enumerate([("BEFORE (published)", cb, before_df), ("AFTER (+recovered)", ca, after)]):
        draw_heatmap(axes[0, col], arr, 0, vmax, "gist_heat_r", "Counts")
        axes[0, col].set_title(f"{label}\n{paper_fig}: {title}", fontsize=FONT_TITLE)
        heatmap_ineligible_note(axes[0, col])
        meta = MOI_TAGS[tag]
        axes[1, col].hist(df["moi"], bins=meta["bins"], range=meta["hist_range"], weights=df["weight"],
                           color="coral", edgecolor="k", linewidth=0.8)
        axes[1, col].axvline(meta["mean"], color="k", linestyle="dashed", linewidth=1.2,
                              label=r"$\tilde{C}$=" + str(meta["mean"]))
        axes[1, col].tick_params(labelsize=FONT_TICK)
        axes[1, col].set_xlabel(r"$\tilde{C}$ (MoI factor)", fontsize=FONT_LABEL)
        axes[1, col].set_ylabel("Counts (weighted)", fontsize=FONT_LABEL)
        axes[1, col].legend(fontsize=FONT_LEGEND, loc="upper left")
    moi_name = "margot/high" if tag == "high" else "genova/low"
    fig.suptitle(f"{paper_fig} comparison -- moi={tag} ({moi_name})", fontsize=FONT_SUPTITLE)
    savefig(fig, f"{paper_fig.lower()}_{cat}_{tag}MoI.png", k)
    return dict(tag=tag, cat=cat, before_total=float(cb.sum()), after_total=float(ca.sum()))


def heatmap_meanCV_panel(tag, cat, paper_fig):
    pub = load_published(tag)
    rec = load_recovered(tag)
    before_df = pub[cat]
    after = after_df(pub[cat], rec[cat])
    mb, sb = bin_meanstd_chiS(before_df)
    ma, sa = bin_meanstd_chiS(after)
    cvb = np.divide(sb, mb, out=np.zeros_like(sb), where=mb != 0)
    cva = np.divide(sa, ma, out=np.zeros_like(sa), where=ma != 0)
    vmax_mean = max(mb.max(), ma.max())
    vmin_mean = min(x[x > 0].min() if (x > 0).any() else 0 for x in (mb, ma))
    vmax_cv = max(cvb.max(), cva.max())
    vmin_cv = min(x[x > 0].min() if (x > 0).any() else 0 for x in (cvb, cva))
    width_in = PRINT_WIDTH_IN * 2.2
    fig, axes = plt.subplots(2, 2, figsize=(width_in, width_in * 0.95), constrained_layout=True)
    k = width_in / PRINT_WIDTH_IN
    for col, (label, marr, carr) in enumerate([("BEFORE", mb, cvb), ("AFTER", ma, cva)]):
        draw_heatmap(axes[0, col], marr, vmin_mean, vmax_mean, "viridis_r", "Mean chi_S,bulk (wt%)", mask_zero=True)
        axes[0, col].set_title(f"{label} -- {paper_fig} mean chi_S,bulk", fontsize=FONT_TITLE)
        heatmap_ineligible_note(axes[0, col])
        draw_heatmap(axes[1, col], carr, vmin_cv, vmax_cv, "viridis_r", "CV of chi_S,bulk", mask_zero=True)
        axes[1, col].set_title(f"{label} -- {paper_fig} CV chi_S,bulk", fontsize=FONT_TITLE)
        heatmap_ineligible_note(axes[1, col])
    fig.suptitle(f"{paper_fig} comparison -- moi={tag}, category={cat}", fontsize=FONT_SUPTITLE)
    savefig(fig, f"{paper_fig.lower()}_meanCV_{cat}_{tag}MoI.png", k)


def s5_heatmaps(tag):
    cats = ["all", "goodTCMB", "sl", "goodTCMB_sl"]
    titles = ["All Successful Models", "TCMB Constraint", "Snow Layer Constraint", "TCMB Constraint + Snow Layer"]
    pub = load_published(tag)
    rec = load_recovered(tag)
    befores = {c: bin_counts(pub[c]) for c in cats}
    afters = {c: bin_counts(after_df(pub[c], rec[c])) for c in cats}
    width_in = PRINT_WIDTH_IN * 1.4
    fig, axes = plt.subplots(4, 2, figsize=(width_in, width_in * 1.9), constrained_layout=True)
    k = width_in / PRINT_WIDTH_IN
    for i, cat in enumerate(cats):
        vmax = max(befores[cat].max(), afters[cat].max())
        draw_heatmap(axes[i, 0], befores[cat], 0, vmax, "gist_heat_r", "Counts")
        axes[i, 0].set_title(f"BEFORE -- {titles[i]}", fontsize=FONT_TITLE)
        heatmap_ineligible_note(axes[i, 0])
        draw_heatmap(axes[i, 1], afters[cat], 0, vmax, "gist_heat_r", "Counts")
        axes[i, 1].set_title(f"AFTER -- {titles[i]}", fontsize=FONT_TITLE)
        heatmap_ineligible_note(axes[i, 1])
    fig.suptitle(f"Fig S5 comparison (heat maps) -- moi={tag}", fontsize=FONT_SUPTITLE)
    savefig(fig, f"figs5_heatmaps_{tag}MoI.png", k)


def s6_hist(tag):
    cats = ["all", "goodTCMB", "sl", "goodTCMB_sl"]
    titles = ["All Successful Models", "TCMB Constraint", "Snow Layer Constraint", "TCMB Constraint + Snow Layer"]
    pub = load_published(tag)
    rec = load_recovered(tag)
    meta = MOI_TAGS[tag]
    width_in = PRINT_WIDTH_IN * 1.4
    fig, axes = plt.subplots(4, 2, figsize=(width_in, width_in * 1.6), constrained_layout=True)
    k = width_in / PRINT_WIDTH_IN
    for i, cat in enumerate(cats):
        bdf = pub[cat]
        adf = after_df(pub[cat], rec[cat])
        hmax = 0
        for col, df in [(0, bdf), (1, adf)]:
            h, _ = np.histogram(df["moi"], bins=meta["bins"], range=meta["hist_range"], weights=df["weight"])
            hmax = max(hmax, h.max() if len(h) else 0)
        for col, (label, df) in enumerate([("BEFORE", bdf), ("AFTER", adf)]):
            ax = axes[i, col]
            ax.hist(df["moi"], bins=meta["bins"], range=meta["hist_range"], weights=df["weight"],
                    color="coral", edgecolor="k", linewidth=0.8)
            ax.axvline(meta["mean"], color="k", linestyle="dashed", linewidth=1.2)
            ax.set_ylim(0, hmax * 1.05 if hmax > 0 else 1)
            ax.set_xlabel(r"$\tilde{C}$ (MoI factor)", fontsize=FONT_LABEL)
            ax.set_ylabel("Counts (weighted)", fontsize=FONT_LABEL)
            ax.set_title(f"{label} -- {titles[i]}", fontsize=FONT_TITLE)
            ax.tick_params(labelsize=FONT_TICK)
            ax.text(0.98, 0.95, "full ricb range (not heat-map-limited)", transform=ax.transAxes,
                    ha="right", va="top", fontsize=6.5, color="darkgreen")
    fig.suptitle(f"Fig S6 comparison (MoI histograms, full ricb range) -- moi={tag}", fontsize=FONT_SUPTITLE)
    savefig(fig, f"figs6_hist_{tag}MoI.png", k)


def s9_s10_fraccounts(tag, paper_fig):
    cats = ["goodTCMB", "sl", "goodTCMB_goodchiS"]
    titles = ["TCMB Constraint", "Snow Layer Constraint (no TCMB filter --\n"
              "published script mislabels this row 'TCMB+Snow',\n"
              "a pre-existing paper_figures.py bug, reproduced\n"
              "here WITHOUT the mislabel; see item18b note sec.0)",
              "TCMB Constraint + chi_S,bulk<2wt%"]
    pub = load_published(tag)
    rec = load_recovered(tag)
    width_in = PRINT_WIDTH_IN * 1.4
    fig, axes = plt.subplots(3, 2, figsize=(width_in, width_in * 1.5), constrained_layout=True)
    k = width_in / PRINT_WIDTH_IN
    for i, cat in enumerate(cats):
        cb = bin_counts(pub[cat])
        ca = bin_counts(after_df(pub[cat], rec[cat]))
        fb = cb / cb.max() if cb.max() > 0 else cb
        fa = ca / ca.max() if ca.max() > 0 else ca
        for col, (label, arr) in enumerate([("BEFORE", fb), ("AFTER", fa)]):
            draw_heatmap(axes[i, col], arr, 0, 1, "pink_r", "Fraction of max. count")
            axes[i, col].set_title(f"{label} -- {titles[i]}", fontsize=FONT_TITLE - 1)
            heatmap_ineligible_note(axes[i, col])
    fig.suptitle(f"{paper_fig} comparison (fraction-of-max heat maps) -- moi={tag}", fontsize=FONT_SUPTITLE)
    savefig(fig, f"{paper_fig.lower()}_fraccounts_{tag}MoI.png", k)


def fig5_scatter():
    cat = "goodTCMB_goodchiS"
    parts = []
    for tag in ("high", "low"):
        pub = load_published(tag)
        rec = load_recovered(tag)
        bdf = pub[cat].copy()
        rdf = rec[cat].copy()
        bdf["set"] = "published"
        rdf["set"] = "recovered"
        parts.append(pd.concat([bdf, rdf], ignore_index=True))
    combo = pd.concat(parts, ignore_index=True)
    before = combo[combo["set"] == "published"]
    after = combo

    def panel(ax, df, xcol, ycol, xlabel, ylabel, highlight=False):
        pubmask = df["set"] == "published"
        ax.scatter(df.loc[pubmask, xcol], df.loc[pubmask, ycol], color="lightgreen", s=8, label="published")
        if highlight:
            recmask = df["set"] == "recovered"
            ax.scatter(df.loc[recmask, xcol], df.loc[recmask, ycol], color="crimson", s=10,
                       marker="^", label="recovered (unweighted, 1 sampled run = 1 pt)")
        ax.axvline(0.346, color="indianred", linewidth=1, label=r"$\tilde{C}=0.346$" if xcol == "moi" else None)
        ax.axvline(0.333, color="cornflowerblue", linewidth=1, label=r"$\tilde{C}=0.333$" if xcol == "moi" else None)
        ax.set_xlabel(xlabel, fontsize=FONT_LABEL)
        ax.set_ylabel(ylabel, fontsize=FONT_LABEL)
        ax.tick_params(labelsize=FONT_TICK)

    width_in = PRINT_WIDTH_IN * 2.2
    fig, axes = plt.subplots(4, 2, figsize=(width_in, width_in * 1.3), constrained_layout=True)
    k = width_in / PRINT_WIDTH_IN
    rows = [
        ("moi", "ricb_km", r"$\tilde{C}$", r"$r_{ICB}$ (km)"),
        ("moi", "chi_Si_icb_pct", r"$\tilde{C}$", r"$\chi_{Si}$ (wt%)"),
        ("moi", "rhom", r"$\tilde{C}$", r"Mantle density (kg/m$^3$)"),
        ("ricb_km", "rhom", r"Inner core radius (km)", r"Mantle density (kg/m$^3$)"),
    ]
    for df_ in (before, after):
        df_["ricb_km"] = (df_["ricb"] - 10) / 1000
        df_["chi_Si_icb_pct"] = df_["chi_Si_icb"] * 100
    for i, (xcol, ycol, xl, yl) in enumerate(rows):
        panel(axes[i, 0], before, xcol, ycol, xl, yl, highlight=False)
        axes[i, 0].set_title("BEFORE (published only)" if i == 0 else "", fontsize=FONT_TITLE)
        panel(axes[i, 1], after, xcol, ycol, xl, yl, highlight=True)
        axes[i, 1].set_title("AFTER (+recovered, highlighted)" if i == 0 else "", fontsize=FONT_TITLE)
    axes[0, 0].legend(fontsize=FONT_LEGEND, loc="best")
    axes[0, 1].legend(fontsize=FONT_LEGEND, loc="best")
    fig.suptitle("Fig 5 comparison -- goodTCMB_goodchiS (both MoI ranges combined)\n"
                 "unbinned scatter: full ricb range, NOT heat-map-limited", fontsize=FONT_SUPTITLE)
    savefig(fig, "fig5_scatter_goodTCMBandS.png", k)
    return dict(before_n=int(len(before)), after_n_unweighted=int(len(after)),
                recovered_n_unweighted=int((after["set"] == "recovered").sum()))


def main():
    summary = []
    for tag in ("high", "low"):
        summary.append(heatmap_counts_panel(tag, "goodTCMB", "TCMB Constraint", "Fig1"))
        summary.append(heatmap_counts_panel(tag, "goodTCMB_sl", "TCMB Constraint + Snow Layer (HEADLINE)", "Fig2"))
        summary.append(heatmap_counts_panel(tag, "goodTCMB_goodchiS", "TCMB + chi_S,bulk<2wt%", "Fig4"))
        heatmap_meanCV_panel(tag, "goodTCMB_sl", "Fig3")
        heatmap_meanCV_panel(tag, "all", "FigS7" if tag == "high" else "FigS8")
        s5_heatmaps(tag)
        s6_hist(tag)
        s9_s10_fraccounts(tag, "FigS9" if tag == "high" else "FigS10")
    fig5_summary = fig5_scatter()
    report = dict(heatmap_counts=summary, fig5=fig5_summary)
    with open(SCRIPT_DIR / "comparison_summary.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
