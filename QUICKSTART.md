# Quick Start Guide

## Prerequisites

1. **Ollama** must be installed and running locally
   - Install: https://ollama.com/download
   - Start: `ollama serve`

2. **Python 3.11+** with virtual environment

3. **Node.js 18+** for frontend

## Running the System

### Option 1: Quick Start Script (Recommended)

```bash
# Make sure Ollama is running first
ollama serve

# In another terminal, run the start script
./start.sh
```

This will:
- Start the FastAPI backend on http://localhost:8000
- Start the Next.js frontend on http://localhost:3000
- Check for Ollama models

### Option 2: Manual Start

**Backend:**
```bash
cd omni/backend
source ../.venv/bin/activate
export PYTHONPATH=/home/dmoniz/projects/antigravity/agent_orchestrator/omni/backend/src
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd omni/frontend
npm install  # First time only
npm run dev
```

### Option 3: Docker Compose

```bash
# Start all services
docker-compose up

# Or in detached mode
docker-compose up -d
```

## Access the Application

Once running, access:

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Testing

### Run Tests
```bash
cd omni/backend
source ../.venv/bin/activate
PYTHONPATH=/home/dmoniz/projects/antigravity/agent_orchestrator/omni/backend/src python -m pytest tests/ -v
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# List agents
curl http://localhost:8000/api/v1/agents/

# List tools
curl http://localhost:8000/api/v1/tools/

# Execute a task
curl -X POST http://localhost:8000/api/v1/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello, how are you?"}'
```

## Troubleshooting

### Ollama Connection Issues
If you see "Failed to connect to Ollama":
1. Ensure Ollama is running: `ollama serve`
2. Check models are available: `ollama list`
3. Pull required models: `ollama pull llama3.1:8b`

### Port Already in Use
If ports 8000 or 3000 are already in use:
```bash
# Find and kill processes
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### Python Dependencies Missing
```bash
cd omni/backend
source ../.venv/bin/activate
pip install fastapi uvicorn httpx sqlalchemy asyncpg pyyaml structlog python-multipart
```

### Node Modules Missing
```bash
cd omni/frontend
npm install
```