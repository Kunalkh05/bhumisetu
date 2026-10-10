#!/usr/bin/env bash
set -euo pipefail

# BHUMISETU Render Deployment Script
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== Deploying BHUMISETU Backend & Workers to Render ==="

# Option A: Trigger Render Deploy Hook Webhook
if [[ -n "${RENDER_DEPLOY_HOOK:-}" ]]; then
  echo "Triggering Render deployment webhook..."
  curl -sS -X POST "$RENDER_DEPLOY_HOOK"
  echo "✓ Render deploy webhook successfully triggered!"
  exit 0
fi

# Option B: Render Blueprint Guidance
echo "Render Blueprint configuration is ready at: $REPO_ROOT/render.yaml"
echo ""
echo "To activate on Render:"
echo "1. Log in to dashboard.render.com"
echo "2. Click 'New +' -> 'Blueprint'"
echo "3. Connect your GitHub repository 'bhumisetu'"
echo "4. Render will automatically provision:"
echo "   • FastAPI Web Service (using Dockerfile.production)"
echo "   • Celery Worker Service"
echo "   • Managed PostgreSQL (with PostGIS)"
echo "   • Managed Redis"
echo ""
echo "Alternatively, export RENDER_DEPLOY_HOOK in .env.harness to trigger deployments automatically."
