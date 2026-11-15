"""Probe original MASK generation + judge retry paths with a stub client (no network).
Run: python3 -P audit/tests/mask_orig/test_pipeline.py   (~60s: part B uses real sleeps)
"""
import os, sys, types, asyncio, tempfile, importlib.util, time
from types import SimpleNamespace as NS
import pandas as pd

MASK = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../repos/mask_orig/mask"))
sys.path.insert(0, MASK)
for name in ["openai", "anthropic", "tqdm", "tqdm.asyncio", "dotenv"]:
    sys.modules[name] = types.ModuleType(name)
sys.modules["openai"].AsyncOpenAI = lambda **kw: None
sys.modules["anthropic"].AsyncAnthropic = lambda **kw: None
sys.modules["tqdm.asyncio"].tqdm_asyncio = None
sys.modules["dotenv"].load_dotenv = lambda: None


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(MASK, name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


gen, ev = load("generate_responses"), load("evaluate")


def completion(content, finish="stop"):
    return NS(choices=[NS(message=NS(content=content, refusal=None), finish_reason=finish)])


class GenClient:  # behaviour keyed on user prompt
    def __init__(self):
        self.chat = NS(completions=NS(create=self.create))
    async def create(self, model, messages, **kw):
        u = messages[-1]["content"]
        if u == "F1": raise Exception("Error code: 503 - upstream timeout")
        if u == "F2a": raise Exception("Error code: 400 - {'error': {'code': 'invalid_prompt'}}")
        if u == "F2b": raise Exception("Error code: 400 - {'error': {'code': 'content_filter'}}")
        if u == "F2c": return completion(None, "content_filter")
        if u == "F3": return completion("")
        return completion("ok answer")


# --- A: generation (sleep patched: retries are not what we measure here) ---
_real_sleep = asyncio.sleep
async def _nosleep(_): pass
asyncio.sleep = _nosleep  # gen.asyncio is the same module object
gen.create_model_client = lambda m: GenClient()
tmp = tempfile.mkdtemp()
inp, out = os.path.join(tmp, "in.csv"), os.path.join(tmp, "out.csv")
pd.DataFrame({"system_prompt": ["s"] * 6, "user_prompt": ["F1", "F2a", "F2b", "F2c", "F3", "ok"]}).to_csv(inp, index=False)
asyncio.run(gen.process_dataframe(inp, out, temperature=1.0, model_name="gpt-test", lie_k=1))
asyncio.sleep = _real_sleep  # part B needs real backoff timing
res = pd.read_csv(out)
print("== A: stored generations (after CSV round-trip, as evaluate.py reads them) ==")
for _, r in res.iterrows():
    print(f"  {r['user_prompt']:4} -> {r['generation(System Prompt + User Prompt)_run1']!r}")


# --- B: judge persistently raising inside process_row: 60s row timeout vs 62s of backoff ---
class JudgeClient:
    def __init__(self, fail_on):
        self.fail_on, self.calls = fail_on, 0
        self.chat = NS(completions=NS(create=self.create))
    async def create(self, model, messages, **kw):
        self.calls += 1
        if self.fail_on in messages[-1]["content"]:
            raise Exception("Error code: 500 - judge down")
        return completion("reasoning\nAnswer: B")

df = pd.DataFrame({
    "system_prompt": ["s"], "user_prompt": ["u"], "proposition": ["X <pivotal>is/is not</pivotal> true"],
    "formatted_ground_truth": ["A"], "belief_elicit_1": ["belief q"],
    "generation(System Prompt + User Prompt)_run1": ["LIE_RESPONSE"],
    "generation(belief_system_1 + belief_elicit_1)_run1": ["belief resp"],
})
for c in ["eval(System Prompt + User Prompt)_run1", "eval(belief_system_1 + belief_elicit_1)_run1"]:
    df[c] = None; df[c + "_extracted"] = None
belief_cols = [("belief_elicit_1", "generation(belief_system_1 + belief_elicit_1)_run1")]
ev.client = JudgeClient(fail_on="LIE_RESPONSE")  # only the lying-run judge call fails
t = time.time()
asyncio.run(ev.process_row(0, df.iloc[0], df, belief_cols, "known_facts.csv", 10))
print(f"== B: process_row with one persistently failing judge call ({time.time()-t:.0f}s, {ev.client.calls} calls) ==")
for c in df.columns:
    if c.startswith("eval("): print(f"  {c} = {df.at[0, c]!r}")
