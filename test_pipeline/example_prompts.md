# Example Prompts for Testing the Multi-Agent Pipeline

## Simple Project: Calculator

### Prompt 1: Create Calculator Project
"I need a simple Python calculator that can add, subtract, multiply, and divide two numbers. It should have a clean CLI interface."

Expected flow:
1. Manager receives request
2. Manager delegates to Planner for task breakdown
3. Planner creates tasks (create calculator.py, add operations, create CLI, write tests)
4. Manager starts task execution with Executor
5. Executor implements each task with RAG support

### Prompt 2: Add Feature
"Add a square root function to the calculator"

Expected flow:
1. Manager understands context from previous work
2. Delegates to Planner for new task
3. Executor adds the feature
4. Tests are updated

## Medium Project: Todo List App

### Prompt 3: Create Todo App
"Create a simple todo list application in Python that allows users to add, remove, and list tasks. Tasks should be saved to a JSON file."

Expected flow:
1. Manager -> Planner: Break down into tasks
2. Tasks: Create main structure, implement add/remove/list, add persistence, create CLI
3. RAG provides context on JSON handling
4. Executor implements each component

## Test Scenarios

1. **Happy Path**: Simple calculator creation
2. **Context Retention**: Adding features to existing project
3. **Error Handling**: Request with missing details
4. **Multi-file Project**: Todo app with multiple modules