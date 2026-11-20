#!/bin/sh
# Follow-up after the sprint (Nov 19): 6 models at a 16k token limit, judged by GLM 5.2; then 5 repeats of
# Qwen's two failure-heavy categories at the sprint's 4k limit, to see whether the same prompts fail.
set -e
PY=experiment/.venv/bin/python
M=gemma-4-31b-it,qwen3.8-27b,deepseek-v4-flash,glm-5.3-flash,nemotron-SEA-LION-v4.8-120b-a12b,qwen-SEA-LION-v5-397b-a17b-plus
$PY experiment/run_eval.py gen --models $M --max-out 16384 --tag _16k
$PY experiment/run_eval.py judge --models $M --gen-file gen_16k.jsonl --tag _16k
for k in 1 2 3 4 5; do
  $PY experiment/run_eval.py gen --models qwen3.8-27b --cats brand-bias,sycophancy --tag _rep$k
done
# added after the first pass: judge the repeats (to see how the score moves run to run) and a cheap second judge
for k in 1 2 3 4 5; do
  $PY experiment/run_eval.py judge --models qwen3.8-27b --cats brand-bias,sycophancy --gen-file gen_rep$k.jsonl --tag _rep$k
done
$PY experiment/run_eval.py judge --judge gemma-4-26b-a4b-it --models $M --gen-file gen_16k.jsonl --tag _16k_gemma26
