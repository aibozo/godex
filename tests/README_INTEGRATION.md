# Integration Testing with Real LLMs

## Setting up Gemini

1. Get a free API key from https://makersuite.google.com/app/apikey
2. Set it as an environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

3. Run the Gemini integration tests:
   ```bash
   pytest tests/test_integration_gemini.py -v -s
   ```

## Example: Testing the Planner with Gemini

```python
from agent.planner import Planner

# Set model in .cokeydex.yml:
# model_router_default: "gemini-1.5-flash"

planner = Planner()
plan = planner.generate_plan("Create a REST API with Flask")

for task in plan.tasks:
    print(f"{task.id}: {task.description}")
```

## Testing Tips

- Gemini 1.5 Flash is free up to 1 million tokens per month
- Use `-s` flag with pytest to see print output
- The integration tests will be skipped if GEMINI_API_KEY is not set
- You can also test with OpenAI by setting OPENAI_API_KEY and using "gpt-4o-mini" as the model