#!/bin/bash
# run_tests.sh — Run the full test suite inside Docker.
# Usage: ./run_tests.sh

set -e

echo "Building Companion-AI Docker image..."
docker build -t companion-ai .

echo ""
echo "Running tests..."
echo ""

docker run --rm companion-ai pytest tests/ -v
