# lm-evaluation-harness: how infrastructure failures are recorded

- Repo: https://github.com/EleutherAI/lm-evaluation-harness, commit `d6de81643928d653435c431bae19945d41d32520` (shallow clone in `audit/repos/lm_eval`).
- Scope: the generative (`generate_until`) path and the API backends only. Log-likelihood paths were not audited.
- Base dependencies at this commit do **not** include torch (`pyproject.toml` lists datasets, numpy, evaluate, ...). lm_eval itself was not installed. One small venv, `audit/tests/lm_eval/.venv`, has only numpy, tqdm, tenacity, requests, aiohttp, pyyaml, jinja2, typing_extensions and sacrebleu. The test stubs the `lm_eval` package root so `lm_eval/__init__.py` (which needs installed metadata) is skipped, then imports the real repo modules.
- Test: `audit/tests/lm_eval/check_failures.py`, output in `audit/tests/lm_eval/run_output.txt`. It patches `requests.post` with fake responses and uses a stub `anthropic` module and a stub OpenAI client for the judge. No network calls, no keys. Only the **sync** API path (`num_concurrent<=1`) was run. The async path was read only.

## 1. Provider call and retries (`lm_eval/models/api_models.py`)

```python
# api_models.py:123, 140
        max_retries: int = 3,
        timeout: int = 300,
```

```python
# api_models.py:775-783  (sync generate_until)
                outputs = retry(
                    stop=stop_after_attempt(self.max_retries),
                    wait=wait_exponential(multiplier=0.5, min=1, max=10),
                    reraise=True,
                )(self.model_call)(
```

```python
# api_models.py:477-488  (model_call)
            if not response.ok:
                eval_logger.warning(
                    f"API request failed with error message: {response.text}. Retrying..."
                )
            response.raise_for_status()
            return response.json()
        except RetryError:
            eval_logger.error(
                "API request failed after multiple retries. Please check the API status."
            )
            return None
```

The `except RetryError` is dead code. Tenacity wraps `model_call` from outside, and with `reraise=True` it re-raises the last original exception, not `RetryError`. So the `return None` never happens.

```python
# api_models.py:555-560 (async amodel_call) and :603-610 (async retry)
        except BaseException as e:
            eval_logger.error(
                f"Exception:{e!r}, {locals().get('outputs', '(no outputs)')}, retrying."
            )
            raise
...
            retry_: Callable[..., Awaitable[Any]] = retry(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=0.5, min=1, max=10),
                reraise=True,
```

**F1 = RETRY-THEN-ABORT.** Every exception is retried 3 times, then raised, and the run fails. This includes non-retryable 4xx errors. Confirmed: HTTP 500 gave `('raised', 'HTTPError: 500 ...', 3 calls)`, and `requests.Timeout` gave `('raised', 'Timeout: read timed out', 3 calls)`.

**F2 (HTTP 400 content_filter) = RETRY-THEN-ABORT**, on the same path. Confirmed: 3 calls, then `HTTPError: 400 {"error": {"code": "content_filter", ...}}`.

## 2. None or blocked content becomes "" (F2 at HTTP 200, F3)

```python
# api_models.py:41-47
# Set a placeholder to use as model output when the returned answer is "None"
# This commonly occurs when the model runs out of tokens during the thinking
# process and returns an empty answer but no error.
# Default value is an empty string, but it can be edited if this is problematic.
LMEVAL_MODEL_NONE_ANSWER_PLACEHOLDER = os.environ.get(
    "LMEVAL_MODEL_NONE_ANSWER_PLACEHOLDER", ""
)
```

```python
# api_models.py:792-800 (sync); the same logic is in async at :540-549
                    # Always append to res to maintain the correct number of items
                    # even if generation failed (generated_text is None)
                    if generated_text is None:
                        eval_logger.warning(
                            f"API returned null content. Content filled with ..."
                        )
                        # Patch "None" answer with consistent value (async and sync calls)
                        res.append(LMEVAL_MODEL_NONE_ANSWER_PLACEHOLDER)
```

```python
# openai_completions.py:219-237  (LocalChatCompletion / OpenAIChatCompletion / Azure)
            try:
                tmp = [None] * len(out["choices"])
                for choices in out["choices"]:
                    content = choices["message"]["content"]
                    tmp[choices["index"]] = (
                        postprocess_generated_text(...)
                        if content is not None
                        else None
                    )
            except (IndexError, KeyError, TypeError) as e:
                # account for cases that generation is blocked by content filter,
                # which is common for Azure OpenAI Service,
                # not sure if need to account for multiple choices
                eval_logger.warning(f"Could not parse generations: {e}")
                tmp = [""]
```

`finish_reason`, `stop_reason` and `refusal` appear nowhere in `lm_eval/models/` (grep: 0 hits). Confirmed: `finish_reason=content_filter, content=None` gave `['']`, a missing `message` key gave `['']`, a `refusal` field with `content=None` gave `['']`, and empty content gave `['']`. The only trace is a log warning.

