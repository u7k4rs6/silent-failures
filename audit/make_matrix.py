#!/usr/bin/env python3
"""Render the split and default-route harness failure policy matrices."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SOURCE = ROOT / "audit_table_v2.csv"
FIGURES = REPO / "figures"
FAILURES = [f"F{i}" for i in range(1, 7)]

COMPONENTS = [
    ("inspect_ai", "inspect_ai"),
    ("inspect_evals/mask", "inspect_evals / MASK"),
    ("inspect_evals/agentharm", "inspect_evals / AgentHarm"),
    ("inspect_evals/strong_reject", "inspect_evals / StrongREJECT"),
    ("inspect_evals/theagentcompany", "inspect_evals / TheAgentCompany"),
    ("darkbench", "DarkBench"),
    ("harmbench", "HarmBench"),
    ("pyrit", "PyRIT (attack components)"),
    ("promptfoo-evals", "promptfoo / evals"),
    ("promptfoo-redteam", "promptfoo / red-team"),
    ("lm_eval", "lm_eval"),
    ("mask_orig", "MASK (original)"),
]

POLICY_CODES = {
    "IMPUTE-NEG": ("NEG", "Imputed: absent", "absent"),
    "IMPUTE-POS": ("POS", "Imputed: present", "present"),
    "IMPUTE-RANDOM": ("RAND", "Random", "random"),
    "GRADE-AS-OUTPUT": ("GRADE", "Graded as output", "grade"),
    "DROP-SILENT": ("DROP-S", "Dropped (silent)", "dropped"),
    "DROP-REPORTED": ("DROP-R", "Dropped (reported)", "dropped"),
    "SEPARATE": ("SEP", "Separate outcome", "separate"),
    "ABORT": ("ABORT", "Abort", "abort"),
}

# Okabe-Ito colors; Abort and Separate outcome use different colors.
COLORS = {
    "absent": "#0072B2",
    "present": "#D55E00",
    "grade": "#CC79A7",
    "dropped": "#999999",
    "separate": "#009E73",
    "abort": "#000000",
    "random": "#E69F00",
}
TEXT_COLORS = {key: "white" for key in COLORS}
TEXT_COLORS.update({"grade": "#202020", "random": "#202020"})


def component_key(harness: str) -> str:
    if harness == "MASK (original)":
        return "mask_orig"
    if harness == "HarmBench":
        return "harmbench"
    if harness == "DarkBench":
        return "darkbench"
    if harness == "promptfoo (evals)":
        return "promptfoo-evals"
    if harness == "promptfoo (red-team)":
        return "promptfoo-redteam"
    if harness.startswith("inspect_evals/"):
        return harness
    if harness.startswith("pyrit/"):
        return "pyrit"
    return harness


def policy_details(policy: str) -> tuple[str, str, str, str]:
    retry = policy.startswith("RETRY-THEN-")
    base = policy.removeprefix("RETRY-THEN-") if retry else policy
    if base not in POLICY_CODES:
        raise ValueError(f"Unrecognized policy: {policy}")
    code, full, family = POLICY_CODES[base]
    prefix = "R→" if retry else ""
    full = f"Retry → {full}" if retry else full
    return prefix + code, full, family, base


def wrapped_label(label: str) -> str:
    return {
        "Imputed: absent": "Imputed:\nabsent",
        "Imputed: present": "Imputed:\npresent",
        "Graded as output": "Graded as\noutput",
        "Dropped (silent)": "Dropped\n(silent)",
        "Dropped (reported)": "Dropped\n(reported)",
        "Separate outcome": "Separate\noutcome",
        "R→ Imputed: absent": "R→ Imputed:\nabsent",
        "R→ Imputed: present": "R→ Imputed:\npresent",
        "R→ Graded as output": "R→ Graded as\noutput",
        "R→ Dropped (silent)": "R→ Dropped\n(silent)",
        "R→ Dropped (reported)": "R→ Dropped\n(reported)",
        "R→ Separate outcome": "R→ Separate\noutcome",
        "R→ Abort": "R→ Abort",
    }.get(label, label)


def read_rows() -> list[dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    expected = {"policy_v2", "default_route", "default_reason"}
    if not rows or not expected.issubset(rows[0]):
        raise ValueError(f"{SOURCE} must contain columns {sorted(expected)}")
    return rows


def collect(rows: list[dict[str, str]], default_only: bool = False):
    cells: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    for row in rows:
        if default_only and row["default_route"].lower() != "y":
            continue
        key = component_key(row["harness"])
        if row["failure_type"] not in FAILURES:
            continue
        code, full, family, _ = policy_details(row["policy_v2"])
        entry = (code, full, family)
        if entry not in cells[(key, row["failure_type"] )]:
            cells[(key, row["failure_type"])].append(entry)
    return cells


def write_markdown(rows: list[dict[str, str]]) -> None:
    cells = collect(rows)
    lines = [
        "# Harness failure-handling matrix (split routes)",
        "",
        "Cells show all audited routes from `policy_v2`. `R→` means retry before the displayed policy; multiple codes denote split routes. `n/a` means not audited.",
        "",
        "| Harness component | " + " | ".join(FAILURES) + " |",
        "|---|" + "---:|" * len(FAILURES),
    ]
    for key, label in COMPONENTS:
        values = []
        for failure in FAILURES:
            entries = cells.get((key, failure), [])
            values.append(" / ".join(f"`{code}`" for code, _, _ in entries) if entries else "n/a")
        lines.append("| " + label + " | " + " | ".join(values) + " |")
    lines.extend([
        "",
        "## Code key",
        "",
        "| Code | Policy |",
        "|---|---|",
        "| NEG / POS / RAND | Imputed: absent / present / random |",
        "| GRADE | Graded as output |",
        "| DROP-S / DROP-R | Dropped (silent) / (reported) |",
        "| SEP / ABORT | Separate outcome / Abort |",
        "| R→X | Retry before policy X |",
        "",
        "The default-route matrix selects the row marked `default_route=y` for each component and failure type. See `audit_table_v2.csv` for each row's `default_reason`.",
        "",
    ])
    (FIGURES / "audit_matrix_full.md").write_text("\n".join(lines), encoding="utf-8")


def render(rows: list[dict[str, str]], *, default_only: bool) -> None:
    cells = collect(rows, default_only=default_only)
    suffix = "main" if default_only else "full"
    active_components = [(key, name) for key, name in COMPONENTS if any(k == key for k, _ in cells)]
    # Main artwork is sized at 8 cm wide; compact wrapped text keeps every
    # component, failure label, color and policy readable at that size.
    width = 3.15 if default_only else 10.4
    height = 4.335 if default_only else 10.0
    fig, ax = plt.subplots(figsize=(width, height), constrained_layout=False)
    left, right, top, bottom = (0.31, 0.985, 0.92, 0.1) if default_only else (0.27, 0.99, 0.94, 0.15)
    ax.set_position([left, bottom, right - left, top - bottom])
    ax.set_xlim(0, len(FAILURES))
    row_heights = {}
    for key, _ in active_components:
        row_heights[key] = max(1, max((len(cells.get((key, f), [])) for f in FAILURES), default=1)) if not default_only else 1
    row_starts = {}
    cursor = 0
    for key, _ in active_components:
        row_starts[key] = cursor
        cursor += row_heights[key]
    ax.set_ylim(cursor, 0)
    ax.set_xticks([i + 0.5 for i in range(len(FAILURES))], FAILURES)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=3, labelsize=5.2 if default_only else 9)
    ax.tick_params(axis="y", length=0, pad=3, labelsize=4.4 if default_only else 9)
    ylabels = {
        "inspect_evals / MASK": "inspect_evals /\nMASK",
        "inspect_evals / AgentHarm": "inspect_evals /\nAgentHarm",
        "inspect_evals / StrongREJECT": "inspect_evals /\nStrongREJECT",
        "inspect_evals / TheAgentCompany": "inspect_evals /\nTheAgentCompany",
        "PyRIT (attack components)": "PyRIT / attack\ncomponents",
        "promptfoo / red-team": "promptfoo /\nred-team",
        "promptfoo / evals": "promptfoo / evals",
    }
    ax.set_yticks([row_starts[key] + row_heights[key] / 2 for key, _ in active_components], [ylabels.get(name, name) for _, name in active_components])
    for spine in ax.spines.values():
        spine.set_visible(False)

    for key, _ in active_components:
        row_start = row_starts[key]
        row_height = row_heights[key]
        for x, failure in enumerate(FAILURES):
            entries = cells.get((key, failure), [])
            if not entries:
                ax.add_patch(plt.Rectangle((x, row_start), 1, row_height, facecolor="#F3F3F3", edgecolor="white", linewidth=0.65))
                ax.text(x + 0.5, row_start + row_height / 2, "n/a", ha="center", va="center", color="#666666", fontsize=5 if default_only else 9)
                continue
            n = len(entries)
            for j, (_, full, family) in enumerate(entries):
                sub_y = row_start + j * row_height / n
                sub_height = row_height / n
                ax.add_patch(plt.Rectangle((x, sub_y), 1, sub_height, facecolor=COLORS[family], edgecolor="white", linewidth=0.65))
                label = full if default_only else full
                label = label.replace("Retry → ", "R→ ")
                ax.text(
                    x + 0.5,
                    sub_y + sub_height / 2,
                    wrapped_label(label),
                    ha="center",
                    va="center",
                    color=TEXT_COLORS[family],
                    fontsize=3.05 if default_only else (5.7 if n == 1 else 5.2),
                    linespacing=0.95,
                    clip_on=True,
                )
    if not default_only:
        fig.suptitle("Failure handling by harness component (all audited routes)", x=left, y=0.985, ha="left", fontsize=14, fontweight="bold")
    legend_labels = {
        "absent": "Imputed: absent",
        "present": "Imputed: present",
        "random": "Random",
        "grade": "Graded as output",
        "dropped": "Dropped",
        "separate": "Separate outcome",
        "abort": "Abort",
    }
    present_families = {family for entries in cells.values() for _, _, family in entries}
    legend_items = [(family, legend_labels[family]) for family in legend_labels if family in present_families]
    legend = [Patch(facecolor=COLORS[k], label=label, edgecolor="none") for k, label in legend_items]
    fig.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.012 if default_only else 0.025),
        ncol=4 if default_only else 4,
        frameon=False,
        fontsize=3.6 if default_only else 8,
        handlelength=0.7,
        handleheight=0.65,
        columnspacing=0.75,
        labelspacing=0.35,
    )
    fig.savefig(FIGURES / f"audit_matrix_{suffix}.png", dpi=500 if default_only else 220, facecolor="white")
    fig.savefig(FIGURES / f"audit_matrix_{suffix}.pdf", facecolor="white")
    plt.close(fig)


WIDE_COLS = {
    "inspect_ai": "Inspect", "inspect_evals/mask": "MASK\n(inspect_\nevals)", "inspect_evals/agentharm": "Agent-\nHarm",
    "inspect_evals/strong_reject": "Strong-\nREJECT", "inspect_evals/theagentcompany": "TheAgent-\nCompany",
    "darkbench": "Dark-\nBench", "harmbench": "Harm-\nBench", "pyrit": "PyRIT", "promptfoo-evals": "prompt-\nfoo\nevals",
    "promptfoo-redteam": "prompt-\nfoo red-\nteam", "lm_eval": "lm-eval", "mask_orig": "MASK\n(original)",
}
WIDE_ROWS = {"F1": "F1 provider error", "F2": "F2 content filter", "F3": "F3 empty answer",
             "F4": "F4 judge call error", "F5": "F5 judge unparseable", "F6": "F6 judge refuses"}
WIDE_WORD = {"absent": "absent", "present": "present", "grade": "graded", "dropped": "dropped",
             "separate": "separate", "abort": "abort", "random": "random"}


def render_wide(rows: list[dict[str, str]]) -> None:
    """Default routes, transposed (failure types x components) so it fits across a page."""
    cells = collect(rows, default_only=True)
    cols = [key for key, _ in COMPONENTS]
    fig, ax = plt.subplots(figsize=(7.0, 3.5))
    for x, key in enumerate(cols):
        for y, f in enumerate(FAILURES):
            entries = cells.get((key, f), [])
            if not entries:
                ax.add_patch(plt.Rectangle((x, y), 1, 1, facecolor="#F3F3F3", edgecolor="white", linewidth=1.2))
                ax.text(x + 0.5, y + 0.5, "n/a", ha="center", va="center", fontsize=7, color="#9A9A9A")
                continue
            code, _, family = entries[0]  # default route: exactly one entry per cell
            ax.add_patch(plt.Rectangle((x, y), 1, 1, facecolor=COLORS[family], edgecolor="white", linewidth=1.2))
            word = ("R→ " if code.startswith("R→") else "") + WIDE_WORD[family]
            ax.text(x + 0.5, y + 0.5, word.replace("R→ ", "R→\n"), ha="center", va="center", fontsize=6.9,
                    color=TEXT_COLORS[family], linespacing=1.0)
    ax.set_xlim(0, len(cols)); ax.set_ylim(len(FAILURES), 0)
    ax.set_xticks([i + 0.5 for i in range(len(cols))], [WIDE_COLS[k] for k in cols], fontsize=6.6)
    ax.xaxis.tick_top()
    ax.set_yticks([i + 0.5 for i in range(len(FAILURES))], [WIDE_ROWS[f] for f in FAILURES], fontsize=8.6)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    used = sorted({fam for es in cells.values() for _, _, fam in es},
                  key=["absent", "grade", "present", "random", "dropped", "separate", "abort"].index)
    names = {"absent": "imputed as absent", "present": "imputed as present", "grade": "graded as if model output",
             "dropped": "dropped", "separate": "separate ERROR outcome", "abort": "run aborts", "random": "random answer"}
    fig.legend(handles=[Patch(facecolor=COLORS[k], label=names[k]) for k in used], loc="lower center",
               ncol=3, frameon=False, fontsize=7.8, handlelength=1.1, columnspacing=1.4, bbox_to_anchor=(0.58, -0.01))
    fig.subplots_adjust(left=0.205, right=0.995, top=0.78, bottom=0.15)
    fig.savefig(FIGURES / "audit_matrix_wide.png", dpi=400, facecolor="white")
    fig.savefig(FIGURES / "audit_matrix_wide.pdf", facecolor="white")
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    write_markdown(rows)
    render(rows, default_only=False)
    render(rows, default_only=True)
    render_wide(rows)
    print("Wrote figures/audit_matrix_full.{png,pdf,md}, audit_matrix_main.{png,pdf} and audit_matrix_wide.{png,pdf}")


if __name__ == "__main__":
    main()
