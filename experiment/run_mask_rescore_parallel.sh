#!/bin/sh
# The 4,000-token judge re-scoring from run_mask_followup.sh, one process per model, run in parallel to save time.
PY=audit/tests/inspect/.venv/bin/python
for M in deepseek-v4-flash gemma-4-31b-it qwen3.8-27b; do
  $PY experiment/mask_study.py rescore glm-5.3-flash 4000 judge4000 $M > data/raw/mask_logs/rescore_j4000_$M.txt 2>&1 &
done
wait
