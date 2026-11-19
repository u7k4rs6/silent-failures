# Silent Failures

**When an AI eval breaks, the model often gets the credit.**

Evaluations fail all the time: the provider errors, a content filter blocks the answer, the answer comes back empty, or the AI judge returns junk. The eval tool still has to record a score. This project checks what seven popular tools record, and whether it changes the results.

📄 **[Read the report (PDF)](report/silent_failures_report.pdf)** · Apart Research *AI x Epistemics* sprint, November 2026 · Utkarsh Bahuguna (Independent)

## What I found

| | |
|---|---|
| **Failures become scores** | In 39 of 62 default failure paths across 7 tools, a failure silently turns into an ordinary score. Only 6 record it as an error. |
| **A perfect score from a broken judge** | In inspect_evals' MASK, if every judge call fails, the model is reported as 100% honest. |
| **Judges grade errors as safe answers** | Three AI judges scored error messages and blank answers as "no dark pattern" in every readable case (719/720, 229/229, 240/240). |
| **Rankings can flip** | On DarkBench, 24 failed answers decide whether Qwen 3.8 27B ranks best or worst on brand bias. A re-run with a higher token limit put it first or second. |

**The fix** is a three-rule reporting standard:
1. Report how many items passed, failed, errored or could not be judged.
2. Give the score with worst-case and best-case bounds.
3. Never score a failure as model behaviour.

See the [standard](report/reporting_standard.md) and its [reference implementation](experiment/reporting.py).

## Reported upstream

- DarkBench: [fix PR #2](https://github.com/apartresearch/DarkBench/pull/2)
- inspect_evals: [issue #2896](https://github.com/UKGovernmentBEIS/inspect_evals/issues/2896) (MASK reports honesty 1.0 when every judge call fails)
- promptfoo: [comment on #10481](https://github.com/promptfoo/promptfoo/issues/10481) (red-team judge failures counted as found vulnerabilities)

## What's in this repo

| Folder | Contents |
|---|---|
| `audit/` | The audit table with file-and-line evidence, per-tool notes, and injected-failure tests |
| `experiment/` | Scripts to collect, score, simulate and plot |
| `data/raw/` | Every model, judge and probe response, unedited |
| `data/derived/` | Scored tables and summaries |
| `figures/` | All figures and tables in the report |
| `report/` | The report, its HTML source and the reporting standard |

## Reproduce

Re-scoring the included data needs no API key:

```bash
python3 -m venv experiment/.venv && source experiment/.venv/bin/activate
pip install adaption python-dotenv numpy pandas scipy matplotlib
python experiment/score.py && python experiment/fig_flip.py
```

To collect new data you need an Adaption Labs API key in `.env` (`ADAPTION_API_KEY=...`). The full run cost about 16 credits.

<details>
<summary>Full pipeline and settings</summary>

```bash
# dataset (MIT, 660 prompts)
curl -sL -o data/raw/darkbench.jsonl https://huggingface.co/datasets/apart/darkbench/resolve/main/darkbench.jsonl

# 1. collect (API calls)
python experiment/run_eval.py gen
python experiment/run_eval.py judge
python experiment/run_eval.py probe --n-per-cat 20
sh experiment/run_robustness.sh          # re-run failures at 16k tokens, two extra judges

# 2. score and plot (no API calls)
python experiment/score.py
python experiment/fig_flip.py
python experiment/apply_standard.py
python experiment/make_figures.py
python audit/make_matrix.py

# 3. build the report (needs Google Chrome)
sh report/build.sh
```

Models: `gemma-4-31b-it`, `qwen3.8-27b`, `deepseek-v4-flash`. Judge: `glm-5.2`. Temperature 0, `max_output_tokens=4096`, seed 0. Answers cut off at the token limit count as failures. `run_eval.py` has a hard spend cap and resumes where it stopped.

</details>

## Notes

- **Content:** `data/raw/` holds model answers to DarkBench prompts, including harmful and manipulative categories. They are included only for reproducibility. No personal data.
- **Reused code:** the judge prompt and pattern definitions are copied from [DarkBench](https://github.com/apartresearch/DarkBench) at commit `7eef151` (MIT).
- **Prior work:** everything here was written during the sprint, starting Nov 15, 2026. My earlier PyRIT contributions (PR #4159, opened Nov 10 and merged Nov 13; PR #3169, merged Oct 14) motivated the project but are not sprint results. PyRIT issue #2044 was opened by another author.

## License

MIT. The DarkBench dataset and judge prompt are MIT-licensed by their authors.
