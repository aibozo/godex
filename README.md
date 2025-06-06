# Cokeydex

A full-stack SOTA coding agent platform with safe execution, memory management, and hybrid retrieval capabilities.

## Features

- **Safe Tool Execution**: ACL-based permissions with sandboxed execution via Firejail/Docker
- **Memory Management**: Markdown scratchpads with automatic summarization and vector storage
- **Hybrid Retrieval**: BM25 + vector search for code understanding
- **Task Planning**: Structured task objects with acceptance tests
- **ReAct Loop**: Thought → Tool → Observation execution pattern
- **Reflexion**: Self-critique and retry logic
- **Skill Library**: Reusable code patterns and solutions

## Quick Start

```bash
# Install dependencies
poetry install

# Initialize a new project
poetry run cokeydex new my-project

# Run the CLI
poetry run cokeydex --help
```

## Configuration

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

Create a `.cokeydex.yml` in your project root to configure agent settings.

## Development

```bash
# Run tests
poetry run pytest

# Lint code
poetry run ruff .

# Format code
poetry run black .
```

## License

MIT