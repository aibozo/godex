# 🚀 Cokeydx - Multi-Agent Coding Platform

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/LLM-Multi--Provider-green.svg" alt="Multi-LLM Support">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License">
</p>

Cokeydx is a sophisticated multi-agent coding platform that uses Large Language Models (LLMs) to understand, plan, and implement software projects. It features intelligent orchestration where specialized AI agents collaborate to handle complex coding tasks.

## 🌟 Key Features

### 🤖 Multi-Agent Architecture
- **LLM Orchestrating Manager**: Uses dynamic tool calling to coordinate agents based on intent
- **Enhanced Planner**: Creates context-aware project plans with codebase analysis
- **RAG Specialist**: Performs intelligent code search with pattern recognition
- **Executor Pool**: Implements code with detailed reporting and validation

### 🧠 Intelligent Capabilities
- **Dynamic Orchestration**: Manager uses LLM reasoning instead of deterministic routing
- **Multi-Round Tool Calling**: Supports complex workflows with up to 5 tool call rounds
- **Context-Aware Planning**: Plans are informed by existing codebase patterns
- **Automatic Replanning**: Handles failures gracefully with intelligent retry logic

### 🛠️ Technical Features
- **Multi-LLM Support**: Works with OpenAI, Anthropic Claude, and Google Gemini models
- **Hybrid Retrieval**: Combines BM25 and vector search for code understanding
- **Safe Execution**: ACL-based permissions with sandboxed tool execution
- **Memory Management**: Persistent scratchpads with automatic summarization
- **Cost Optimization**: Configurable model selection for cost/performance balance

## 📋 Prerequisites

- Python 3.10+
- API keys for at least one LLM provider:
  - OpenAI API key
  - Anthropic API key
  - Google Gemini API key

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/cokeydx.git
cd cokeydx

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or using poetry
poetry install
```

### Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Add your API keys to `.env`:
```env
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GEMINI_API_KEY=your-gemini-key
```

3. (Optional) Create `.cokeydex.yml` for custom configuration:
```yaml
# Model selection (defaults to Gemini 2.5 Flash for cost efficiency)
model_router_default: gemini-2.5-flash-preview-05-20
cost_cap_daily: 20.0

# Retrieval settings
retrieval:
  bm25:
    index_dir: bm25_index
  embeddings:
    model: text-embedding-3-small
```

### Basic Usage

```bash
# Start the interactive chat interface
./cokeydx chat-complete interactive

# Example interactions:
You: Can you explain the architecture of this codebase?
# Manager will use RAG to analyze and explain the architecture

You: Create a new REST API endpoint for user authentication
# Manager will coordinate Planner → RAG → Executor to implement

You: Find all error handling patterns in the codebase
# Manager will use RAG to search and analyze patterns
```

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    🎯 LLM Orchestrating Manager                  │
│                        (Intent Analysis)                         │
│                    Uses LLM tool calling to                      │
│                  coordinate specialized agents                   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 🧠 Planner   │    │ 🔍 RAG       │    │ ⚡ Executor  │
│              │    │ Specialist   │    │    Pool      │
├──────────────┤    ├──────────────┤    ├──────────────┤
│ • Task       │    │ • Code       │    │ • Code       │
│   breakdown  │    │   search     │    │   writing    │
│ • Dependency │    │ • Pattern    │    │ • Testing    │
│   analysis   │    │   analysis   │    │ • Validation │
│ • Replanning │    │ • Context    │    │ • Debugging  │
│              │    │   building   │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                    🔄 Message Broker
                  (Async Communication)
```

## 💡 Example Workflows

### 1. Understanding Existing Code
```
User: "How does the authentication system work?"
↓
Manager → RAG Specialist (searches for auth-related code)
↓
RAG analyzes patterns and architecture
↓
Manager presents comprehensive explanation
```

### 2. Implementing New Features
```
User: "Add a caching layer to the API"
↓
Manager → Planner (creates task breakdown)
↓
Planner → RAG (analyzes existing patterns)
↓
Manager → Executor (implements with context)
↓
Executor runs tests and validates
↓
Manager reports completion status
```

### 3. Refactoring Code
```
User: "Refactor the database layer to use repository pattern"
↓
Manager → RAG (analyzes current structure)
↓
Manager → Planner (creates refactoring plan)
↓
Manager → Executor (implements changes)
↓
Automatic testing and validation
```

## 🛠️ Available Commands

### Chat Commands
- `./cokeydx chat-complete interactive` - Full system with all agents
- `./cokeydx chat` - Basic chat interface
- `./cokeydx plan <objective>` - Create a project plan
- `./cokeydx usage` - Check token usage and costs

### Development Commands
- `./cokeydx logs recent` - View recent LLM interactions
- `./cokeydx logs stats` - View usage statistics
- `pytest tests/` - Run test suite
- `ruff .` - Lint code

## 🔧 Advanced Configuration

### Model Selection
Configure models for different agents based on your needs:

```python
# High performance (more expensive)
manager = LLMOrchestratingManager(model="claude-opus-4-20250514")
planner = EnhancedPlannerAgent(model="gpt-4.1-2025-04-14")

# Balanced (default)
manager = LLMOrchestratingManager(model="gemini-2.5-flash-preview-05-20")

# Cost optimized
rag = EnhancedRAGSpecialist(model="gemini-1.5-flash")
```

### Tool Permissions
Control what tools agents can use in `.cokeydex.yml`:

```yaml
tools_allowed:
  - read_file
  - write_diff
  - run_tests
  - static_analyze
  - grep
  - vector_search
```

## 📊 Performance & Costs

| Model | Provider | Input Cost | Output Cost | Best For |
|-------|----------|------------|-------------|----------|
| Gemini 2.5 Flash | Google | $0.15/1M | $3.50/1M | General use (default) |
| Claude Sonnet 4 | Anthropic | $3/1M | $15/1M | Complex reasoning |
| GPT-4o | OpenAI | $2.50/1M | $10/1M | Balanced performance |

Daily cost cap can be configured to prevent unexpected charges.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=agent tests/

# Format code
black .
ruff . --fix
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with LangChain, Pydantic, and various LLM providers
- Inspired by modern agent architectures and AutoGPT patterns
- Special thanks to the open-source community

---

<p align="center">
  Made with ❤️ by the Cokeydx team
</p>