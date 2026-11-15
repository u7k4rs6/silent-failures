"""Probe HarmBench API wrappers + classifier label parsing with stubs (no network, no torch/vllm).
Run: python3 -P audit/tests/harmbench/test_failures.py
SDKs, spacy and datasketch are stubbed; only api_models.py and eval_utils.compute_results_classifier are exercised.
"""
import os, sys, types, importlib.util
from types import SimpleNamespace as NS

HB = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../repos/harmbench"))


def mod(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m


class OpenAIError(Exception): pass
class APIError(Exception): pass
class BadRequestError(APIError): pass  # mirrors anthropic's hierarchy

mod("openai", OpenAI=lambda **kw: None, OpenAIError=OpenAIError)
mod("anthropic", Anthropic=lambda **kw: None, HUMAN_PROMPT="\n\nHuman:", AI_PROMPT="\n\nAssistant:",
    BadRequestError=BadRequestError, APIError=APIError)
mod("google"); mod("google.generativeai", configure=lambda **kw: None)
mod("mistralai"); mod("mistralai.client", MistralClient=lambda **kw: None)
mod("mistralai.models"); mod("mistralai.models.chat_completion", ChatMessage=lambda **kw: kw)
mod("spacy", load=lambda name: NS()); mod("datasketch", MinHash=object)


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HB, name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


api, eu = load("api_models"), load("eval_utils")
api.time.sleep = lambda s: None  # skip 10s retry sleeps


def raiser(exc):
    def f(**kw): raise exc
    return f


def openai_returning(content):
    return lambda **kw: NS(choices=[NS(message=NS(content=content))])


print("== GPT._generate ==")
for label, create in [
    ("F1 persistent OpenAIError (503/timeout)", raiser(OpenAIError("Error code: 503"))),
    ("F2 HTTP 400 content_filter", raiser(OpenAIError("Error code: 400 - {'code': 'content_filter'}"))),
    ("F2/F3 content=None (finish_reason=content_filter)", openai_returning(None)),
    ("F3 empty string", openai_returning("")),
]:
    g = object.__new__(api.GPT); g.model_name = "gpt-x"
    g.client = NS(chat=NS(completions=NS(create=create)))
    print(f"  {label:50} -> {g._generate('p', 10, 0.0, 1.0)!r}")

print("== Claude._generate ==")
for label, create in [
    ("F2 'Output blocked by content filtering policy'", raiser(BadRequestError("Output blocked by content filtering policy"))),
    ("F1 other 400 BadRequestError", raiser(BadRequestError("Error code: 400 - invalid_request"))),
    ("F1 persistent APIError (529 overloaded)", raiser(APIError("Error code: 529"))),
]:
    c = object.__new__(api.Claude); c.model_name = "claude-x"
    c.model = NS(completions=NS(create=create))
    print(f"  {label:50} -> {c._generate('p', 10, 0.0, 1.0)!r}")

print("== Mistral._generate with a HEALTHY client ==")
m = api.Mistral("mistral-small", "tok")
m.client = NS(chat=lambda **kw: NS(choices=[NS(message=NS(content="real answer"))]))
print(f"  {'healthy client':50} -> {m._generate('p', 10, 0.0, 1.0)!r}")

print("== compute_results_classifier label parsing (fake cls) ==")
preds = ["Yes", "No", "yes", " Yes", "Yes.", "", "I", "No"]
cls = NS(generate=lambda inputs, params, use_tqdm=False: [NS(outputs=[NS(text=p)]) for p in preds])
behavior = {"BehaviorID": "b1", "Behavior": "do harm", "Tags": ""}
data = [{"test_case": "t", "generation": g} for g in ["harmful", "refusal", "harmful", "harmful", "harmful", "x", "x", "$ERROR$"]]
res = eu.compute_results_classifier(behavior, data, cls, None)
for p, d in zip(preds, res):
    print(f"  classifier output {p!r:8} -> label {d['label']:>2}")
labels = [d["label"] for d in res]
# evaluate_completions.py:91 is `np.mean([d['label'] == 1 for d in data])`; evaluated here on the labels above
print("  ASR per evaluate_completions.py:91 formula:", sum(l == 1 for l in labels) / len(labels),
      f"(denominator {len(labels)}, of which label=-1: {labels.count(-1)})")

print("== GPTV._generate: `except openai.InvalidRequestError` (absent in openai>=1.0; stub mirrors that) ==")
v = object.__new__(api.GPTV); v.model_name = "gpt-4-vision-preview"
v.client = NS(chat=NS(completions=NS(create=raiser(OpenAIError("Error code: 503")))))
try:
    print("  ->", repr(v._generate("p", os.devnull, 10, 0.0, 1.0)))
except Exception as e:
    print(f"  F1 transient OpenAIError -> run aborts: {type(e).__name__}: {e}")

print("== compute_results_advbench (optional --include_advbench_metric) on failure placeholders ==")
gens = ["$ERROR$", "", "I'm sorry, but I cannot assist with that request."]
r = eu.compute_results_advbench([{} for _ in gens], [{"generation": g} for g in gens])
for g, x in zip(gens, r):
    print(f"  generation {g!r:55} -> advbench_label {x['advbench_label']} (1 = jailbroken)")
