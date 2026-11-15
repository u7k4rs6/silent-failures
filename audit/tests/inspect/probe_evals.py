"""Inject judge failures into inspect_evals scorers (AgentHarm, StrongREJECT, MASK) via mockllm."""

import asyncio
import json

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.solver import generate


def judge(kind):
    def fn(input, tools, tool_choice, config):
        if kind == "raise":
            raise RuntimeError("simulated judge outage")
        if kind == "garbage":
            return ModelOutput.from_content("mockllm", "Verdict: looks fine to me")
        if kind == "refuse":
            return ModelOutput.from_content("mockllm", "I can't help with grading this content.", stop_reason="content_filter")
        if kind == "sr_ok":
            return ModelOutput.from_content("mockllm", "#overall_reasoning ok\n#scores\n1.a x\n1.b 1\n2.a x\n2.b 5\n3.a x\n3.b 5")
    return get_model("mockllm/model", custom_outputs=fn, memoize=False)


# --- AgentHarm refusal judge ---
from inspect_evals.agentharm.scorer import RefusalJudgeLLM

for kind in ["raise", "garbage", "refuse"]:
    rj = RefusalJudgeLLM(judge_model=judge(kind))
    refusal, expl = asyncio.run(rj.check_refusal("Sure, here is how to do it."))
    print(json.dumps({"agentharm_check_refusal": kind, "refusal": refusal, "explanation": expl[:70]}))

# --- AgentHarm semantic judge (harm-score component) ---
from inspect_evals.agentharm.benchmark.grading_utils import semantic_judge

for kind in ["garbage", "refuse"]:
    r = asyncio.run(semantic_judge("Is this on topic?", "some answer", judge(kind)))
    print(json.dumps({"agentharm_semantic_judge": kind, "returned": r, "counts_as_pass": r == "pass"}))

# --- StrongREJECT: 2-sample eval, sample "ok" judged normally, "bad" gets failing judge ---
from inspect_evals.strong_reject.scorer import strong_reject_scorer


def sr_run(kind, **kw):
    def fn(input, tools, tool_choice, config):
        if "BADSAMPLE" in input[-1].text:
            return judge(kind).api.outputs(input, tools, tool_choice, config)
        return judge("sr_ok").api.outputs(input, tools, tool_choice, config)
    j = get_model("mockllm/model", custom_outputs=fn, memoize=False)
    task = Task(dataset=[Sample(id="ok", input="OKSAMPLE"), Sample(id="bad", input="BADSAMPLE")],
                solver=generate(), scorer=strong_reject_scorer(judge_model=j))
    log = eval(task, model="mockllm/model", log_dir="logs", display="none", **kw)[0]
    out = {"strong_reject_judge": kind, "status": log.status, "kw": kw}
    if log.results:
        out["completed"] = log.results.completed_samples
        out["scores"] = [{"unscored": s.unscored_samples, "scored": s.scored_samples,
                          "metrics": {k: m.value for k, m in s.metrics.items()}} for s in log.results.scores]
    out["samples"] = [{"id": s.id, "error": (s.error.message[:50] if s.error else None),
                       "score": {k: (v.value, v.reason) for k, v in (s.scores or {}).items()}} for s in log.samples]
    print(json.dumps(out, default=str))


sr_run("garbage")
sr_run("refuse")
sr_run("raise", fail_on_error=False)

# --- MASK: parse failure -> ERROR; how headline honesty treats ERROR ---
from inspect_evals.mask.judge_estimate.parse import parse_belief, parse_statement
from inspect_evals.mask.metrics.core import calculate_honesty_score
from inspect_evals.mask.types import Honesty, QuestionType

print(json.dumps({"mask_parse_statement_garbage": str(parse_statement("Verdict: looks fine", QuestionType.BINARY).value),
                  "mask_parse_belief_refusal": str(parse_belief("I can't help with that.", QuestionType.BINARY).value)}))
print(json.dumps({"mask_honesty[HONEST,LIE]": calculate_honesty_score([Honesty.HONEST, Honesty.LIE]),
                  "mask_honesty[ERROR,LIE]": calculate_honesty_score([Honesty.ERROR, Honesty.LIE]),
                  "mask_honesty[ERROR,ERROR]": calculate_honesty_score([Honesty.ERROR, Honesty.ERROR])}))
