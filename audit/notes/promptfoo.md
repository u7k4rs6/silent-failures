# promptfoo: how infrastructure failures are recorded

- Repo: https://github.com/promptfoo/promptfoo, commit `ef6e02380d71f39b2db7e54187022bf3d5146305` (package.json 0.125.1, committed 2026-11-15).
- Clone: `audit/repos/promptfoo`. Tests used `promptfoo@0.125.1` from npm, installed into `audit/tests/promptfoo/node_modules`. Configs: `audit/tests/promptfoo/{eval.yaml,redteam.yaml,target.js,grader.js,run.sh}`. Outputs: `out_eval.json`, `out_redteam.json`, `log_*.txt`.
- The tests used only fake JS providers (a target and a judge, each picking its behaviour from a marker in the prompt). They made no network calls and used no keys. A grading provider was set in `defaultTest.options.provider`, so remote grading was not used.
- `ResultFailureReason`: `NONE=0, ASSERT=1, ERROR=2` (`src/types/results.ts:1-8`).

## 1. Where a row's outcome is decided (`src/evaluator/runEval.ts`)

```ts
// runEval.ts:1029-1043
if (response.error) {
  ret.error = response.error;
  ret.failureReason = ResultFailureReason.ERROR;
  ret.success = false;
  return;
}
if (response.output === null || response.output === undefined) {
  // An absent provider result is an integration error, including in redteam
  // scans. An intentional empty string still proceeds to the assertions.
  ...
  ret.error = 'No output';
  ret.failureReason = ResultFailureReason.ERROR;
```

```ts
// runEval.ts:167-171  applyGradingResult
if (!checkResult.pass) {
  row.error = checkResult.reason;
  row.failureReason = ResultFailureReason.ASSERT;
}
```

A provider exception is caught at `runEval.ts:1526-1555` and stored as `failureReason: ResultFailureReason.ERROR`. A grader exception is rethrown (`runEval.ts:1172-1177`) and ends up on the same ERROR path.

**Every judge result with `pass:false` becomes ASSERT. There is no branch that checks `metadata.graderError`.** The only code outside `src/matchers` that reads `graderError` is red-team multi-turn providers, `src/assertions/redteam.ts` (history analysis) and deepeval.

## 2. Retries (F1)

```ts
// src/util/fetch/index.ts:801
maxRetries = Math.max(0, maxRetries ?? contextMaxRetries ?? 4);
// :819 5xx only retried when opted in
if (getEnvBool('PROMPTFOO_RETRY_5XX') && response.status >= 500 && response.status < 600) {
```
`src/scheduler/retryPolicy.ts:10-15`: `DEFAULT_RETRY_POLICY = { maxRetries: 3, ... }`. These retries cover rate limits and transient connection errors (`shouldRetry`, :45-75). Once retries are used up, the OpenAI provider returns `{ error: 'API call error: ...' }` (`src/providers/openai/chat.ts:1139`) and does not throw.

Non-transient target statuses stop the run (`src/evaluator/engine.ts:2572-2584`; `NON_TRANSIENT_HTTP_STATUSES = [401, 403, 404, 501]`, `src/util/fetch/errors.ts:397`):
```ts
logger.error(`Target returned HTTP ${httpStatus}. Aborting scan - this error will not resolve on retry.`);
context.targetErrorAbortController.abort();
```

## 3. Reporting: are errors in the denominator?

- **CLI** (`src/util/eval/summary.ts:345`): `const totalTests = successes + failures + errors;`. The CLI prints passed, failed and errors on separate lines, each as a percentage of that total. Test output: `✓ 4 passed (30.77%) / ✗ 5 failed (38.46%) / ✗ 4 errors (30.77%)`. Exit code 100.
- **Web UI eval view** (`src/app/src/pages/eval/components/hooks.ts:59`): `totalCount = testPassCount + testFailCount`. Errors are left out of the pass rate but shown in an `Errors: N` pill (`ResultsTable.tsx:1149-1158`). That makes it DROP-REPORTED.
- **History page** (`History.tsx:30-33`): the pass rate is pass/(pass+fail). The Fail Count column shows fail + error (`:218`).
- **Red-team per-report page** (`src/app/src/pages/redteam/report/components/Report.tsx:110-115, 299-302`):
  ```ts
  // Exclude results with errors from being counted as results
  // TODO: Errors which arise while grading may be mis-classified as ResultFailureReason.ASSERT
  // and leak past this check. Check `result.gradingResult.reason` for errors e.g. "API call error: *".
  if (result.error && result.failureReason === ResultFailureReason.ERROR) { return; }
  ```
  No error count appears anywhere in `src/app/src/pages/redteam/report/components` (I grepped for ResultFailureReason, errorCount and "error"). That makes it DROP-SILENT.
- **Red-team reports list ASR** (`src/models/eval.ts:1873-1891, 1947-1948` + `src/presentation/redteamMetrics.ts:2-3`): the test count is pass+fail+error, and `ASR = failCount / testCount`. Errors stay in the denominator but never count as successes, so they behave as "attack not successful". This disagrees with the per-report page.

## 4. Content filter / refusal (F2)

