#!/bin/bash

# OMNI Quick Start Script
# This script starts the OMNI backend and frontend for testing

echo "🚀 Starting OMNI Multi-Agent System..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: Ollama doesn't seem to be running on localhost:11434${NC}"
    echo "Please start Ollama first: ollama serve"
    echo ""
fi

# Check for required models
echo -e "${BLUE}📋 Checking available Ollama models...${NC}"
MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
if [ -z "$MODELS" ]; then
    echo -e "${YELLOW}⚠️  No models found. You may need to pull models:${NC}"
    echo "  ollama pull llama3.1:8b"
    echo "  ollama pull qwen2.5-coder:14b"
else
    echo "Available models:"
    echo "$MODELS" | head -5 | sed 's/^/  - /'
fi
echo ""

# Start Backend
echo -e "${GREEN}🔧 Starting Backend...${NC}"
cd backend
source ../.venv/bin/activate
export PYTHONPATH=/home/dmoniz/projects/antigravity/agent_orchestrator/omni/backend/src

echo "Installing/updating dependencies..."
pip install -q fastapi uvicorn httpx sqlalchemy asyncpg pyyaml structlog python-multipart 2>/dev/null

echo "Starting FastAPI server on http://localhost:8000"
echo "API docs available at http://localhost:8000/docs"
echo ""

# Start backend in background
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend started successfully
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${YELLOW}⚠️  Backend may not have started properly${NC}"
else
    echo -e "${GREEN}✅ Backend is running!${NC}"
fi

echo ""
cd ..

# Start Frontend
echo -e "${GREEN}🎨 Starting Frontend...${NC}"
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Starting Next.js dev server on http://localhost:3000"
echo ""

# Start frontend in background
npm run dev &
FRONTEND_PID=$!

# Wait for frontend
sleep 5

echo ""
echo -e "${GREEN}✨ OMNI is now running!${NC}"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔌 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Trap Ctrl+C to kill both processes
trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Wait for both processes
wait