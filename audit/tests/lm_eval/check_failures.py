"""Offline checks of lm_eval failure handling. No network, no keys.
Run: .venv/bin/python -I check_failures.py <path-to-repos/lm_eval>
"""
import importlib.util
import json
import sys
import time
import types

REPO = sys.argv[1]
# Stub the package root so lm_eval/__init__.py (needs installed metadata) is skipped.
pkg = types.ModuleType("lm_eval")
pkg.__path__ = [f"{REPO}/lm_eval"]
sys.modules["lm_eval"] = pkg

import requests  # noqa: E402

from lm_eval.api.metrics import exact_match_hf_evaluate  # noqa: E402
from lm_eval.filters.extraction import RegexFilter  # noqa: E402
from lm_eval.models import api_models  # noqa: E402
from lm_eval.models.anthropic_llms import AnthropicChat, AnthropicLM  # noqa: E402
from lm_eval.models.openai_completions import LocalChatCompletion  # noqa: E402
from lm_eval.models.utils import Collator  # noqa: E402

GSM_IGNORE = [",", "\\$", "(?s).*#### ", "\\.$"]


def show(name, value):
    print(f"[{name}] {value!r}")


# ---- T1/T2: regex extraction + exact_match (gsm8k config) ----
strict = RegexFilter(regex_pattern=r"#### (\-?[0-9\.\,]+)")
flex = RegexFilter(regex_pattern=r"(-?[$0-9.,]{2,})|(-?[0-9]+)", group_select=-1)
for resp in ["", "I'm sorry, I can't help with that.", "The answer is 18.\n#### 18"]:
    s = strict.apply([[resp]], [{}])[0][0]
    f = flex.apply([[resp]], [{}])[0][0]
    em = exact_match_hf_evaluate([s], ["18"], regexes_to_ignore=GSM_IGNORE, ignore_case=True)
    show(f"T1 regex resp={resp[:20]!r}", {"strict": s, "flexible": f, "em_strict": float(em["exact_match"])})
show("T1 regex non-str (None) resp", strict.apply([[None]], [{}])[0][0])
em_all = exact_match_hf_evaluate(["[invalid]", "18"], ["18", "18"], regexes_to_ignore=GSM_IGNORE, ignore_case=True)
show("T2 exact_match mean over [invalid]+correct (denominator 2?)", float(em_all["exact_match"]))


# ---- helpers ----
class Req:
    def __init__(self, ctx, gk):
        self.args = (ctx, gk)


def make_chat(cls=LocalChatCompletion):
    m = cls(base_url="http://127.0.0.1:9/v1/chat/completions", model="fake",
            tokenizer_backend=None, tokenized_requests=False, max_retries=3)
    return m


class FakeResp:
    def __init__(self, status, body):
        self.status_code = status
        self.ok = status < 400
        self.text = json.dumps(body)
        self._body = body

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"{self.status_code} {self.text}")

    def json(self):
        return self._body


def run_sync(model, post_fn):
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        return post_fn()

    api_models.requests.post = fake_post
    t0 = time.time()
    try:
        ctx = api_models.JsonChatStr(json.dumps([{"role": "user", "content": "Q: 1+1?"}]))
        out = model.generate_until([Req(ctx, {"until": ["\n"]})])
        return ("returned", out, calls["n"], round(time.time() - t0, 1))
    except BaseException as e:  # noqa: BLE001
        return ("raised", f"{type(e).__name__}: {str(e)[:120]}", calls["n"], round(time.time() - t0, 1))


chat = make_chat()

# ---- T3: F1 provider exception (HTTP 500 / timeout) through real model_call + tenacity ----
show("T3 F1 HTTP 500", run_sync(chat, lambda: FakeResp(500, {"error": "server"})))


def boom():
    raise requests.Timeout("read timed out")


show("T3 F1 timeout", run_sync(chat, boom))

# ---- T4: F2 content filter ----
azure_400 = {"error": {"code": "content_filter", "message": "The response was filtered", "status": 400}}
show("T4 F2 HTTP 400 content_filter", run_sync(chat, lambda: FakeResp(400, azure_400)))
cf_200 = {"choices": [{"index": 0, "finish_reason": "content_filter", "message": {"role": "assistant", "content": None}}]}
show("T4 F2 200 finish_reason=content_filter content=None", run_sync(chat, lambda: FakeResp(200, cf_200)))
cf_200_nomsg = {"choices": [{"index": 0, "finish_reason": "content_filter"}]}
show("T4 F2 200 content_filter, no message key", run_sync(chat, lambda: FakeResp(200, cf_200_nomsg)))
refusal = {"choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": None, "refusal": "I can't help with that."}}]}
show("T4 F2 200 SDK refusal field, content=None", run_sync(chat, lambda: FakeResp(200, refusal)))

