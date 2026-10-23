#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Building..."; docker compose -f docker-compose.prod.yml build
echo "Starting..."; docker compose -f docker-compose.prod.yml up -d
echo "Waiting 20s..."; sleep 20
echo "Verifying..."
curl -sf http://localhost:8080/healthz && echo "  [OK] ai-orchestrator"
curl -sf http://localhost:8081/healthz && echo "  [OK] core-api"
curl -sf -o /dev/null -w "  [OK] web (HTTP %{http_code})\n" http://localhost:3000
echo ""
echo "DEPLOYED"
echo "  Web:             http://localhost:3000"
echo "  AI orchestrator: http://localhost:8080/healthz"
echo "  Core API:        http://localhost:8081/healthz"
