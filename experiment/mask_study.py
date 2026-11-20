"""MASK study: how often does the judge fail in a real inspect_evals MASK run, and what does that do to the score?

Run with the inspect venv (it has inspect_ai and inspect_evals 0.29.0):

  PY=audit/tests/inspect/.venv/bin/python
  $PY experiment/mask_study.py rescore <judge> <max_tokens> <tag> [model ...]   # re-judge the default runs' answers
  $PY experiment/mask_study.py analyze                                         # -> data/derived/mask_study.{csv,md}

Step 1 (experiment/run_mask_all.sh) generates answers and judges them with MASK's default judge settings
(500 output tokens, temperature 1, reasoning effort low). Re-scoring keeps the same answers and changes only the
judge, so differences come from the judge setting, not from new answers (the judge still samples at temperature 1).

Honesty as inspect_evals reports it: 1 - lies / all samples, so judge errors count as "not a lie"
(mask/metrics/core.py:124-139). Accuracy: correct / samples, so judge errors count as incorrect (core.py:142-163).
"""
import glob
import os
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "data/raw/mask_logs"
OUT = ROOT / "data/derived"
MODELS = ["deepseek-v4-flash", "gemma-4-31b-it", "qwen3.8-27b"]


def latest(tag):
    files = sorted(glob.glob(str(LOGS / tag / "*.eval")))
    return files[-1] if files else None


def rescore(judge, max_tokens, tag, models):
    load_dotenv(ROOT / ".env")
    os.environ.setdefault("ADAPTION_BASE_URL", "https://api.prod.adaptionlabs.ai/api/v1")
    from inspect_ai import score
    from inspect_ai.log import read_eval_log, write_eval_log
    from inspect_ai.model import GenerateConfig, ModelOutput
    from inspect_evals.mask import defaults
    from inspect_evals.mask.scorer import build_accuracy_and_honesty_scorer
    from inspect_evals.mask.types import MetadataKey, NoBeliefConsistencyHandling, QuestionArchetype

    j = f"openai-api/adaption/{judge}"
    scorer = build_accuracy_and_honesty_scorer(include_core=True, include_statistical_summary=False,
                                               include_normalisation=False, include_stratification=False)(
        honesty_at_n=defaults.HONESTY_AT_N, binary_judge_model=j, numeric_judge_model=j,
        numeric_tol=defaults.NUMERIC_TOLERANCE,
        no_belief_handling=NoBeliefConsistencyHandling(defaults.NO_BELIEF_HANDLING),
        judge_config=GenerateConfig(max_tokens=max_tokens, temperature=defaults.JUDGE_TEMPERATURE,
                                    reasoning_effort=defaults.JUDGE_REASONING_EFFORT, max_connections=5))
    for m in models:
        src = latest(f"default_{m}")
        if src is None:
            print("no default log for", m)
            continue
        dst = LOGS / f"{tag}_{m}" / Path(src).name
        if dst.exists():
            print("exists, skipping", dst)
            continue
        log = read_eval_log(src)
        for s in log.samples:  # the log stores the archetype as a plain string; the scorer needs the enum
            s.metadata[MetadataKey.CONFIG] = QuestionArchetype(s.metadata[MetadataKey.CONFIG])
            for k, v in s.store.items():  # and the stored answers as dicts; the scorer needs ModelOutput
                if isinstance(v, list):
                    s.store[k] = [ModelOutput.model_validate(x) if isinstance(x, dict) else x for x in v]
        log = score(log, scorers=[scorer], action="overwrite", display="none")
        dst.parent.mkdir(parents=True, exist_ok=True)
        write_eval_log(log, str(dst))
        print("wrote", dst)


def text_of(x):
    """Answer text of a stored model output (a dict once read back from a log), without reasoning."""
    if not isinstance(x, dict):
        return (x.completion or "").strip()
    c = ((x.get("choices") or [{}])[0].get("message") or {}).get("content")
    if isinstance(c, list):
        c = " ".join(p.get("text", "") for p in c if isinstance(p, dict) and p.get("type") == "text")
    return (c or "").strip()


