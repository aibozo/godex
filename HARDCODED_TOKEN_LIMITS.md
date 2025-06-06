# Hardcoded Token Limits in Cokeydex

This document lists all locations where token limits are hardcoded instead of using the model registry.

## Summary of Findings

The codebase has several places where token limits and context sizes are hardcoded rather than using the model registry's `max_output_tokens` and `context_window` properties.

## Files with Hardcoded Token Limits

### 1. `/agent/orchestrator/manager.py`
- **Line 156**: `max_tokens=16000` - hardcoded for conversation context building
- **Line 249**: `max_tokens: int = 5000` - default parameter in `_build_conversation_context`

### 2. `/agent/memory/summarizer.py`
- **Line 72**: `max_tokens=400` - hardcoded for summarization with OpenAI
- **Line 102**: `max_tokens=400` - hardcoded in Anthropic stub

### 3. `/agent/specialists/enhanced_rag.py`
- **Line 192**: `max_tokens=500` - for query understanding
- **Line 287**: `max_tokens=2000` - for result synthesis
- **Line 363**: `max_tokens=3000` - for codebase analysis
- **Line 409**: `max_tokens=2000` - for building task context

### 4. `/agent/specialists/enhanced_executor.py`
- **Line 129**: `max_tokens=2000` - for task analysis
- **Line 171**: `max_tokens=1500` - for implementation plan creation
- **Line 259**: `max_tokens=4000` - for code generation
- **Line 342**: `max_tokens=1500` - for validation

### 5. `/agent/orchestrator/context_optimizer.py`
- **Line 211**: `budget_tokens: 80_000` - hardcoded context budget for executor
- **Line 217**: `budget_tokens: 50_000` - hardcoded context budget for planner
- **Line 223**: `budget_tokens: 100_000` - hardcoded context budget for debugging
- **Line 231**: `budget_tokens: 50_000` - default context budget

### 6. `/agent/orchestrator/cost_optimizer.py`
- **Line 93**: `context_size = 5000` - base context size estimate
- **Line 95**: `context_size = 100_000` - for entire codebase
- **Line 97**: `context_size = 50_000` - for multiple files
- **Line 99**: `context_size = 10_000` - for single file

### 7. Test Files
- `/tests/test_planner.py` - Line 80: `max_tokens: 100` in config
- `/tests/test_executor.py` - Various hardcoded values
- `/tests/test_planner_gemini.py` - Various hardcoded values
- `/tests/test_retrieval.py` - Various hardcoded values

## Recommendations

1. **Create helper functions** in the model registry to get appropriate token limits:
   ```python
   def get_safe_max_tokens(model_id: str, requested_tokens: Optional[int] = None) -> int:
       """Get safe max tokens for a model, respecting its limits."""
       model_info = get_model_info(model_id)
       if not model_info:
           return 4096  # Safe default
       
       if requested_tokens:
           return min(requested_tokens, model_info.max_output_tokens)
       return model_info.max_output_tokens
   ```

2. **Create context budget strategies** based on model capabilities:
   ```python
   def get_context_budget(model_id: str, percentage: float = 0.5) -> int:
       """Get reasonable context budget as percentage of model's context window."""
       model_info = get_model_info(model_id)
       if not model_info:
           return 50000  # Safe default
       
       return int(model_info.context_window * percentage)
   ```

3. **Update all hardcoded values** to use the model registry:
   - Replace hardcoded `max_tokens` with calls to `get_safe_max_tokens()`
   - Replace hardcoded context budgets with calls to `get_context_budget()`
   - Use model-specific limits from the registry

4. **Add configuration options** for default token allocations:
   - Add to `Settings` class in `config.py`:
     - `default_summary_tokens: int = 400`
     - `default_analysis_tokens: int = 2000`
     - `default_generation_tokens: int = 4000`
     - `context_budget_percentage: float = 0.5`

5. **Update the LLM client** to log when token limits are capped (already done in line 93)

## Next Steps

1. Implement the helper functions in `agent/models/registry.py`
2. Update each file to use the registry instead of hardcoded values
3. Add tests to ensure token limits are respected
4. Consider adding warnings when approaching token limits