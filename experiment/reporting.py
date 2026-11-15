"""Summarize evaluation outcomes without assigning scores to failures."""

from __future__ import annotations

from collections import Counter
from typing import TypedDict


class Report(TypedDict):
    counts: dict[str, int]
    coverage: float
    score_valid: float | None
    lower_bound: float | None
    upper_bound: float | None


def report(outcomes: list[str]) -> Report:
    """Return outcome counts, valid-score coverage, and conservative bounds.

    ``fail`` means the evaluated behaviour was present. ``pass`` means it was
    absent. Errors and undetermined outcomes are never assigned individual
    scores; they widen the interval from all-failures-absent to all-failures-present.
    For an empty input, coverage is zero and score/bounds are undefined (None).
    """
    allowed = {"pass", "fail", "error", "undetermined"}
    invalid = set(outcomes) - allowed
    if invalid:
        raise ValueError(f"Unsupported outcome(s): {', '.join(sorted(invalid))}")

    counts = Counter(outcomes)
    total = len(outcomes)
    valid = counts["pass"] + counts["fail"]
    coverage = valid / total if total else 0.0

    if total == 0:
        score_valid = lower_bound = upper_bound = None
    else:
        score_valid = counts["fail"] / valid if valid else None
        lower_bound = counts["fail"] / total
        upper_bound = (counts["fail"] + counts["error"] + counts["undetermined"]) / total

    return {
        "counts": {
            "PASS": counts["pass"],
            "FAIL": counts["fail"],
            "ERROR": counts["error"],
            "UNDETERMINED": counts["undetermined"],
        },
        "coverage": coverage,
        "score_valid": score_valid,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
    }


if __name__ == "__main__":
    all_error = report(["error", "error"])
    assert all_error["counts"] == {"PASS": 0, "FAIL": 0, "ERROR": 2, "UNDETERMINED": 0}
    assert all_error["coverage"] == 0.0
    assert all_error["score_valid"] is None
    assert all_error["lower_bound"] == 0.0
    assert all_error["upper_bound"] == 1.0

    mixed = report(["pass", "fail", "error", "undetermined"])
    assert mixed["counts"] == {"PASS": 1, "FAIL": 1, "ERROR": 1, "UNDETERMINED": 1}
    assert mixed["coverage"] == 0.5
    assert mixed["score_valid"] == 0.5
    assert mixed["lower_bound"] == 0.25
    assert mixed["upper_bound"] == 0.75

    print("reporting.py self-test passed")
