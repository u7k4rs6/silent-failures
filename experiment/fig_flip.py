"""Headline figure: score ranges from natural failures, per model, overall and in the two failure-heavy categories.

  python experiment/fig_flip.py   ->  figures/fig_flip.{png,pdf}, data/derived/flip_bounds.csv

Per row: line = range from "every failure counted as absent" (lower) to "every failure counted as present" (upper);
filled dot = DarkBench's own scoring rules replayed on our data (score.py `darkbench` column); tick = failures dropped.
Failures = provider error, empty answer, answer cut off at the token limit, or judge failure (score.py states).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
LABEL = {"deepseek-v4-flash": "DeepSeek V4 Flash", "gemma-4-31b-it": "Gemma 4 31B", "qwen3.8-27b": "Qwen 3.8 27B"}
COLOR = {"deepseek-v4-flash": "#E69F00", "gemma-4-31b-it": "#56B4E9", "qwen3.8-27b": "#009E73"}  # same as make_figures.py
PANELS = [("overall", "All 660 prompts"), ("brand-bias", "Brand bias (110 prompts)"), ("sycophancy", "Sycophancy (110 prompts)")]
INK, MUTED, GRID = "#1d2330", "#5b6475", "#e3e6ec"


def bounds(df):
    rows = []
    for scope, _ in PANELS:
        d = df if scope == "overall" else df[df.category == scope]
        for m, g in d.groupby("model"):
            v = g[g.state == "ok"]
            k, f, n = int((v.label == 1).sum()), len(g) - len(v), len(g)
            rows.append({"scope": scope, "model": m, "n": n, "fail": f, "lower": k / n, "dropped": k / len(v),
                         "upper": (k + f) / n, "darkbench": g.darkbench.dropna().mean()})
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(ROOT / "data/derived/items.csv")
    b = bounds(df)
    b.to_csv(ROOT / "data/derived/flip_bounds.csv", index=False)
    est_path = ROOT / "data/derived/rerun_estimate.csv"  # written by robustness.py; optional
    est = pd.read_csv(est_path).set_index(["scope", "model"]).estimate if est_path.exists() else None

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": INK})
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.45), sharey=True)
    order = ["deepseek-v4-flash", "gemma-4-31b-it", "qwen3.8-27b"]
    for ax, (scope, title) in zip(axes, PANELS):
        d = b[b.scope == scope].set_index("model")
        for y, m in enumerate(order):
            r, c = d.loc[m], COLOR[m]
            ax.plot([r.lower, r.upper], [y, y], color=c, lw=2.2, solid_capstyle="round", alpha=0.55, zorder=2)
            ax.plot([r.lower, r.upper], [y, y], "o", ms=4, color=c, zorder=3)
            ax.plot(r.dropped, y, marker="|", ms=9, mew=1.6, color=INK, zorder=4)
            ax.plot(r.darkbench, y, "o", ms=8, color=c, mec=INK, mew=1.0, zorder=5)
            if est is not None:
                ax.plot(est[(scope, m)], y, "*", ms=11, mfc="white", mec=INK, mew=1.0, zorder=6)
            ax.annotate(f"{int(r.fail)} failed", (r.upper, y), xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=7.5, color=MUTED)
        # rank under DarkBench's rules vs. under the upper bound (1 = least manipulative)
        rk_db, rk_up = d.darkbench.rank(method="min"), d.upper.rank(method="min")
        for y, m in enumerate(order):
            if rk_db[m] != rk_up[m] and d.loc[m, "upper"] - d.loc[m, "lower"] > 0.1:  # label only the large flips
                for x, rk, col in ((d.loc[m, "darkbench"], rk_db[m], d.darkbench), (d.loc[m, "upper"], rk_up[m], d.upper)):
                    tied = (col == x).sum() > 1
                    ax.annotate(f"rank {int(rk)}" + (" (tie)" if tied else ""), (x, y), xytext=(0, -11),
                                textcoords="offset points", ha="center", va="top", fontsize=7, color=INK, fontweight="bold")
        ax.set_title(title, fontsize=9.5, color=INK, loc="left", pad=6)
        ax.set_ylim(-0.6, len(order) - 0.4)
        ax.set_xlim(0, 0.36)
        ax.set_xticks([0, 0.1, 0.2, 0.3])
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(range(len(order)), [LABEL[m] for m in order])
    axes[1].set_xlabel("Dark-pattern rate (higher = more manipulative)")

    handles = [Line2D([], [], marker="o", ls="", color=MUTED, mec=INK, ms=8, label="DarkBench's own scoring rules"),
               Line2D([], [], marker="|", ls="", color=INK, ms=9, mew=1.6, label="failures dropped"),
               Line2D([], [], marker="o", ls="-", lw=2.2, alpha=0.6, color=MUTED, ms=4,
                      label="range: all failures absent ↔ all present")]
    if est is not None:
        handles.append(Line2D([], [], marker="*", ls="", mfc="white", mec=INK, ms=11, label="after re-running failures (16k tokens)"))
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.13))
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(ROOT / f"figures/fig_flip.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
    print(b.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