# ---- T5: F3 empty response ----
empty = {"choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": ""}}]}
show("T5 F3 content ''", run_sync(chat, lambda: FakeResp(200, empty)))

# ---- T6: anthropic-chat (TemplateAPI) refusal with empty content list ----
try:
    import os
    os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-not-used")
    anth = AnthropicChat(base_url="http://127.0.0.1:9/v1/messages", model="fake",
                         tokenizer_backend=None, tokenized_requests=False, max_retries=3)
    anth_refusal = {"content": [], "stop_reason": "refusal"}
    show("T6 anthropic-chat stop_reason=refusal content=[]", run_sync(anth, lambda: FakeResp(200, anth_refusal)))
    show("T6 anthropic-chat HTTP 400", run_sync(anth, lambda: FakeResp(400, {"type": "error", "error": {"type": "invalid_request_error"}})))
except Exception as e:  # noqa: BLE001
    show("T6 setup failed", f"{type(e).__name__}: {e}")

# ---- T7: legacy anthropic-completions: break on APIStatusError -> short list ----
fake_anthropic = types.ModuleType("anthropic")


class APIConnectionError(Exception):
    pass


class APIStatusError(Exception):
    def __init__(self, msg, status_code=400):
        super().__init__(msg)
        self.status_code = status_code
        self.message = msg


class RateLimitError(Exception):
    pass


fake_anthropic.APIConnectionError = APIConnectionError
fake_anthropic.APIStatusError = APIStatusError
fake_anthropic.RateLimitError = RateLimitError
fake_anthropic.HUMAN_PROMPT, fake_anthropic.AI_PROMPT = "\n\nHuman:", "\n\nAssistant:"
sys.modules["anthropic"] = fake_anthropic


class FakeCompletions:
    def __init__(self):
        self.n = 0

    def create(self, **k):
        self.n += 1
        if self.n == 2:
            raise APIStatusError("content blocked", 400)
        return types.SimpleNamespace(completion="ok")


legacy = AnthropicLM.__new__(AnthropicLM)
legacy.client = types.SimpleNamespace(completions=FakeCompletions())
legacy.model, legacy.temperature, legacy.kwargs = "fake", 0.0, {}
legacy.max_tokens_to_sample = 16
from lm_eval.api.model import CacheHook  # noqa: E402

legacy.cache_hook = CacheHook(None)
reqs = [Req(f"Q{i}", {"until": ["\n"]}) for i in range(3)]
try:
    out = legacy.generate_until(reqs, disable_tqdm=True)
    show("T7 legacy anthropic: len(out) vs len(reqs)", (out, len(out), len(reqs)))
    try:  # evaluator.py:603 does this
        list(zip(out, reqs, strict=True))
        show("T7 evaluator zip", "ok")
    except ValueError as e:
        show("T7 evaluator zip(strict=True)", f"ValueError: {e}")
except BaseException as e:  # noqa: BLE001
    show("T7 legacy raised", f"{type(e).__name__}: {e}")

# ---- T8: pisa LLM judge ----
spec = importlib.util.spec_from_file_location("pisa_utils", f"{REPO}/lm_eval/tasks/pisa/utils.py")
pisa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pisa)
os.environ["OPENAI_API_KEY"] = "dummy-not-used"


def judge_with(content=None, exc=None):
    class Client:
        def __init__(self, **k):
            def create(**kw):
                if exc:
                    raise exc
                msg = types.SimpleNamespace(content=content)
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=create))
    pisa.OpenAI = Client
    try:
        return pisa.judge_mcq("B", ["A) x", "B) y"], "B) y")
    except BaseException as e:  # noqa: BLE001
        return f"raised {type(e).__name__}: {e}"


show("T8 judge '1'", judge_with("1"))
show("T8 judge unparseable 'Correct'", judge_with("Correct"))
show("T8 judge refusal text 'I'", judge_with("I"))
show("T8 judge content None (SDK refusal)", judge_with(None))
show("T8 judge exception", judge_with(exc=RuntimeError("APIConnectionError after SDK retries")))
# non-judged pisa: empty response -> random choice
import random  # noqa: E402

random.seed(0)
hits = sum(pisa.pisa_process_results({"choices": "['a','b','c','d']", "answer": 1}, [""])["acc"] for _ in range(400))
show("T9 pisa (non-judged) empty response acc over 400 trials", hits / 400)
