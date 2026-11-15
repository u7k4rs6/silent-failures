# Harness failure-handling matrix (split routes)

Cells show all audited routes from `policy_v2`. `R→` means retry before the displayed policy; multiple codes denote split routes. `—` means not audited.

| Harness component | F1 | F2 | F3 | F4 | F5 | F6 |
|---|---:|---:|---:|---:|---:|---:|
| inspect_ai | `R→ABORT` | `GRADE` / `NEG` / `ABORT` | `NEG` / `GRADE` | `ABORT` | `DROP-R` | `DROP-R` |
| inspect_evals / MASK | — | — | — | `ABORT` | `NEG` | `NEG` |
| inspect_evals / AgentHarm | — | — | `NEG` | `NEG` | `NEG` | `NEG` |
| inspect_evals / StrongREJECT | — | `GRADE` | — | `ABORT` | `DROP-R` | `DROP-R` |
| inspect_evals / TheAgentCompany | — | — | — | `NEG` | `NEG` | `NEG` |
| DarkBench | `ABORT` | `GRADE` | `GRADE` | `ABORT` | `R→DROP-S` / `R→NEG` | `R→DROP-S` / `R→NEG` |
| HarmBench | `R→GRADE` / `ABORT` | `GRADE` / `R→GRADE` / `ABORT` | `GRADE` | `ABORT` | `NEG` | `NEG` |
| PyRIT (attack components) | `SEP` / `ABORT` / `DROP-S` / `DROP-R` / `NEG` | `NEG` / `R→NEG` | `R→SEP` | `SEP` | `R→SEP` | `R→SEP` |
| promptfoo / evals | `R→SEP` / `ABORT` | `GRADE` | `GRADE` / `NEG` | `NEG` / `SEP` | `NEG` / `POS` | `NEG` |
| promptfoo / red-team | `SEP` / `DROP-S` / `NEG` | `NEG` / `GRADE` | `NEG` | `POS` / `SEP` / `NEG` | `POS` | `POS` |
| lm_eval | `R→ABORT` / `ABORT` | `R→ABORT` / `NEG` / `ABORT` | `NEG` / `RAND` | `ABORT` | `NEG` | `NEG` / `ABORT` |
| MASK (original) | `R→GRADE` / `R→NEG` | `GRADE` / `R→GRADE` | `GRADE` / `NEG` | `R→NEG` / `POS` | `POS` / `NEG` | `NEG` |

## Code key

| Code | Policy |
|---|---|
| NEG / POS / RAND | Imputed: absent / present / random |
| GRADE | Graded as output |
| DROP-S / DROP-R | Dropped (silent) / (reported) |
| SEP / ABORT | Separate outcome / Abort |
| R→X | Retry before policy X |

The default-route matrix selects the row marked `default_route=y` for each component and failure type. See `audit_table_v2.csv` for each row's `default_reason`.
