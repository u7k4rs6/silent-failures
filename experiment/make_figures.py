#!/usr/bin/env python3
"""Create experiment figures and summary tables from data/derived CSVs."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "derived"
FIGURES = ROOT / "figures"

MODEL_LABELS = {
    "gemma-4-31b-it": "Gemma 4 31B",
    "qwen3.8-27b": "Qwen 3.8 27B",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
}

# Okabe-Ito palette, assigned deterministically by the displayed model label.
OKABE_ITO = [
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#0072B2",  # blue
    "#D55E00",  # vermilion
    "#CC79A7",  # reddish purple
    "#000000",  # black
]
POLICY_STYLES = {"IMPUTE-NEG": "-", "DROP": "--", "IMPUTE-POS": ":"}
FAILURE_STATES = ["F1", "F2", "F3", "TR"]
FAILURE_HATCHES = {"F1": "///", "F2": "\\\\", "F3": "xx", "TR": ".."}


def short_model(model: object) -> str:
    name = str(model)
    return MODEL_LABELS.get(name, name)


def read_csv(name: str, required: list[str]) -> pd.DataFrame:
    path = DATA / name
    frame = pd.read_csv(path)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
    return frame


def model_colors(models: list[str]) -> dict[str, str]:
    labels = sorted(set(models), key=lambda model: short_model(model).casefold())
    return {model: OKABE_ITO[i % len(OKABE_ITO)] for i, model in enumerate(labels)}


def save_figure(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIGURES / f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_headline(injection: pd.DataFrame, flips: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(6.7, 3.55), sharey=True)
    models = sorted(injection["model"].dropna().astype(str).unique(), key=lambda model: short_model(model).casefold())
    colors = model_colors(models)
    policies = [policy for policy in ["IMPUTE-NEG", "DROP", "IMPUTE-POS"] if policy in set(injection["policy"].dropna())]

    for ax, mechanism in zip(axes, ["MCAR", "MNAR"]):
        panel = injection[injection["mechanism"] == mechanism].copy()
        for model in models:
            model_panel = panel[panel["model"].astype(str) == model]
            for policy in policies:
                curve = model_panel[model_panel["policy"] == policy].sort_values("p")
                if curve.empty:
                    continue
                x = pd.to_numeric(curve["p"], errors="coerce").to_numpy(float)
                y = pd.to_numeric(curve["mean"], errors="coerce").to_numpy(float)
                lo = pd.to_numeric(curve["lo"], errors="coerce").to_numpy(float)
                hi = pd.to_numeric(curve["hi"], errors="coerce").to_numpy(float)
                valid = np.isfinite(x) & np.isfinite(y)
                if not valid.any():
                    continue
                x, y = x[valid], y[valid]
                lo, hi = lo[valid], hi[valid]
                ax.plot(
                    x,
                    y,
                    color=colors[model],
                    linestyle=POLICY_STYLES.get(policy, "-"),
                    linewidth=1.45,
                    label=f"{short_model(model)}: {policy}",
                    zorder=3,
                )
                band = np.isfinite(lo) & np.isfinite(hi)
                if band.any():
                    ax.fill_between(x[band], lo[band], hi[band], color=colors[model], alpha=0.12, linewidth=0, zorder=1)

            # The policies coincide at p=0 by construction; use the NEG row as the model baseline.
            baseline = model_panel[(model_panel["policy"] == "IMPUTE-NEG") & (pd.to_numeric(model_panel["p"], errors="coerce") == 0)]
            if baseline.empty:
                baseline = model_panel[pd.to_numeric(model_panel["p"], errors="coerce") == 0]
            if not baseline.empty:
                value = pd.to_numeric(baseline.iloc[0]["mean"], errors="coerce")
                if pd.notna(value):
                    ax.axhline(float(value), color=colors[model], linestyle=":", linewidth=0.8, alpha=0.7, zorder=2)

        # Mark provider-differential ranking flips on the worse model's NEG curve.
        if not flips.empty:
            flip_panel = flips[(flips["mechanism"] == mechanism) & (flips["policy"] == "IMPUTE-NEG")].copy()
            flip_panel["flip_p"] = pd.to_numeric(flip_panel["flip_p"], errors="coerce")
            flip_panel = flip_panel[np.isfinite(flip_panel["flip_p"])]
            for rank, (_, flip) in enumerate(flip_panel.iterrows()):
                worse, safer, point = str(flip["worse"]), str(flip["safer"]), float(flip["flip_p"])
                curve = panel[(panel["model"].astype(str) == worse) & (panel["policy"] == "IMPUTE-NEG")].sort_values("p")
                if curve.empty:
                    continue
                cx = pd.to_numeric(curve["p"], errors="coerce").to_numpy(float)
                cy = pd.to_numeric(curve["mean"], errors="coerce").to_numpy(float)
                valid = np.isfinite(cx) & np.isfinite(cy)
                if valid.sum() == 0 or point < cx[valid].min() or point > cx[valid].max():
                    continue
                ypoint = float(np.interp(point, cx[valid], cy[valid]))
                color = colors.get(worse, "#333333")
                ax.scatter([point], [ypoint], marker="D", s=20, color=color, edgecolor="white", linewidth=0.45, zorder=5)
                x_fraction = float(np.clip(point / 0.30, 0.06, 0.94))
                place_left = x_fraction >= 0.58
                ax.annotate(
                    f"flips below\n{short_model(safer)}",
                    (point, ypoint),
                    xytext=(x_fraction, 0.95 - 0.12 * (rank % 4)),
                    textcoords="axes fraction",
                    fontsize=5.9,
                    color=color,
                    ha="right" if place_left else "left",
                    va="top",
                    bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none", "pad": 1.0},
                    arrowprops={"arrowstyle": "-", "color": color, "lw": 0.55},
                )

        ax.set_title(mechanism, fontsize=10, pad=5)
        ax.set_xlim(0, 0.30)
        ax.set_xticks(np.arange(0, 0.301, 0.05), [f"{p:.0%}" for p in np.arange(0, 0.301, 0.05)])
        ax.set_xlabel("Injected failure rate p")
        ax.grid(axis="both", color="#D9D9D9", linewidth=0.55, alpha=0.75)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)

    axes[0].set_ylabel("Dark-pattern rate")
    model_handles = [Line2D([0], [0], color=colors[m], lw=2, label=short_model(m)) for m in models]
    policy_handles = [
        Line2D([0], [0], color="#444444", lw=1.35, linestyle=POLICY_STYLES[p], label=p)
        for p in policies
    ]
    handles = model_handles + policy_handles
    if handles:
        fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.01), ncol=min(5, len(handles)), frameon=False, fontsize=7.2)
    fig.subplots_adjust(left=0.09, right=0.99, top=0.88, bottom=0.22, wspace=0.12)
    save_figure(fig, "fig_headline")


def plot_natural_failures(items: pd.DataFrame) -> None:
    failed = items[items["gen_state"].isin(FAILURE_STATES)].copy()
    categories = sorted(failed["category"].dropna().astype(str).unique())
    models = sorted(items["model"].dropna().astype(str).unique(), key=lambda model: short_model(model).casefold())
    colors = model_colors(models)
    fig_width = max(6.7, min(10.0, 3.6 + 0.38 * len(categories)))
    fig, ax = plt.subplots(figsize=(fig_width, 3.6))

    if categories and models:
        positions = np.arange(len(categories), dtype=float)
        group_width = 0.82
        bar_width = group_width / max(1, len(models))
        counts = failed.groupby(["category", "model", "gen_state"], observed=False).size()
        for model_index, model in enumerate(models):
            x = positions + (model_index - (len(models) - 1) / 2) * bar_width
            bottom = np.zeros(len(categories), dtype=float)
            for state in FAILURE_STATES:
                heights = np.array([counts.get((category, model, state), 0) for category in categories], dtype=float)
                ax.bar(
                    x,
                    heights,
                    bar_width * 0.88,
                    bottom=bottom,
                    color=colors[model],
                    edgecolor="#333333",
                    linewidth=0.35,
                    hatch=FAILURE_HATCHES[state],
                    label=f"{short_model(model)}: {state}",
                )
                bottom += heights
        ax.set_xticks(positions, categories, rotation=25, ha="right")
        model_handles = [Patch(facecolor=colors[m], edgecolor="#333333", label=short_model(m)) for m in models]
        state_handles = [
            Patch(facecolor="white", edgecolor="#444444", hatch=FAILURE_HATCHES[state], label=state)
            for state in FAILURE_STATES
        ]
        fig.legend(handles=model_handles, title="Model", loc="upper left", bbox_to_anchor=(0.04, 0.99), ncol=min(3, len(model_handles)), frameon=False, fontsize=7, title_fontsize=7)
        fig.legend(handles=state_handles, title="Generation failure", loc="upper right", bbox_to_anchor=(0.98, 0.99), ncol=3, frameon=False, fontsize=7, title_fontsize=7)
    else:
        ax.text(0.5, 0.5, "No non-ok F1–F3 generation rows", transform=ax.transAxes, ha="center", va="center", fontsize=9)

    ax.set_ylabel("Item count")
    ax.set_xlabel("Category")
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.55, alpha=0.75)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=(0, 0, 1, 0.82))
    save_figure(fig, "fig_natural_failures")


def fmt(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{number:.3f}" if math.isfinite(number) else "n/a"


def fmt_int(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return str(int(number)) if math.isfinite(number) else "n/a"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(escape(h) for h in headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(escape(value) for value in row) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def latex_escape(value: object) -> str:
    text = str(value)
    for char, replacement in {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }.items():
        text = text.replace(char, replacement)
    return text


def write_tables(scores: pd.DataFrame, probes: pd.DataFrame) -> None:
    failure_columns = [f"n_F{i}" for i in range(1, 7)]
    headers = ["Model", "n", "Coverage", *[f"F{i}" for i in range(1, 7)], "DROP (valid)", "[IMPUTE-NEG, IMPUTE-POS]"]
    table_rows = []
    for _, row in scores.sort_values("model").iterrows():
        interval = f"[{fmt(row['IMPUTE-NEG'])}, {fmt(row['IMPUTE-POS'])}]"
        table_rows.append([
            short_model(row["model"]),
            fmt_int(row["n"]),
            fmt(row["coverage"]),
            *[fmt_int(row[column]) for column in failure_columns],
            fmt(row["DROP"]),
            interval,
        ])
    (FIGURES / "table_bounds.md").write_text("# Natural-result policy bounds\n\n" + markdown_table(headers, table_rows), encoding="utf-8")

    latex_headers = [latex_escape(header) for header in headers]
    column_spec = "l" + "r" * (len(headers) - 1)
    tex_lines = [
        r"\begin{tabular}{" + column_spec + "}",
        r"\hline",
        " & ".join(latex_headers) + r" \\",
        r"\hline",
    ]
    for row in table_rows:
        tex_lines.append(" & ".join(latex_escape(value) if not value.startswith("[") else "$" + value.replace("[", r"\left[").replace("]", r"\right]") + "$" for value in row) + r" \\")
    tex_lines.extend([r"\hline", r"\end{tabular}", ""])
    (FIGURES / "table_bounds.tex").write_text("\n".join(tex_lines), encoding="utf-8")

    probe_headers = ["Artifact", "Present", "Absent", "Unparsed", "n"]
    probe_rows = []
    for _, row in probes.sort_values("artifact").iterrows():
        probe_rows.append([str(row["artifact"]), fmt(row["present"]), fmt(row["absent"]), fmt(row["unparsed"]), fmt(row["n"])])
    (FIGURES / "table_probe.md").write_text("# Probe artifact summary\n\n" + markdown_table(probe_headers, probe_rows), encoding="utf-8")


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    injection = read_csv("injection.csv", ["model", "mechanism", "p", "policy", "mean", "lo", "hi"])
    flips = read_csv("flip_points.csv", ["safer", "worse", "gap", "mechanism", "policy", "flip_p"])
    scores = read_csv(
        "policy_scores.csv",
        ["model", "n", "n_valid", "n_fail", "coverage", *[f"n_F{i}" for i in range(1, 7)], "IMPUTE-NEG", "IMPUTE-POS", "DROP", "GRADE-AS-OUTPUT"],
    )
    items = read_csv("items.csv", ["model", "item_id", "category", "gen_state", "judge_state", "label", "state"])
    probes = read_csv("probe_summary.csv", ["artifact", "present", "absent", "unparsed", "n"])

    plot_headline(injection, flips)
    plot_natural_failures(items)
    write_tables(scores, probes)


if __name__ == "__main__":
    main()
