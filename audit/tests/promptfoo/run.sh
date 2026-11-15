#!/bin/sh
# Offline run: no API keys, fake providers only.
cd "$(dirname "$0")"
export PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1 PROMPTFOO_CONFIG_DIR="$PWD/.pfhome" PROMPTFOO_DISABLE_SHARING=1 PROMPTFOO_REQUEST_BACKOFF_MS=10
for c in eval redteam; do
  ./node_modules/.bin/promptfoo eval -c $c.yaml --no-cache --max-concurrency 1 --no-table -o out_$c.json > log_$c.txt 2>&1
  echo "$c exit=$?" >> log_$c.txt
done
