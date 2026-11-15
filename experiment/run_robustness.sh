#!/bin/sh
# Robustness run: re-run failed generations with 16k tokens, judge them, then two second judges. Resumable.
cd "$(dirname "$0")/.." || exit 1
P=experiment/.venv/bin/python
$P experiment/run_eval.py rerun --max-out 16384 --tag _16k
$P experiment/run_eval.py judge --gen-file rerun_16k.jsonl --tag _rerun16k
for J in "qwen3.5-397b _qwen397" "gemma-4-26b-a4b-it _gemma26"; do
  set -- $J
  $P experiment/run_eval.py judge --judge "$1" --cats brand-bias,sycophancy --tag "$2"
  $P experiment/run_eval.py probe --judge "$1" --cats brand-bias,sycophancy --n-per-cat 20 --tag "$2"
done
$P experiment/robustness.py > data/robustness_run.log 2>&1
echo DONE
