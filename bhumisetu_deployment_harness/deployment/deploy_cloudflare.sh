#!/usr/bin/env bash
set -euo pipefail

# BHUMISETU Cloudflare Pages Deploy Script
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_DIR="$REPO_ROOT/bhumi-setu/apps/web"

echo "=== Deploying BHUMISETU Frontend to Cloudflare Pages ==="

# 1. Ensure production build exists
if [[ ! -d "$WEB_DIR/dist" ]]; then
  echo "Building frontend bundle..."
  (cd "$WEB_DIR" && npm run build)
fi

# 2. Check Cloudflare authentication token
if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "ℹ Cloudflare authentication required to deploy via CLI:"
  echo "  Option A: Provide CLOUDFLARE_API_TOKEN in bhumisetu_deployment_harness/.env.harness"
  echo "  Option B: In Cloudflare Dashboard (dash.cloudflare.com):"
  echo "    1. Navigate to: Workers & Pages -> Create Application -> Pages -> Connect to Git"
  echo "    2. Select repository 'bhumisetu'"
  echo "    3. Framework preset: None (or Vite)"
  echo "    4. Root directory: bhumi-setu/apps/web"
  echo "    5. Build command: npm run build"
  echo "    6. Build output directory: dist"
  echo "    7. Click 'Save and Deploy'"
  exit 1
fi

# 3. Deploy build directory to Cloudflare Pages
echo "Uploading dist/ to Cloudflare Pages (project: bhumisetu)..."
npx -y wrangler pages deploy "$WEB_DIR/dist" --project-name bhumisetu --commit-dirty=true
echo "✓ Cloudflare Pages deployment completed!"
