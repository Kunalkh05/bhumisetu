#!/bin/bash

echo "Stopping BHUMISETU services..."
if [ -f /tmp/bhumisetu-api.pid ]; then
  kill $(cat /tmp/bhumisetu-api.pid) 2>/dev/null || true
  rm -f /tmp/bhumisetu-api.pid
  echo "✓ FastAPI backend stopped"
fi

if [ -f /tmp/bhumisetu-web.pid ]; then
  kill $(cat /tmp/bhumisetu-web.pid) 2>/dev/null || true
  rm -f /tmp/bhumisetu-web.pid
  echo "✓ Web frontend stopped"
fi

# Also clean up any lingering uvicorn/vite on these ports
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5174 | xargs kill -9 2>/dev/null || true

echo "All dev services stopped."
