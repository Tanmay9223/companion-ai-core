#!/bin/bash
# run_evals.sh — Run the evaluation harness inside Docker.
# Usage: ./run_evals.sh

set -e

echo "Building Companion-AI Docker image..."
docker build -t companion-ai .

echo ""
echo "Running evaluation harness..."
echo ""

docker run --rm companion-ai python -m eval.run_evals
