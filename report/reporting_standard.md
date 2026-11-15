# Reporting standard for evaluation failures

Apply these rules to every evaluation result:

1. **Show outcomes and coverage.** Report counts of PASS, FAIL, ERROR, and UNDETERMINED, and coverage: the fraction of evaluated items that produced a valid score (PASS or FAIL).
2. **Show the valid-item score and failure bounds.** Report the score over valid items, alongside lower and upper bounds that treat every unresolved item as absent or as present. State how the metric maps PASS and FAIL to the measured behaviour.
3. **Do not score evaluation failures as model behaviour.** A failed or unparseable judge call must never produce a score, and failure artifacts (such as error text, filter messages, placeholders, empty outputs, or harness-authored refusals) must never be graded as if they were model output.

Example: real output for Qwen 3.8 27B on our DarkBench run (660 prompts; FAIL = dark pattern present), produced by `experiment/reporting.py` via `experiment/apply_standard.py`:

```text
PASS 487 | FAIL 129 | ERROR 43 | UNDETERMINED 1
coverage            0.933
score (valid items) 0.209
bounds              [0.195, 0.262]
brand-bias only     score 0.070, bounds [0.055, 0.273]   <- 24 of 110 answers failed
```

## Edge cases

- **Retries:** count each item once, by its final outcome after retries, and report how many items needed retries.
- **Partial outputs:** an answer cut off at the token limit is ERROR unless the tool can verify it is complete (e.g. a normal finish reason).
- **Invalid but gradable:** if the judge flags an answer as invalid but still returns a verdict, keep the verdict and report how many answers were flagged; never convert them to absent.
- **Several judges:** report their agreement, or the bounds across judges, rather than one judge's score.
