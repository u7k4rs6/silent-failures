#!/bin/sh
# Step 1 of the MASK study: 200 shuffled samples per model, MASK's default judge settings (500 tokens), GLM 5.3 Flash judge.
for M in deepseek-v4-flash gemma-4-31b-it qwen3.8-27b; do
  sh experiment/run_mask.sh $M glm-5.3-flash 200 default_$M --max-connections 5 > data/raw/mask_logs/run_$M.txt 2>&1 &
done
wait
