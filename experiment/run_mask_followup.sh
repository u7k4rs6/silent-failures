#!/bin/sh
# Step 2 of the MASK study (run after run_mask_all.sh).
# (a) same 200 samples per model, answer limit raised from MASK's default 1,000 to 8,000 tokens;
# (b) the default runs' answers re-judged: identical settings (noise control) and a 4,000-token judge limit.
PY=audit/tests/inspect/.venv/bin/python
for M in deepseek-v4-flash gemma-4-31b-it qwen3.8-27b; do
  sh experiment/run_mask.sh $M glm-5.3-flash 200 gen8k_$M --max-connections 5 --max-tokens 8000 > data/raw/mask_logs/run_gen8k_$M.txt 2>&1 &
done
wait
$PY experiment/mask_study.py rescore glm-5.3-flash 500 rejudge500
$PY experiment/mask_study.py rescore glm-5.3-flash 4000 judge4000
$PY experiment/mask_study.py analyze
