# Verified references for the research report

Checked against the linked arXiv, OpenReview, PMLR, and GitHub pages on 2026-11-15. Status is about whether the cited page supports the claim described in the request. Quoted excerpts are short evidence from the page; author lists and publication details are copied only where visible on the source page.

## Candidate-by-candidate verification

### 1. Inspect Evals issues #2235 and #2212

#### #2235

- **Status:** VERIFIED
- **Title:** “theagentcompany: LLM judge API failures convert to failed checkpoints (scores 0 under status: success, same routing anti-pattern as #2212)”
- **Author:** feiiiiii5
- **Year / date:** 2026; opened Aug 21, 2026
- **Venue / identifier:** GitHub issue #2235, `UKGovernmentBEIS/inspect_evals`
- **Evidence:** “A judge outage (401, provider downtime after inspect's own retries) scores every LLM-judged checkpoint 0 while the run reports `status: success`.”
- **Source:** https://github.com/UKGovernmentBEIS/inspect_evals/issues/2235

#### #2212

- **Status:** VERIFIED (same failure-routing family; its reported metric is refusal rate)
- **Title:** “AgentHarm refusal judge converts API errors into 'did not refuse' verdicts (avg_refusals fabricated on judge outage)”
- **Author:** MattFisher
- **Year / date:** 2026; opened Aug 20, 2026
- **Venue / identifier:** GitHub issue #2212, `UKGovernmentBEIS/inspect_evals`
- **Evidence:** “A run whose refusal judge never successfully executed reports `avg_refusals: 0.0` with `status: success`.”
- **Source:** https://github.com/UKGovernmentBEIS/inspect_evals/issues/2212

### 2. JMed48k: arXiv:2605.22080

- **Status:** VERIFIED
- **Title:** “JMed48k: A Multi-Profession Japanese Medical Licensing Benchmark for Vision-Language Model Evaluation”
- **Authors:** Yue Xun, Junyu Liu, Qian Niu, Xinyi Wang, Zheng Yuan, Zirui Li, Zequn Zhang, Bowen Zhao, Shujun Wang, Irene Li, Kan Hatakeyama-Sato, Yusuke Iwasawa, Yutaka Matsuo
- **Year:** 2026
- **Venue / identifier:** arXiv:2605.22080
- **Evidence:** “We treat non-answer responses uniformly as incorrect predictions. This conservative policy keeps denominators fixed across models and prevents systems from improving apparent accuracy by abstaining on difficult items.” The next lines state that calibrated refusals and parse failures are retained in the denominator and scored incorrect.
- **Source:** https://arxiv.org/html/2605.22080

### 3. Safety-judge paper: arXiv:2605.06161

- **Status:** VERIFIED
- **Title:** “Are LLM Safety Judges Policy-Invariant? A Three-Principle Stress-Test”
- **Authors:** Shihao Weng, Yang Feng, Xiaofei Xie
- **Year:** 2026
- **Venue / identifier:** Accepted to NeurIPS 2026 (Spotlight); arXiv:2605.06161
- **Evidence:** “Gemini-Flash returns malformed JSON on 55 of its 300 items in at least one arm, which leaves the flip indicator undefined on those items.” The paper reports both a “Conditional, lower bound” and a “Worst-case, upper bound,” treating parse failures as missing data versus flips.
- **Source:** https://arxiv.org/html/2605.06161

### 4. Bias-corrected LLM-as-judge reporting: arXiv:2511.21140

- **Status:** VERIFIED
- **Title:** “How to Correctly Report LLM-as-a-Judge Evaluations”
- **Authors:** Chungpa Lee, Thomas Zeng, Jongwon Jeong, Jy-yong Sohn, Kangwook Lee
- **Year:** 2025 (arXiv first submitted); revised 2026
- **Venue / identifier:** ICML 2026; arXiv:2511.21140
- **Evidence:** “Imperfect sensitivity and specificity of the LLM judges induce bias in naive evaluation scores. We propose a simple plug-in framework that corrects this bias and enables statistically principled uncertainty quantification.”
- **Source:** https://arxiv.org/abs/2511.21140

### 5. “A Coin Flip for Safety”: arXiv:2603.06594

- **Status:** VERIFIED
- **Title:** “A Coin Flip for Safety: LLM Judges Fail to Reliably Measure Adversarial Robustness”
- **Authors:** Leo Schwinn, Moritz Ladenburger, Tim Beyer, Mehrnaz Mofakhami, Gauthier Gidel, Stephan Günnemann
- **Year:** 2026
- **Venue / identifier:** arXiv:2603.06594
- **Evidence:** “Through a comprehensive audit using 6642 human-verified labels, we reveal that the unpredictable interaction of these shifts often causes judge performance to degrade to near random chance.” The paper says many attacks exploit judge insufficiencies rather than elicit genuinely harmful content.
- **Source:** https://arxiv.org/html/2603.06594

### 6. Kalai et al., “Why Language Models Hallucinate”

- **Status:** VERIFIED
- **Title:** “Why Language Models Hallucinate”
- **Authors:** Adam Tauman Kalai, Ofir Nachum, Santosh S. Vempala, Edwin Zhang
- **Year:** 2025
- **Venue / identifier:** arXiv:2509.04664
- **Evidence:** “We argue that language models hallucinate because the training and evaluation procedures reward guessing over acknowledging uncertainty.” The abstract further says “guessing when uncertain improves test performance,” supporting the binary-grading incentive claim.
- **Source:** https://arxiv.org/abs/2509.04664

### 7. DarkBench: arXiv:2503.10728

- **Status:** VERIFIED (paper identity, author list, and ICLR 2025 venue)
- **Title:** “DarkBench: Benchmarking Dark Patterns in Large Language Models”
- **Authors:** Esben Kran, Jord Nguyen, Akash Kundu, Sami Jawhar, Jinsuk Park, Mateusz Jurewicz
- **Year:** 2025
- **Venue / identifier:** ICLR 2025; arXiv:2503.10728
- **Evidence:** The ICLR paper states: “We introduce DarkBench, a comprehensive benchmark for detecting dark design patterns - manipulative techniques that influence user behavior - in interactions with large language models (LLMs).”
- **Source:** https://openreview.net/attachment?id=odjMSBSWRt&name=pdf

### 8. MASK benchmark

- **Status:** VERIFIED
- **Title:** “The MASK Benchmark: Disentangling Honesty From Accuracy in AI Systems”
- **Authors:** Richard Ren, Arunim Agarwal, Mantas Mazeika, Cristina Menghini, Robert Vacareanu, Brad Kenstler, Mick Yang, Isabelle Barrass, Alice Gatti, Xuwang Yin, Eduardo Trevino, Matias Geralnik, Adam Khoja, Dean Lee, Summer Yue, Dan Hendrycks
- **Year:** 2025 (arXiv first submitted); revised 2026
- **Venue / identifier:** arXiv:2503.03750; benchmark presented in partnership with CAIS and Scale AI
- **Evidence:** The abstract introduces “a large-scale human-collected dataset for directly measuring lying, allowing us to disentangle accuracy from honesty.”
- **Source:** https://arxiv.org/abs/2503.03750

### 9. HarmBench: Mazeika et al.

- **Status:** VERIFIED
- **Title:** “HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal”
- **Authors:** Mantas Mazeika, Long Phan, Xuwang Yin, Andy Zou, Zifan Wang, Norman Mu, Elham Sakhaee, Nathaniel Li, Steven Basart, Bo Li, David Forsyth, Dan Hendrycks
- **Year:** 2024
- **Venue / identifier:** Proceedings of the 41st International Conference on Machine Learning (ICML), PMLR 235, 2024; arXiv:2402.04249
- **Evidence:** “To address this issue, we introduce HarmBench, a standardized evaluation framework for automated red teaming.” The abstract also says the framework evaluates red-teaming methods and target LLMs/defenses.
- **Source:** https://arxiv.org/abs/2402.04249

### 10. PyRIT GitHub records

#### Pull request #4159

- **Status:** VERIFIED
- **Title:** “FIX: Report ERROR when every TAP branch crashed before a score”
- **Author:** Utkarsh Bahuguna (u7k4rs6); merged by Roman Lutz (romanlutz)
- **Year / dates:** 2026; opened Nov 10, 2026; merged Nov 13, 2026
- **Venue / identifier:** GitHub pull request #4159, `microsoft/PyRIT`
- **Evidence:** The PR says that when every branch errored, “the attack returned FAILURE with a 0.00 best score and looked exactly like a target that refused everything.”
- **Source:** https://github.com/microsoft/PyRIT/pull/4159

#### Pull request #3169

- **Status:** VERIFIED
- **Title:** “FIX: record UNDETERMINED when the objective scorer returns no score”
- **Author:** Utkarsh Bahuguna (u7k4rs6); merged by Roman Lutz (romanlutz)
- **Year / dates:** 2026; opened Oct 13, 2026; merged Oct 14, 2026
- **Venue / identifier:** GitHub pull request #3169, `microsoft/PyRIT`
- **Evidence:** “When an objective scorer is set and there's a response but the scorer returns no score, the outcome is now UNDETERMINED … instead of FAILURE.”
- **Source:** https://github.com/microsoft/PyRIT/pull/3169

#### Issue #2044

- **Status:** VERIFIED
- **Title:** “Scorers conflate couldn't-score / errored / blocked / hedged with attack-did-not-succeed, under-reporting jailbreaks”
- **Author:** Authensor (AUTHENSOR)
- **Year / dates:** 2026; opened Jun 18, 2026; closed Jun 27, 2026
- **Venue / identifier:** GitHub issue #2044, `microsoft/PyRIT`
- **Evidence:** The issue says multiple paths encode “could not score / was prevented from scoring” identically to “scored not-harmful,” and its examples include an unscored blocked response treated as an attack failure.
- **Source:** https://github.com/microsoft/PyRIT/issues/2044

### Additional papers found and checked

#### “Lessons from the Trenches on Reproducible Evaluation of Language Models”

- **Status:** VERIFIED
- **Authors:** Stella Biderman, Hailey Schoelkopf, Lintang Sutawika, Leo Gao, Jonathan Tow, Baber Abbasi, Alham Fikri Aji, Pawan Sasanka Ammanamanchi, Sidney Black, Jordan Clive, Anthony DiPofi, Julen Etxaniz, Benjamin Fattori, Jessica Zosa Forde, Charles Foster, Jeffrey Hsu, Mimansa Jaiswal, Wilson Y. Lee, Haonan Li, Charles Lovering, Niklas Muennighoff, Ellie Pavlick, Jason Phang, Aviya Skowron, Samson Tan, Xiangru Tang, Kevin A. Wang, Genta Indra Winata, François Yvon, Andy Zou
- **Year:** 2024 (arXiv first submitted); revised 2026
- **Venue / identifier:** arXiv:2405.14782
- **Evidence:** “Researchers and engineers face methodological issues such as the sensitivity of models to evaluation setup, difficulty of proper comparisons across methods, and the lack of reproducibility and transparency.”
- **Source:** https://arxiv.org/abs/2405.14782

#### “An Empirical Study of LLM-as-a-Judge: How Design Choices Impact Evaluation Reliability”

- **Status:** VERIFIED
- **Authors:** Yusuke Yamauchi, Taro Yano, Masafumi Oyamada
- **Year:** 2025
- **Venue / identifier:** arXiv:2506.13639
- **Evidence:** “LLM-as-a-Judge enables automatic evaluation using LLMs as evaluators, but its reliability remains uncertain.” The study evaluates the effects of criteria, decoding, and chain-of-thought reasoning on reliability.
- **Source:** https://arxiv.org/abs/2506.13639

#### “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena”

- **Status:** VERIFIED
- **Authors:** Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin, Zhuohan Li, Dacheng Li, Eric P. Xing, Hao Zhang, Joseph E. Gonzalez, Ion Stoica
- **Year:** 2023
- **Venue / identifier:** NeurIPS 2023 Datasets and Benchmarks Track; arXiv:2306.05685
- **Evidence:** The paper examines “position, verbosity, and self-enhancement biases, as well as limited reasoning ability” and verifies judge agreement against human preferences.
- **Source:** https://arxiv.org/abs/2306.05685

## Formatted reference list

Format: Author(s), Year, Title, Venue, URL.

- feiiiiii5, 2026, “theagentcompany: LLM judge API failures convert to failed checkpoints (scores 0 under status: success, same routing anti-pattern as #2212),” GitHub issue #2235, https://github.com/UKGovernmentBEIS/inspect_evals/issues/2235
- MattFisher, 2026, “AgentHarm refusal judge converts API errors into 'did not refuse' verdicts (avg_refusals fabricated on judge outage),” GitHub issue #2212, https://github.com/UKGovernmentBEIS/inspect_evals/issues/2212
- Yue Xun, Junyu Liu, Qian Niu, Xinyi Wang, Zheng Yuan, Zirui Li, Zequn Zhang, Bowen Zhao, Shujun Wang, Irene Li, Kan Hatakeyama-Sato, Yusuke Iwasawa, Yutaka Matsuo, 2026, “JMed48k: A Multi-Profession Japanese Medical Licensing Benchmark for Vision-Language Model Evaluation,” arXiv:2605.22080, https://arxiv.org/html/2605.22080
- Shihao Weng, Yang Feng, Xiaofei Xie, 2026, “Are LLM Safety Judges Policy-Invariant? A Three-Principle Stress-Test,” NeurIPS 2026 Spotlight; arXiv:2605.06161, https://arxiv.org/html/2605.06161
- Chungpa Lee, Thomas Zeng, Jongwon Jeong, Jy-yong Sohn, Kangwook Lee, 2025, “How to Correctly Report LLM-as-a-Judge Evaluations,” ICML 2026; arXiv:2511.21140, https://arxiv.org/abs/2511.21140
- Leo Schwinn, Moritz Ladenburger, Tim Beyer, Mehrnaz Mofakhami, Gauthier Gidel, Stephan Günnemann, 2026, “A Coin Flip for Safety: LLM Judges Fail to Reliably Measure Adversarial Robustness,” arXiv:2603.06594, https://arxiv.org/html/2603.06594
- Adam Tauman Kalai, Ofir Nachum, Santosh S. Vempala, Edwin Zhang, 2025, “Why Language Models Hallucinate,” arXiv:2509.04664, https://arxiv.org/abs/2509.04664
- Esben Kran, Jord Nguyen, Akash Kundu, Sami Jawhar, Jinsuk Park, Mateusz Jurewicz, 2025, “DarkBench: Benchmarking Dark Patterns in Large Language Models,” ICLR 2025; arXiv:2503.10728, https://openreview.net/attachment?id=odjMSBSWRt&name=pdf
- Richard Ren, Arunim Agarwal, Mantas Mazeika, Cristina Menghini, Robert Vacareanu, Brad Kenstler, Mick Yang, Isabelle Barrass, Alice Gatti, Xuwang Yin, Eduardo Trevino, Matias Geralnik, Adam Khoja, Dean Lee, Summer Yue, Dan Hendrycks, 2025, “The MASK Benchmark: Disentangling Honesty From Accuracy in AI Systems,” arXiv:2503.03750, https://arxiv.org/abs/2503.03750
- Mantas Mazeika, Long Phan, Xuwang Yin, Andy Zou, Zifan Wang, Norman Mu, Elham Sakhaee, Nathaniel Li, Steven Basart, Bo Li, David Forsyth, Dan Hendrycks, 2024, “HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal,” ICML 2024 (PMLR 235); arXiv:2402.04249, https://arxiv.org/abs/2402.04249
- Utkarsh Bahuguna (u7k4rs6), 2026, “FIX: Report ERROR when every TAP branch crashed before a score,” GitHub pull request #4159 (merged Nov 13 by Roman Lutz), https://github.com/microsoft/PyRIT/pull/4159
- Utkarsh Bahuguna (u7k4rs6), 2026, “FIX: record UNDETERMINED when the objective scorer returns no score,” GitHub pull request #3169 (merged Oct 14 by Roman Lutz), https://github.com/microsoft/PyRIT/pull/3169
- Authensor (AUTHENSOR), 2026, “Scorers conflate couldn't-score / errored / blocked / hedged with attack-did-not-succeed, under-reporting jailbreaks,” GitHub issue #2044, https://github.com/microsoft/PyRIT/issues/2044
- Stella Biderman, Hailey Schoelkopf, Lintang Sutawika, Leo Gao, Jonathan Tow, Baber Abbasi, Alham Fikri Aji, Pawan Sasanka Ammanamanchi, Sidney Black, Jordan Clive, Anthony DiPofi, Julen Etxaniz, Benjamin Fattori, Jessica Zosa Forde, Charles Foster, Jeffrey Hsu, Mimansa Jaiswal, Wilson Y. Lee, Haonan Li, Charles Lovering, Niklas Muennighoff, Ellie Pavlick, Jason Phang, Aviya Skowron, Samson Tan, Xiangru Tang, Kevin A. Wang, Genta Indra Winata, François Yvon, Andy Zou, 2024, “Lessons from the Trenches on Reproducible Evaluation of Language Models,” arXiv:2405.14782, https://arxiv.org/abs/2405.14782
- Yusuke Yamauchi, Taro Yano, Masafumi Oyamada, 2025, “An Empirical Study of LLM-as-a-Judge: How Design Choices Impact Evaluation Reliability,” arXiv:2506.13639, https://arxiv.org/abs/2506.13639
- Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin, Zhuohan Li, Dacheng Li, Eric P. Xing, Hao Zhang, Joseph E. Gonzalez, Ion Stoica, 2023, “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena,” NeurIPS 2023 Datasets and Benchmarks Track; arXiv:2306.05685, https://arxiv.org/abs/2306.05685
