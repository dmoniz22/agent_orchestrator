# MODEL_PLAN.md — Agent Orchestrator

## Central Policy Reference
See the canonical model strategy at:
`/home/dmoniz/.openclaw/workspace-coding/MODEL_PLAN.md`

## Per-Repo Defaults
- **Primary model:** `openrouter/qwen/qwen3.5-35b-a3b`
- **Fallbacks (in order):**
  1. `openrouter/minimax-m2`
  2. `openrouter/kimi-k2.5`
  3. `openrouter/mimi-v2`
- **Switching policy:** priority (prefer primary; fallback if unavailable)

## Project-Specific Notes
- This project supports both Ollama (local) and OpenRouter backends
- The model plan here governs development assistance, not runtime agent models
- Runtime agent models are configured in `omni/CONFIG/models.yaml`
- For architecture review and complex multi-agent debugging, consider Claude Sonnet 4.5

## How to Update
1. Edit this file with new primary/fallback choices
2. Commit and push
3. Central policy remains unchanged unless you also update the workspace MODEL_PLAN.md
