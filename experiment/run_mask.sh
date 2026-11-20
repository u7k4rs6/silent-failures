#!/bin/sh
# MASK (inspect_evals 0.29.0) on Adaption-hosted models through its OpenAI-compatible endpoint.
# Usage: sh experiment/run_mask.sh <model> <judge> <limit> <tag> [extra inspect args]
# Logs: data/raw/mask_logs/<tag>/ ; the API key is read from .env by inspect.
set -e
M=$1; J=$2; N=$3; TAG=$4; shift 4
export ADAPTION_BASE_URL=https://api.prod.adaptionlabs.ai/api/v1
audit/tests/inspect/.venv/bin/inspect eval inspect_evals/mask \
  --model openai-api/adaption/$M \
  -T binary_judge_model=openai-api/adaption/$J -T numeric_judge_model=openai-api/adaption/$J \
  --limit $N --sample-shuffle 0 --max-connections 8 --no-fail-on-error \
  --log-dir data/raw/mask_logs/$TAG --no-ansi "$@"
