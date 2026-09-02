#!/bin/bash
# run.sh — Build and run Companion-AI in Docker.
# Usage: ./run.sh

set -e

# Check for .env file
if [ ! -f .env ]; then
  echo ""
  echo "ERROR: No .env file found."
  echo ""
  echo "Create one with your OpenAI API key:"
  echo ""
  echo "  cp .env.example .env"
  echo "  # Then edit .env and replace 'your_api_key_here' with your real key"
  echo ""
  exit 1
fi

echo "Building Companion-AI Docker image..."
docker build -t companion-ai .

echo ""
echo "Starting Companion-AI..."
echo "  Type /exit to quit."
echo "  Type /memories to see stored facts."
echo "  Type /history to see all facts including superseded ones."
echo "  Type /debug to toggle debug mode."
echo ""

docker run -it --rm \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  -e DB_PATH=/app/data/memory.sqlite \
  companion-ai
