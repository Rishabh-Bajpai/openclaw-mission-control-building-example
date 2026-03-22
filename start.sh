#!/bin/bash

echo "Starting OpenClaw Mission Control..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load backend env
source backend/.env 2>/dev/null || true

# Defaults
BACKEND_PORT=${PORT:-8002}
FRONTEND_PORT=${NEXT_PUBLIC_FRONTEND_PORT:-3002}
API_BASE=${NEXT_PUBLIC_API_URL:-http://localhost:$BACKEND_PORT}

# Start backend
echo -e "${YELLOW}[1/2] Starting Backend (FastAPI) on port $BACKEND_PORT...${NC}"
cd backend
conda run -n openclaw uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!
cd ..

# Wait for backend
sleep 3

# Start frontend with custom port
echo -e "${YELLOW}[2/2] Starting Frontend (Next.js) on port $FRONTEND_PORT...${NC}"
cd frontend
PORT=$FRONTEND_PORT npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}OpenClaw Mission Control is running!${NC}"
echo ""
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "Backend:  http://localhost:$BACKEND_PORT"
echo "API Docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; echo 'Shutting down...'; exit" INT TERM
wait
