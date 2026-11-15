"""Headline figure: score ranges from natural failures, per model, overall and in the two failure-heavy categories.

  python experiment/fig_flip.py   ->  figures/fig_flip.{png,pdf}, data/derived/flip_bounds.csv

Per row: line = range from "every failure counted as absent" (lower) to "every failure counted as present" (upper);
filled dot = DarkBench's own scoring rules replayed on our data (score.py `darkbench` column); open dot = failures dropped;
diamond = re-run estimate (robustness.py). Right column = number of failed items.
Failures = provider error, empty answer, answer cut off at the token limit, or judge failure (score.py states).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
LABEL = {"deepseek-v4-flash": "DeepSeek V4 Flash", "gemma-4-31b-it": "Gemma 4 31B", "qwen3.8-27b": "Qwen 3.8 27B"}
PANELS = [("overall", "All prompts (660)"), ("brand-bias", "Brand bias (110)"), ("sycophancy", "Sycophancy (110)")]
INK, MUTED, GRID, ACCENT = "#111111", "#8a8f99", "#e6e6e6", "#c0392b"


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

    plt.rcParams.update({"font.family": ["Noto Sans", "DejaVu Sans"], "font.size": 8, "axes.edgecolor": INK,
                         "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.major.size": 2.5,
                         "xtick.color": INK, "ytick.color": INK, "axes.labelcolor": INK})
    fig, axes = plt.subplots(1, 3, figsize=(6.8, 1.95), sharey=True)
    order = ["deepseek-v4-flash", "gemma-4-31b-it", "qwen3.8-27b"]
    for i, (ax, (scope, title)) in enumerate(zip(axes, PANELS)):
        d = b[b.scope == scope].set_index("model")
        for y, m in enumerate(order):
            r = d.loc[m]
            ax.plot([r.lower, r.upper], [y, y], color=MUTED, lw=1.0, zorder=2, clip_on=False)
            ax.plot([r.lower, r.upper], [y, y], marker="|", ls="", ms=5, mew=1.0, color=MUTED, zorder=2, clip_on=False)
            ax.plot(r.dropped, y, marker="o", ms=4.2, mfc="white", mec=INK, mew=0.8, ls="", zorder=4, clip_on=False)
            ax.plot(r.darkbench, y, marker="o", ms=3.6, color=INK, ls="", zorder=5, clip_on=False)
            if est is not None:
                ax.plot(est[(scope, m)], y, marker="D", ms=5.2, mfc="none", mec=ACCENT, mew=1.1, ls="", zorder=6, clip_on=False)
            ax.text(1.0, y, f"{int(r.fail)}", transform=ax.get_yaxis_transform(), ha="right", va="center",
                    fontsize=7, color=MUTED)
        ax.text(1.0, len(order) - 0.45, "failed", transform=ax.get_yaxis_transform(), ha="right", va="bottom",
                fontsize=7, color=MUTED, style="italic")
        ax.set_title(f"({'abc'[i]}) {title}", fontsize=8.5, color=INK, loc="left", pad=4)
        ax.set_ylim(-0.5, len(order) - 0.5)
        ax.set_xlim(-0.01, 0.34)
        ax.set_xticks([0, 0.1, 0.2, 0.3], ["0", ".1", ".2", ".3"])
        ax.grid(axis="x", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(range(len(order)), [LABEL[m] for m in order])
    axes[1].set_xlabel("Dark-pattern rate (higher = more manipulative)", labelpad=3)

    handles = [Line2D([], [], color=MUTED, lw=1.0, marker="|", ms=5, mew=1.0, label="bounds (failures absent / present)"),
               Line2D([], [], marker="o", ls="", ms=3.6, color=INK, label="DarkBench rules"),
               Line2D([], [], marker="o", ls="", ms=4.2, mfc="white", mec=INK, mew=0.8, label="failures dropped")]
    if est is not None:
        handles.append(Line2D([], [], marker="D", ls="", ms=5.2, mfc="none", mec=ACCENT, mew=1.1, label="re-run estimate (16k tokens)"))
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False, fontsize=7.2,
               handletextpad=0.4, columnspacing=1.4, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1), w_pad=1.2)
    for ext in ("png", "pdf"):
        fig.savefig(ROOT / f"figures/fig_flip.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
    print(b.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
