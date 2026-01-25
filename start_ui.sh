#!/bin/bash

# MindsDB UI Startup Script
# This script starts both the backend and frontend servers

echo "╔══════════════════════════════════════════════════════════╗"
echo "║         MindsDB UI - Data Source Manager                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if MindsDB is running
echo -e "${BLUE}Checking MindsDB server...${NC}"
if curl -s http://127.0.0.1:47334/api/sql/query > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MindsDB server is running at http://127.0.0.1:47334${NC}"
else
    echo "⚠ MindsDB server is not running. Please start it first:"
    echo "  docker run -p 47334:47334 mindsdb/mindsdb"
    echo ""
fi

# Start Backend
echo ""
echo -e "${BLUE}Starting FastAPI Backend...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started at http://localhost:8000${NC}"
echo "  API Docs: http://localhost:8000/docs"

# Start Frontend
echo ""
echo -e "${BLUE}Starting Vue.js Frontend...${NC}"
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started at http://localhost:5173${NC}"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Services Started:                                       ║"
echo "║  - Backend:  http://localhost:8000 (API: /docs)          ║"
echo "║  - Frontend: http://localhost:5173                       ║"
echo "║  - MindsDB:  http://localhost:47334                      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Press Ctrl+C to stop all services                       ║"
echo "╚══════════════════════════════════════════════════════════╝"

# Handle cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Done."
}

trap cleanup EXIT

# Wait for both processes
wait
