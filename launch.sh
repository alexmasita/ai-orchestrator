#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

echo "Starting ai-orchestrator..."

ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper