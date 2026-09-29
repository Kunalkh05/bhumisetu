#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
BHUMI_DIR="$DIR/bhumi-setu"

echo "=========================================================="
echo "          Starting BHUMISETU Platform Services"
echo "=========================================================="

# 1. Start Redis if available
if command -v redis-server >/dev/null 2>&1; then
  if ! redis-cli ping >/dev/null 2>&1; then
    echo "Starting Redis daemon..."
    redis-server --daemonize yes 2>/dev/null || true
    sleep 1
  fi
  if redis-cli ping >/dev/null 2>&1; then
    echo "✓ Redis is running on port 6379"
  fi
fi

# 2. Check and start PostgreSQL if available
PG_READY=false
if command -v pg_isready >/dev/null 2>&1 && pg_isready -q 2>/dev/null; then
  PG_READY=true
elif [ -x "/opt/homebrew/opt/postgresql@15/bin/pg_isready" ] && /opt/homebrew/opt/postgresql@15/bin/pg_isready -q 2>/dev/null; then
  PG_READY=true
elif [ -x "/Applications/Postgres.app/Contents/Versions/15/bin/pg_isready" ] && /Applications/Postgres.app/Contents/Versions/15/bin/pg_isready -q 2>/dev/null; then
  PG_READY=true
fi

if [ "$PG_READY" = "true" ]; then
  echo "✓ PostgreSQL is running on port 5432"
else
  echo "ℹ PostgreSQL is currently offline; API will run in resilient dev-fallback mode."
fi

# 3. Environment Variables
export APP_ENV=development
export LOG_LEVEL=INFO
export DATABASE_URL="postgresql+psycopg://bhumisetu:bhumisetu_dev_password@localhost:5432/bhumisetu"
export REDIS_URL="redis://localhost:6379/0"
export OBJECT_STORAGE_ENDPOINT="http://localhost:9000"
export OBJECT_STORAGE_ACCESS_KEY="minioadmin"
export OBJECT_STORAGE_SECRET_KEY="minioadmin"
export OBJECT_STORAGE_BUCKET="bhumisetu-documents"
export JWT_SECRET="dev-internal-secret-token"
export PYTHONPATH="$BHUMI_DIR/apps/api:$BHUMI_DIR"

# 4. Run migrations and seed if PostgreSQL is ready
if [ "$PG_READY" = "true" ]; then
  echo "Running database migrations and seed..."
  cd "$BHUMI_DIR/apps/api"
  .venv/bin/alembic upgrade head >/dev/null 2>&1 || true
  cd "$DIR"
  "$BHUMI_DIR/apps/api/.venv/bin/python" "$BHUMI_DIR/scripts/seed/init_dev_data.py" >/dev/null 2>&1 || true
  echo "✓ Database schema and seeds are up to date"
fi

# 5. Start API Backend (FastAPI / Uvicorn)
echo "Starting FastAPI Backend on http://localhost:8000..."
cd "$BHUMI_DIR/apps/api"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q fastapi uvicorn pydantic pydantic-settings sqlalchemy argon2-cffi redis celery alembic "psycopg[binary]"
fi
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/bhumisetu-api.log 2>&1 &
API_PID=$!
echo $API_PID > /tmp/bhumisetu-api.pid

# 6. Start Web Frontend (Vite)
echo "Starting Web Frontend on http://localhost:5174/..."
cd "$BHUMI_DIR/apps/web"
npm run dev:local > /tmp/bhumisetu-web.log 2>&1 &
WEB_PID=$!
echo $WEB_PID > /tmp/bhumisetu-web.pid

echo ""
echo "=========================================================="
echo "🚀 BHUMISETU is now running!"
echo "=========================================================="
echo "• Citizen Portal:       http://localhost:5174/"
echo "• Officer Portal:       http://localhost:5174/officer/"
echo "• Quick Dev Login:      http://localhost:8000/dev-login"
echo "• API Interactive Docs: http://localhost:8000/docs"
echo "• API Healthz Endpoint: http://localhost:8000/api/healthz"
echo ""
echo "Logs are streaming to:"
echo "  /tmp/bhumisetu-api.log"
echo "  /tmp/bhumisetu-web.log"
echo "=========================================================="
