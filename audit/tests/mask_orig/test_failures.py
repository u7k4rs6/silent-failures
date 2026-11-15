"""Probe original MASK parsing/aggregation with failure inputs. No network.
Run: python3 -P audit/tests/mask_orig/test_failures.py
openai/anthropic/tqdm/dotenv are stubbed so evaluate.py imports without creating a real client.
"""
import os, sys, types, tempfile, importlib.util, io, contextlib
import pandas as pd

MASK = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../repos/mask_orig/mask"))
sys.path.insert(0, MASK)  # for `from prompts.evaluation_prompts import *`

for name in ["openai", "tqdm", "tqdm.asyncio", "dotenv"]:
    sys.modules[name] = types.ModuleType(name)
sys.modules["openai"].AsyncOpenAI = lambda **kw: None
sys.modules["tqdm.asyncio"].tqdm_asyncio = None
sys.modules["dotenv"].load_dotenv = lambda: None


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(MASK, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sys.argv = ["x"]  # metric.py / process_metrics.py call parse_args() at import
ev, metric, pm = load("evaluate"), load("metric"), load("process_metrics")
_extract = ev.extract_boxed_evaluation
def _quiet_extract(x):  # its "Could not find Answer:" warning echoes the whole prompt
    with contextlib.redirect_stdout(io.StringIO()):
        return _extract(x)
ev.extract_boxed_evaluation = _quiet_extract
from prompts.evaluation_prompts import BINARY_JUDGE_PROMPT_TEMPLATE, NUMERICAL_JUDGE_PROMPT

# --- F4: judge exception string, exactly as evaluate.py:79 builds it ---
bin_prompt = BINARY_JUDGE_PROMPT_TEMPLATE.format(system_prompt="sys", user_prompt="usr", model_response="resp",
                                                proposition_option_1="X is true", proposition_option_2="X is false", rules="")
num_prompt = NUMERICAL_JUDGE_PROMPT.format(system_prompt="sys", user_prompt="usr", model_response="resp",
                                           proposition="X is <pivotal><value></pivotal>%")
f4_bin = f"ERROR: Prompt: {bin_prompt} and Exception: Connection error."
f4_num = f"ERROR: Prompt: {num_prompt} and Exception: Connection error."

judge_outputs = {
    "F4 judge exception (binary)": f4_bin,
    "F1-row TIMEOUT_ERROR (evaluate.py:490)": "TIMEOUT_ERROR",
    "F5 empty judge output": "",
    "F6 judge refusal text": "I'm sorry, I can't help with that.",
    "F5 'Answer: B.' (trailing period)": "reasoning...\nAnswer: B.",
    "F5 '**Answer:** B' (markdown)": "reasoning...\n**Answer:** B",
    "F5 'Answer: E' (out of range)": "Answer: E",
    "control 'Answer: B'": "Answer: B",
    "control 'Answer: A'": "Answer: A",
}

print("== extract_boxed_evaluation + aggregate_eval_honesty (belief='B') ==")
rows = []
for label, out in judge_outputs.items():
    ext = ev.extract_boxed_evaluation(out)
    rows.append({"label": label, "eval_belief": "B",
                 "eval(System Prompt + User Prompt)_run1_extracted": ext})
    print(f"{label!r:45} -> extracted={ext!r}"[:160])

# round-trip through CSV as evaluate.py:382 -> metric.py:462 does (None -> NaN)
tmp = tempfile.mkdtemp()
p = os.path.join(tmp, "x.csv")
pd.DataFrame(rows).to_csv(p, index=False)
df = pd.read_csv(p)
col = ["eval(System Prompt + User Prompt)_run1_extracted"]
df["eval_honesty_1"] = df.apply(lambda r: metric.aggregate_eval_honesty(r, col, "eval_belief"), axis=1)
for _, r in df.iterrows():
    print(f"  honesty {r['eval_honesty_1']:>3}  <- {r['label']}")

# --- process_metrics aggregation over the above rows ---
mdir = os.path.join(tmp, "metrics"); os.makedirs(mdir)
df.to_csv(os.path.join(mdir, "known_facts_testmodel.csv"), index=False)
pm.metrics_dir = mdir
res = pm.process_csv_files()["known_facts"]["testmodel"]
print("== process_metrics ==", res)

# --- F4 on numerical (statistics) path ---
ext_num = ev.extract_boxed_evaluation(f4_num)
print("== statistics F4 ==  extracted:", repr(ext_num)[:120])
srow = pd.Series({"eval_belief": "[(40.0, 45.0)]", "e": str(ext_num) if ext_num is not None else None})
print("  parse_tuple_string:", metric.parse_tuple_string(str(ext_num))[:5] if ext_num is not None else None)
print("  honesty_statistics:", metric.aggregate_eval_honesty_statistics(srow, ["e"], "eval_belief"))

# --- Belief side: all elicit_1 judge calls hit F4 -> garbage string becomes the 'belief' ---
g = ev.extract_boxed_evaluation(f4_bin)
brow = pd.Series({"eval(belief_system_1 + belief_elicit_1)_run1_extracted": g,
                  "eval(belief_system_1 + belief_elicit_1)_run2_extracted": g,
                  "eval(belief_system_1 + belief_elicit_1)_run3_extracted": g})
b = metric.aggregate_eval_beliefs(brow, list(brow.index))
print("== belief all-F4 ==  belief:", repr(b)[:80])
hrow = pd.Series({"eval_belief": b, "r1": "A"})
print("  honesty vs honest-looking 'A':", metric.aggregate_eval_honesty(hrow, ["r1"], "eval_belief"))

# --- F3: empty generation round-trips to NaN, and is formatted into the judge prompt as 'nan' ---
gp = os.path.join(tmp, "gen.csv")
pd.DataFrame({"generation(System Prompt + User Prompt)_run1": [""]}).to_csv(gp, index=False)
v = pd.read_csv(gp).iloc[0, 0]
print("== F3 empty generation after CSV round-trip ==", repr(v),
      "| in judge prompt:", "AI Response:\nnan" in BINARY_JUDGE_PROMPT_TEMPLATE.format(
          system_prompt="s", user_prompt="u", model_response=v, proposition_option_1="a", proposition_option_2="b", rules=""))
