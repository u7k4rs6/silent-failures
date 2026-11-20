"""Follow-up figures (v2 report). No API calls; run experiment/followup.py first.

  python experiment/fig_followup.py  ->  figures/fig_scale.{png,pdf}, figures/fig_repeats.{png,pdf}

fig_scale: six models at a 16k-token limit, same marks as fig_flip (bounds, DarkBench replay, failures dropped).
fig_repeats: Qwen 3.8 27B, the same prompts and settings run six times; one row per run.
"""
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

from fig_flip import INK, MUTED, GRID, ROOT

DER = ROOT / "data/derived"
LABEL = {"deepseek-v4-flash": "DeepSeek V4 Flash", "gemma-4-31b-it": "Gemma 4 31B", "qwen3.8-27b": "Qwen 3.8 27B",
         "glm-5.3-flash": "GLM 5.3 Flash", "nemotron-SEA-LION-v4.8-120b-a12b": "SEA-LION v4.8 120B",
         "qwen-SEA-LION-v5-397b-a17b-plus": "SEA-LION v5 397B"}


def style():
    plt.rcParams.update({"font.family": ["Noto Sans", "DejaVu Sans"], "font.size": 8, "axes.edgecolor": INK,
                         "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.major.size": 2.5,
                         "xtick.color": INK, "ytick.color": INK, "axes.labelcolor": INK})


def draw(ax, rows, title, xmax):
    """rows: DataFrame with lower, upper, darkbench, dropped (optional), fail; drawn bottom to top."""
    for y, (_, r) in enumerate(rows.iterrows()):
        ax.plot([r.lower, r.upper], [y, y], color=MUTED, lw=1.0, zorder=2, clip_on=False)
        ax.plot([r.lower, r.upper], [y, y], marker="|", ls="", ms=5, mew=1.0, color=MUTED, zorder=2, clip_on=False)
        if "dropped" in r and pd.notna(r.dropped):
            ax.plot(r.dropped, y, marker="o", ms=4.2, mfc="white", mec=INK, mew=0.8, ls="", zorder=4, clip_on=False)
        ax.plot(r.darkbench, y, marker="o", ms=3.6, color=INK, ls="", zorder=5, clip_on=False)
        ax.text(1.0, y, f"{int(r.fail)}", transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=7, color=MUTED)
    ax.text(1.0, len(rows) - 0.45, "failed", transform=ax.get_yaxis_transform(), ha="right", va="bottom",
            fontsize=7, color=MUTED, style="italic")
    ax.set_title(title, fontsize=8.5, color=INK, loc="left", pad=4)
    ax.set_ylim(-0.5, len(rows) - 0.5)
    ax.set_xlim(-0.01, xmax)
    ax.grid(axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)


def legend(fig, with_dropped, extra=()):
    h = [Line2D([], [], color=MUTED, lw=1.0, marker="|", ms=5, mew=1.0, label="bounds (failures absent / present)"),
         Line2D([], [], marker="o", ls="", ms=3.6, color=INK, label="DarkBench rules")]
    if with_dropped:
        h.append(Line2D([], [], marker="o", ls="", ms=4.2, mfc="white", mec=INK, mew=0.8, label="failures dropped"))
    h += list(extra)
    fig.legend(handles=h, loc="lower center", ncol=len(h), frameon=False, fontsize=7.2, handletextpad=0.4,
               columnspacing=1.4, bbox_to_anchor=(0.5, -0.02))


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(ROOT / f"figures/{name}.{ext}", dpi=300, bbox_inches="tight", facecolor="white")


def fig_scale():
    b = pd.read_csv(DER / "followup_bounds.csv")
    panels = [("overall", "(a) All prompts (660)", 0.34), ("brand-bias", "(b) Brand bias (110)", 0.20),
              ("sycophancy", "(c) Sycophancy (110)", 0.20)]
    order = b[b.scope == "overall"].sort_values("darkbench", ascending=False).model.tolist()  # worst at bottom
    fig, axes = plt.subplots(1, 3, figsize=(6.8, 2.5), sharey=True)
    for ax, (scope, title, xmax) in zip(axes, panels):
        draw(ax, b[b.scope == scope].set_index("model").loc[order], title, xmax)
    axes[0].set_yticks(range(len(order)), [LABEL[m] for m in order])
    axes[1].set_xlabel("Dark-pattern rate (higher = more manipulative)", labelpad=3)
    legend(fig, False)
    fig.tight_layout(rect=(0, 0.07, 1, 1), w_pad=1.2)
    save(fig, "fig_scale")


def fig_repeats():
    rs = pd.read_csv(DER / "followup_run_scores.csv")
    runs = ["sprint", "rep1", "rep2", "rep3", "rep4", "rep5"][::-1]
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.4), sharey=True)
    for ax, (cat, title, xmax) in zip(axes, [("brand-bias", "(a) Brand bias (110)", 0.36),
                                             ("sycophancy", "(b) Sycophancy (110)", 0.26)]):
        draw(ax, rs[rs.category == cat].set_index("run").loc[runs], title, xmax)
    # reference: DeepSeek's brand-bias rate under DarkBench's rules in the sprint run (flip_bounds.csv)
    fb = pd.read_csv(DER / "flip_bounds.csv")
    ds = fb[(fb.scope == "brand-bias") & (fb.model == "deepseek-v4-flash")].darkbench.iloc[0]
    axes[0].axvline(ds, color=MUTED, lw=0.8, ls=(0, (3, 2)), zorder=1)

    axes[0].set_yticks(range(len(runs)), ["sprint run" if r == "sprint" else f"repeat {r[-1]}" for r in runs])
    fig.supxlabel("Qwen 3.8 27B dark-pattern rate, same prompts and settings (4,096-token limit)", fontsize=8, y=0.1)
    legend(fig, True, [Line2D([], [], color=MUTED, lw=0.8, ls=(0, (3, 2)),
                              label=f"DeepSeek brand bias, sprint run ({ds:.3f})")])
    fig.tight_layout(rect=(0, 0.07, 1, 1), w_pad=1.2)
    save(fig, "fig_repeats")


if __name__ == "__main__":
    style()
    fig_scale()
    fig_repeats()
