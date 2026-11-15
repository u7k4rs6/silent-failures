"""Apply the reporting standard (experiment/reporting.py) to our DarkBench run.

  python experiment/apply_standard.py  ->  figures/table_standard.md

Outcome mapping: judge label 1 -> fail (dark pattern present), 0 -> pass,
generation failure F1-F3 -> error, judge failure F4-F6 -> undetermined.
"""
from pathlib import Path

import pandas as pd

from reporting import report

ROOT = Path(__file__).resolve().parent.parent
LABEL = {"deepseek-v4-flash": "DeepSeek V4 Flash", "gemma-4-31b-it": "Gemma 4 31B", "qwen3.8-27b": "Qwen 3.8 27B"}


def outcome(row):
    if row.state in ("F1", "F2", "F3", "TR"):
        return "error"
    if row.state in ("F4", "F5", "F6"):
        return "undetermined"
    assert row.state == "ok", row.state
    return "fail" if row.label == 1 else "pass"


def main():
    df = pd.read_csv(ROOT / "data/derived/items.csv")
    df["outcome"] = df.apply(outcome, axis=1)
    lines = ["| Model | Scope | PASS | FAIL | ERROR | UNDET. | Coverage | Score (valid) | [Lower, Upper] |",
             "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for scope in ("overall", "brand-bias", "sycophancy"):
        for m in LABEL:
            d = df[df.model == m] if scope == "overall" else df[(df.model == m) & (df.category == scope)]
            r = report(d.outcome.tolist())
            c = r["counts"]
            lines.append(f"| {LABEL[m]} | {scope} | {c['PASS']} | {c['FAIL']} | {c['ERROR']} | {c['UNDETERMINED']} | "
                         f"{r['coverage']:.3f} | {r['score_valid']:.3f} | [{r['lower_bound']:.3f}, {r['upper_bound']:.3f}] |")
    out = ROOT / "figures/table_standard.md"
    out.write_text("# Reporting standard applied to the DarkBench run\n\n"
                   "FAIL = dark pattern present. ERROR = generation failed (provider error, filter, empty answer). "
                   "UNDET. = judge failed. Lower bound counts every failure as absent, upper as present.\n\n"
                   + "\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
