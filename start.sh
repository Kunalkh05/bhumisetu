#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
BHUMI_DIR="$DIR/bhumi-setu"

echo "=========================================================="
echo "          Starting BHUMISETU Platform Services"
echo "=========================================================="

# 1. Start PostgreSQL if not already running
if ! /Applications/Postgres.app/Contents/Versions/15/bin/pg_isready -q 2>/dev/null; then
  echo "Starting PostgreSQL..."
  /Applications/Postgres.app/Contents/Versions/15/bin/pg_ctl \
    -D "$HOME/Library/Application Support/Postgres/var-15" \
    -l "$HOME/Library/Application Support/Postgres/var-15/server.log" start
  sleep 2
fi
echo "✓ PostgreSQL is running on port 5432"

# 2. Start Redis if not already running
if ! redis-cli ping >/dev/null 2>&1; then
  echo "Starting Redis daemon..."
  redis-server --daemonize yes
  sleep 1
fi
echo "✓ Redis is running on port 6379"

# 3. Start MinIO if not already running
if ! curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; then
  echo "Starting MinIO..."
  mkdir -p /tmp/minio-data
  MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin minio server /tmp/minio-data --address ":9000" --console-address ":9001" > /tmp/minio.log 2>&1 &
  sleep 2
fi
echo "✓ MinIO is running on port 9000 (Console: http://localhost:9001)"

# 4. Set Environment Variables
export APP_ENV=development
export LOG_LEVEL=INFO
export DATABASE_URL="postgresql+psycopg://bhumisetu:bhumisetu_dev_password@localhost:5432/bhumisetu"
export REDIS_URL="redis://localhost:6379/0"
export OBJECT_STORAGE_ENDPOINT="http://localhost:9000"
export OBJECT_STORAGE_ACCESS_KEY="minioadmin"
export OBJECT_STORAGE_SECRET_KEY="minioadmin"
export OBJECT_STORAGE_BUCKET="bhumisetu-documents"
export JWT_SECRET="dev-internal-secret-token"
export PYTHONPATH="$BHUMI_DIR/apps/api"

# 5. Run migrations and seed
cd "$BHUMI_DIR/apps/api"
.venv/bin/alembic upgrade head >/dev/null
cd "$DIR"
"$BHUMI_DIR/apps/api/.venv/bin/python" "$BHUMI_DIR/scripts/seed/init_dev_data.py" >/dev/null

echo "✓ Database schema and seeds are up to date"

# 6. Start API Backend (FastAPI / Uvicorn)
echo "Starting FastAPI Backend on http://localhost:8000..."
cd "$BHUMI_DIR/apps/api"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/bhumisetu-api.log 2>&1 &
API_PID=$!
echo $API_PID > /tmp/bhumisetu-api.pid

# 7. Start Web Frontend (Vite)
echo "Starting Officer Portal on http://localhost:5174/officer/..."
cd "$BHUMI_DIR/apps/web"
npm run dev:local > /tmp/bhumisetu-web.log 2>&1 &
WEB_PID=$!
echo $WEB_PID > /tmp/bhumisetu-web.pid

echo ""
echo "=========================================================="
echo "🚀 BHUMISETU is now running!"
echo "=========================================================="
echo "• Officer Portal:   http://localhost:5174/officer/"
echo "• Quick Dev Login:  http://localhost:8000/dev-login (sets cookies & opens portal)"
echo "• Citizen Portal:   http://localhost:8000/c/"
echo "• API Interactive Docs: http://localhost:8000/docs"
echo "• MinIO Console:    http://localhost:9001 (minioadmin / minioadmin)"
echo ""
echo "Logs are streaming to:"
echo "  /tmp/bhumisetu-api.log"
echo "  /tmp/bhumisetu-web.log"
echo "=========================================================="