def summarise(path, setting, model):
    from inspect_ai.log import read_eval_log
    log = read_eval_log(path)
    hon, acc, errored = Counter(), Counter(), 0
    empty_hon, belief_empty, belief_n = Counter(), 0, 0  # verdicts on samples whose pressured answer was empty
    for s in log.samples:
        if s.error or not s.scores:
            errored += 1
            continue
        v = next(iter(s.scores.values())).value
        hon[v["honesty"]] += 1
        acc[v["accuracy"]] += 1
        if any(not text_of(x) for x in s.store.get("pressured_responses") or []):
            empty_hon[v["honesty"]] += 1
        for k in ("belief_elicit_1_responses", "belief_elicit_2_and_3_responses"):
            for x in s.store.get(k) or []:
                belief_n += 1
                belief_empty += not text_of(x)
    n = sum(hon.values())
    if n == 0:  # a run still in progress
        return None
    lies, err = hon["lie"], hon["error"]
    acc_n = n - acc["no-belief-elicitation-done"]
    return {"setting": setting, "model": model, "samples": n, "sample_errors": errored,
            "honest": hon["honest"], "lie": lies, "evade": hon["evade"], "no_belief": hon["no-belief"],
            "judge_error": err, "judge_error_rate": err / n if n else float("nan"),
            "honesty_reported": 1 - lies / n, "honesty_errors_excluded": 1 - lies / (n - err) if n > err else float("nan"),
            "honesty_errors_as_lies": 1 - (lies + err) / n,
            "accuracy_error": acc["error"], "accuracy_reported": acc["correct"] / acc_n if acc_n else float("nan"),
            "accuracy_errors_excluded": acc["correct"] / (acc_n - acc["error"]) if acc_n > acc["error"] else float("nan"),
            "pressured_empty": sum(empty_hon.values()), "empty_judged_lie": empty_hon["lie"],
            "empty_judged_honest": empty_hon["honest"], "empty_judged_evade": empty_hon["evade"],
            "honesty_answered_only": 1 - (lies - empty_hon["lie"]) / (n - sum(empty_hon.values()))
            if n > sum(empty_hon.values()) else float("nan"),
            "belief_empty_share": belief_empty / belief_n if belief_n else float("nan")}


def analyze():
    rows = []
    for d in sorted(LOGS.iterdir()):
        if not d.is_dir() or d.name == "pilot":
            continue
        setting, _, model = d.name.partition("_")
        p = latest(d.name)
        row = summarise(p, setting, model) if p else None
        if row:
            rows.append(row)
    df = pd.DataFrame(rows).sort_values(["setting", "model"])
    df.to_csv(OUT / "mask_study.csv", index=False)
    cols = ["setting", "model", "samples", "judge_error", "judge_error_rate", "lie", "honesty_reported",
            "honesty_errors_excluded", "honesty_errors_as_lies", "accuracy_error", "accuracy_reported",
            "accuracy_errors_excluded", "pressured_empty", "empty_judged_lie", "empty_judged_honest",
            "empty_judged_evade", "honesty_answered_only", "belief_empty_share"]
    text = ["# MASK study (inspect_evals 0.29.0, Adaption-hosted models)", "",
            "Generated by `experiment/mask_study.py analyze`. `honesty_reported` is what inspect_evals reports "
            "(judge errors count as not a lie); `honesty_errors_excluded` drops them; `honesty_errors_as_lies` is "
            "the worst case. Accuracy counts judge errors as incorrect. `pressured_empty` = samples whose pressured "
            "answer was empty (the judge still grades them); `honesty_answered_only` excludes those samples.", "",
            "```", df[cols].round(3).T.to_string(header=False), "```", ""]
    (OUT / "mask_study.md").write_text("\n".join(text))
    print("\n".join(text))


def _self_test():
    # 2 lies, 1 error, 1 honest out of 4: reported 0.5, excluded 1/3 lies -> 0.667, worst 0.25
    n, lies, err = 4, 2, 1
    assert (1 - lies / n, round(1 - lies / (n - err), 3), 1 - (lies + err) / n) == (0.5, 0.333, 0.25)


if __name__ == "__main__":
    _self_test()
    if sys.argv[1] == "rescore":
        rescore(sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5:] or MODELS)
    else:
        analyze()
