"""StrongREJECT: every judge reply unparseable -> what headline metrics show."""
import json
from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.solver import generate
from inspect_evals.strong_reject.scorer import strong_reject_scorer

j = get_model("mockllm/model", custom_outputs=lambda *a: ModelOutput.from_content("mockllm", "garbage"), memoize=False)
task = Task(dataset=[Sample(id=i, input=f"q{i}") for i in range(2)], solver=generate(), scorer=strong_reject_scorer(judge_model=j))
log = eval(task, model="mockllm/model", log_dir="logs", display="none")[0]
print(json.dumps({"status": log.status, "scores": [{"unscored": s.unscored_samples, "scored": s.scored_samples, "metrics": {k: m.value for k, m in s.metrics.items()}} for s in log.results.scores]}))
