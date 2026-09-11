#!/usr/bin/env bash
set -euo pipefail

# Install the models required for local, free-first operation.
echo "Pulling Qwen3 (chat)..."
ollama pull qwen3:8b

echo "Pulling embedding model (for RAG)..."
ollama pull nomic-embed-text

echo "Done. Confirm with: ollama list"