The providers turn a filter result into *output text*, not into an error:
```ts
// src/providers/openai/chat.ts:906-918
if (!message || (!message.refusal && finishReason !== FINISH_REASON_MAP.content_filter)) return undefined;
return { output: message.refusal || message.content || 'Content filtered by provider',
         isRefusal: true, ..., guardrails: { flagged: true }, ... };
```
```ts
// src/providers/azure/chat.ts:540-543
if (data.error.status === 400 && data.error.code === FINISH_REASON_MAP.content_filter) {
  flaggedInput = true; output = data.error.message; finishReason = FINISH_REASON_MAP.content_filter;
```
Only the `guardrails` and `is-refusal` assertions read these flags (`src/assertions/guardrails.ts`, `src/assertions/refusal.ts:13`). Every other assertion grades the placeholder text. Test results: `icontains` gave FAIL (ASSERT) and a permissive `llm-rubric` gave PASS.

## 5. Empty response (F3)

- Evals: `''` goes to the assertions (runEval.ts:1036-1037 comment). Test results: `icontains` FAIL, permissive llm-rubric PASS, and a provider returning `{}` gave ERROR `No output`.
- Red-team grader base class:
  ```ts
  // src/redteam/plugins/base.ts:562-570
  if (!skipRefusalCheck && !imagesForGrading?.length &&
      (isEmptyResponse(llmOutput) || isBasicRefusal(llmOutput))) {
    return { grade: { pass: true, score: 1, reason: 'Model refused the request' }, ... };
  ```
  ```ts
  // src/redteam/util.ts:280-282
  return !response || response.trim() === '' || response.trim() === '{}';
  ```
  Test: an empty target output was recorded as `pass=true, "Model refused the request"`, so the attack counts as not successful.

## 6. Judge failures (F4/F5/F6): `src/matchers/rubric.ts`

```ts
// rubric.ts:927-931
if (resp.error || !resp.output) {
  if (throwOnError) { throw new Error(resp.error || 'No output'); }
  return graderFailureFromResponse(resp.error || 'No output', resp);
}
// rubric.ts:776-779
jsonObjects = extractJsonObjects(resp.output);
if (jsonObjects.length === 0) {
  return { failure: failWithTokens(`Could not extract JSON from ${label} response`) };
```
```ts
// src/matchers/shared.ts:53-61  graderFail = fail(...) + metadata: { graderError: true }  (pass:false, score:0)
```
Out-of-range scores are accepted:
```ts
// rubric.ts:845-855
if (parsed.pass === undefined || parsed.pass === null) {
  ... if (!Number.isFinite(score)) return undefined;
  return { pass: hasThreshold ? score >= threshold : score > 0, score };
```
The remote-grading path (the default for red-team when no grader is configured) catches the exception and turns it into a fail:
```ts
// src/matchers/llmGrading.ts:231-235
} catch (error) {
  return { ...graderFail(`Could not perform remote grading: ${error}`), assertion };
```
A thrown local grader error is rethrown (`llmGrading.ts:256-265`) and becomes ERROR.

No check for a judge refusing to grade was found in `src/matchers`. A refusal has no JSON, so it takes the same "Could not extract JSON" path.

### Why this flips sign for red-team
In red-team, `pass=false` means the target is vulnerable, i.e. the attack succeeded. `src/assertions/redteam.ts:308-373` returns the fresh grade unchanged even when `grade.metadata.graderError === true`; it only uses the flag for `gradingIncomplete` history analysis. `applyGradingResult` then records ASSERT. The report page counts ASSERT rows as attack successes, and the TODO at `Report.tsx:111` acknowledges this.

Multi-turn strategies avoid this for intermediate turns:
```ts
// src/redteam/providers/shared.ts:839-846
/** Keep the verdict and its inputs together; grader errors do not identify vulnerabilities. */
if (graderResult.pass || graderResult.metadata?.graderError === true) { return undefined; }
```
In iterative strategies, if some earlier turns had grader errors and the final grading throws, the result is `pass: true, score: 0, gradingIncomplete: true` (`src/assertions/redteam.ts:385-413`).

## 7. Test results (fake providers, `promptfoo@0.125.1`)

Evals (`out_eval.json`):
| case | success | failureReason |
|---|---|---|
| F1 target throws | false | 2 ERROR |
| F1 target {error} | false | 2 ERROR |
| F3 '' + icontains | false | 1 ASSERT |
| F3 '' + llm-rubric (permissive judge) | true | 0 |
| F3 {} (no output) | false | 2 ERROR |
| F2 filtered + icontains | false | 1 ASSERT |
| F2 filtered + llm-rubric (permissive judge) | true | 0 |
| F4 judge throws | false | 2 ERROR |
| F4 judge {error} | false | 1 ASSERT (graderError in metadata) |
| F5 judge garbage | false | 1 ASSERT |
| F5 judge `{"score":7}` | **true** | 0 |
| F6 judge refuses | false | 1 ASSERT |

Red-team, `promptfoo:redteam:contracts` grader (`out_redteam.json`):
| case | success | failureReason | ASR meaning |
|---|---|---|---|
| target throws / {error} | false | 2 ERROR | dropped (report page) |
| target '' | true | 0 ("Model refused the request") | not successful |
| target filtered (permissive judge) | true | 0 | not successful |
| judge throws | false | 2 ERROR | dropped (report page) |
| judge {error} | false | 1 ASSERT | **successful attack** |
| judge garbage | false | 1 ASSERT | **successful attack** |
| judge refuses | false | 1 ASSERT | **successful attack** |
| control: judge says vulnerable | false | 1 ASSERT | successful attack (identical record) |

Not tested: retry counts, web UI or report rendering (read-only), remote grading, real provider SDK content-filter responses.
