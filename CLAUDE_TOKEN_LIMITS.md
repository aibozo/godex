# Token Limit Configuration

## Overview
The Cokeydex system now dynamically uses each model's maximum token capacity instead of hardcoded limits. This ensures agents can leverage the full capabilities of their assigned models.

## Implementation

### LLM Client (`agent/llm.py`)
- If `max_tokens` is not specified in a call, the model's full `max_output_tokens` from the registry is used
- The system automatically caps requests that exceed the model's limits
- Logs warnings when token limits are capped

### Model Registry (`agent/models/registry.py`)
Each model has a `max_output_tokens` field that specifies its maximum output capacity:
- Default: 4096 tokens (if not specified)
- Claude Opus 4: 4096 tokens
- Claude Sonnet/3.5: 8192 tokens (needs explicit setting)
- GPT-4o/4.1: 16384 tokens (needs explicit setting)
- O1/O3: 65536-100000 tokens
- Gemini 2.5 Pro/Flash: 65536 tokens
- Gemini 1.5: 8192 tokens (needs explicit setting)

### Agent Code Updates
Removed hardcoded `max_tokens` from:
- `orchestrator/manager.py`: Was 200-2000, now uses model default
- `executor.py`: Was 200-1000, now uses model default
- `specialists/executor_pool.py`: Was 2000, now uses model default
- `specialists/planner_agent.py`: Was 4000, now uses model default

### Exceptions
- `memory/summarizer.py`: Kept at 400 tokens (summaries should be concise)

## Benefits
1. **Model Flexibility**: Different models can be swapped without code changes
2. **Full Capacity**: Agents use the full output capacity of their models
3. **No Bottlenecks**: Removed artificial constraints that limited agent responses
4. **Dynamic Configuration**: Token limits adjust automatically based on the model

## Testing
Run `python test_broker_fix.py` to verify the system works with full token capacity.