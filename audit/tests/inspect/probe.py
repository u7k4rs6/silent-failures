"""Inject F1-F6 failures into Inspect via mockllm; print what the log/metrics record.

No network, no API keys. Each scenario: 2 samples. Sample "ok" behaves normally
(target answered correctly / judge says C); sample "bad" gets the injected failure.
accuracy == 1.0 -> failed sample dropped; 0.5 -> imputed negative; error status -> abort.
"""

import json
import sys

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.scorer import match, model_graded_qa
from inspect_ai.solver import generate

DATA = [Sample(id="ok", input="ok: say 42", target="42"),
        Sample(id="bad", input="bad: say 42", target="42")]


def target_fn(kind):
    def fn(input, tools, tool_choice, config):
        text = input[-1].text
        if text.startswith("ok"):
            return ModelOutput.from_content("mockllm", "42")
        if kind == "raise":
            raise RuntimeError("simulated provider outage (post-retry)")
        if kind == "content_filter":
            # what _openai.py openai_refusal_model_output() builds from an HTTP 400 content_filter
            return ModelOutput.from_content("mockllm", "The response was filtered due to the prompt triggering content management policy.", stop_reason="content_filter")
        if kind == "empty":
            return ModelOutput.from_content("mockllm", "")
        return ModelOutput.from_content("mockllm", "42")
    return fn


def judge_fn(kind):
    def fn(input, tools, tool_choice, config):
        prompt = input[-1].text
        is_bad = "bad: say 42" in prompt
        if not is_bad or kind == "ok":
            return ModelOutput.from_content("mockllm", "GRADE: C")
        if kind == "raise":
            raise RuntimeError("simulated judge outage")
        if kind == "garbage":
            return ModelOutput.from_content("mockllm", "Verdict: looks fine to me")
        if kind == "refuse":
            return ModelOutput.from_content("mockllm", "I can't help with grading this content.", stop_reason="content_filter")
        if kind == "empty":
            return ModelOutput.from_content("mockllm", "")
        if kind == "echo":  # judge grades whatever the target produced; for empty/filtered answers say I
            return ModelOutput.from_content("mockllm", "GRADE: I")
    return fn


def run(name, target_kind, scorer_kind, judge_kind="ok", **eval_kwargs):
    model = get_model("mockllm/model", custom_outputs=target_fn(target_kind))
    if scorer_kind == "match":
        scorer = match()
    else:
        judge = get_model("mockllm/model", custom_outputs=judge_fn(judge_kind), memoize=False)
        scorer = model_graded_qa(model=judge)
    task = Task(dataset=DATA, solver=generate(), scorer=scorer)
    log = eval(task, model=model, log_dir="logs", display="none", **eval_kwargs)[0]
    out = {"scenario": name, "status": log.status,
           "eval_error": (log.error.message[:80] if log.error else None)}
    if log.results:
        out["total_samples"] = log.results.total_samples
        out["completed_samples"] = log.results.completed_samples
        out["scores"] = [{"name": s.name, "scored_samples": s.scored_samples,
                          "unscored_samples": s.unscored_samples,
                          "metrics": {k: m.value for k, m in s.metrics.items()}}
                         for s in log.results.scores]
    out["samples"] = []
    for s in log.samples or []:
        sc = {k: {"value": v.value, "reason": getattr(v, "reason", None),
                  "expl": (v.explanation or "")[:60]} for k, v in (s.scores or {}).items()}
        out["samples"].append({"id": s.id, "completion": s.output.completion[:60] if s.output else None,
                               "stop_reason": (s.output.stop_reason if s.output and s.output.choices else None),
                               "error": (s.error.message[:60] if s.error else None),
                               "scores": sc})
    print(json.dumps(out, default=str))


SCENARIOS = {
    "F1_default": lambda: run("F1 target raises, defaults", "raise", "match"),
    "F1_foe_false": lambda: run("F1 target raises, fail_on_error=False", "raise", "match", fail_on_error=False),
    "F1_retry": lambda: run("F1 target raises, retry_on_error=2, fail_on_error=False", "raise", "match", retry_on_error=2, fail_on_error=False),
    "F2_match": lambda: run("F2 content_filter, match scorer", "content_filter", "match"),
    "F2_judge": lambda: run("F2 content_filter, model_graded_qa (judge says I)", "content_filter", "judge", "echo"),
    "F2_fail_on_refusal": lambda: run("F2 content_filter, fail_on_refusal=True, fail_on_error=False", "content_filter", "match", fail_on_refusal=True, fail_on_error=False),
    "F3_match": lambda: run("F3 empty, match scorer", "empty", "match"),
    "F3_judge": lambda: run("F3 empty, model_graded_qa (judge says I)", "empty", "judge", "echo"),
    "F4_default": lambda: run("F4 judge raises, defaults", "ok", "judge", "raise"),
    "F4_foe_false": lambda: run("F4 judge raises, fail_on_error=False", "ok", "judge", "raise", fail_on_error=False),
    "F5_garbage": lambda: run("F5 judge garbage", "ok", "judge", "garbage"),
    "F5_empty": lambda: run("F5 judge empty", "ok", "judge", "empty"),
    "F6_refuse": lambda: run("F6 judge refuses (content_filter)", "ok", "judge", "refuse"),
}

if __name__ == "__main__":
    for key in (sys.argv[1:] or SCENARIOS):
        SCENARIOS[key]()
