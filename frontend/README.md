# OMNI Frontend

Next.js 14+ frontend for the OMNI (Ollama Multi-agent Network Interface) system.

## Features

- **ChatInterface**: Main chat interface for interacting with the multi-agent system
- **AgentPanel**: Direct agent execution and testing
- **ToolTester**: Test individual tools with custom parameters

## Tech Stack

- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS
- React 18+

## Getting Started

### Prerequisites

- Node.js 18+
- Backend API running (see backend README)

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at http://localhost:3000

### Build

```bash
npm run build
npm start
```

## Environment Variables

Create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
src/
  app/
    layout.tsx      # Root layout
    page.tsx        # Main page
    globals.css     # Global styles
  components/
    ChatInterface.tsx   # Main chat component
    AgentPanel.tsx      # Agent execution panel
    ToolTester.tsx      # Tool testing interface
  types/
    index.ts        # TypeScript types
  utils/
    api.ts          # API client functions
```

## API Integration

The frontend connects to the FastAPI backend at the URL specified in `NEXT_PUBLIC_API_URL`. Make sure the backend is running before starting the frontend.