**anthropic-chat** (`AnthropicChat`, a TemplateAPI subclass):

```python
# anthropic_llms.py:362-371
    def parse_generations(self, outputs, **kwargs) -> List[str]:
        res = []
        ...
        for out in outputs:
            for choices in out["content"]:
                res.append(choices["text"])
        return res
```

A refusal with `content: []` appends nothing. `Collator.get_original` (`lm_eval/models/utils.py:414`, `zip(..., strict=True)`) then raises. Confirmed: `ValueError: zip() argument 2 is shorter than argument 1` after 1 call. **F2 here is ABORT** (accidental).

**Legacy anthropic-completions** (`AnthropicLM`):

```python
# anthropic_llms.py:59-63
    @retry_on_specific_exceptions(
        on_exceptions=[anthropic.RateLimitError],
        max_retries=None,  # retry forever, consider changing
# anthropic_llms.py:252-257
            except anthropic.APIConnectionError as e:
                eval_logger.critical(f"Server unreachable: {e.__cause__}")
                break
            except anthropic.APIStatusError as e:
                eval_logger.critical(f"API error {e.status_code}: {e.message}")
                break
```

```python
# evaluator.py:600-604
        resps = getattr(lm, reqtype)(cloned_reqs)
        for x, req in zip(resps, cloned_reqs, strict=True):
```

Confirmed with a stub `anthropic` module: an error on request 2 of 3 returned `['ok']` (1 of 3), and the strict zip raised ValueError. **F1 = ABORT.** It has no retries except for rate limits, which are retried forever.

## 3. Filters and metric (F3, F5 extraction)

```python
# filters/extraction.py:24-28, 44-58
        fallback: str = "[invalid]",
...
            for resp in inst:
                if not isinstance(resp, str):
                    resp = ""
                match = self.regex.findall(resp)
                if match:
                    ...
                else:
                    match = self.fallback
```

```python
# api/metrics.py:264-266
    score_list = predictions == references
    return {"exact_match": np.mean(score_list)}
```

gsm8k (`tasks/gsm8k/gsm8k.yaml`) uses `strict-match` (`#### (\-?[0-9\.\,]+)`) and `flexible-extract`. Confirmed: `""` gave `[invalid]` for both and EM 0. Refusal text gave `[invalid]` and EM 0. `exact_match(['[invalid]','18'], ['18','18'])` gave 0.5, so the item stays in the denominator. No count of `[invalid]` is reported anywhere (no hits in `evaluator.py` / `evaluator_utils.py`). **F3 = IMPUTE-NEG, F5 (extraction) = IMPUTE-NEG.**

Random-guess fallback in multimodal MC tasks:

```python
# tasks/pisa/utils.py:193-194   (same at tasks/mmmu/utils.py:135; mmmu seeds random at :8)
    if len(candidates) == 0:  # still not get answer, randomly choose one.
        pred_index = random.choice(all_choices)
```

Confirmed: pisa with 4 options and an empty response gave acc 0.2275 over 400 trials. A failed generation is **partly IMPUTE-POS**: it counts as correct with probability 1/k.

## 4. LLM judge (F4, F5, F6): only `pisa_*_llm_judged`

A grep of `tasks/` for OpenAI/anthropic/litellm/judge clients found only `tasks/pisa/utils.py`. `slr_bench` uses a symbolic (HF `evaluate`) verifier, not an LLM.

```python
# tasks/pisa/utils.py:312-329
def judge_mcq(pred: str, options: List[str], correct: str) -> int:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    user_prompt = build_user_prompt(pred, options, correct)
    resp = client.chat.completions.create(
        model=MODEL_VERSION, temperature=0, max_tokens=1,
        messages=[...],
    )
    raw = resp.choices[0].message.content.strip()
    return 1 if raw == "1" else 0
```

- **F4 = ABORT**: there is no try/except, and lm_eval adds no retry (any retrying is the OpenAI SDK's own default, not checked). Confirmed at the function level: the exception propagated.
- **F5 = IMPUTE-NEG**: anything other than exactly `"1"` scores 0 (`'Correct'` gave 0).
- **F6**: a text refusal gives 0 (IMPUTE-NEG; `'I'` gave 0). `content=None` (SDK refusal or judge-side filter) raises `AttributeError: 'NoneType' object has no attribute 'strip'`, so the run aborts (confirmed).

## Not checked
- The async (`num_concurrent>1`) path was not executed. Code reading shows the same retry, then re-raise, then `asyncio.gather` raising.
- Other backends (litellm_llms, ibm_watsonx_ai, textsynth, sglang_generate_API) were not traced.
- `--log_samples` output stores the raw `""` / `[invalid]` per sample, but there is no flag or aggregate count.
