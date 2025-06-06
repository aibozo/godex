# Cokeydex - SOTA Coding Agent Platform Summary

## Project Overview

Cokeydex is a sophisticated multi-agent coding platform that combines safe execution, memory management, and hybrid retrieval capabilities. The system follows a ReAct (Thought → Tool → Observation) execution pattern with reflexion capabilities for self-critique and retry logic.

## Architecture Overview

### Core Pipeline
1. **Human Request** → **Manager** (Orchestrator)
2. **Manager** analyzes complexity and delegates to specialized agents:
   - **Planner** (O3/Gemini Pro) - High-level reasoning and task breakdown
   - **Executor** (Claude Sonnet 4) - Code implementation and tool usage  
   - **RAG Specialist** (GPT-4.1) - Context gathering and code retrieval
3. **Agents** collaborate and return results to **Manager**
4. **Manager** coordinates responses back to human

## Key Components

### 1. Central Orchestrator (`agent/orchestrator/manager.py`)
- **Manager Class**: Central coordination hub running on Claude Opus 4
- **Role**: Human interface, conversation state, task delegation, cost optimization
- **Key Functions**:
  - `chat()` - Main human interface
  - `_analyze_request()` - Determines delegation strategy
  - `_handle_complex_request()` - Multi-agent coordination
  - Agent model assignments and cost tracking

### 2. LLM Abstraction (`agent/llm.py`)
- **LLMClient Class**: Unified interface for multiple providers (OpenAI, Anthropic, Google)
- **Features**:
  - Multi-provider support with automatic routing
  - Token usage tracking and cost monitoring
  - Thinking mode support for advanced reasoning
  - Component-specific usage attribution

### 3. Configuration System (`agent/config.py`)
- **Settings Class**: Pydantic-based configuration management
- **Key Settings**:
  - API keys for all providers
  - Model routing and cost caps
  - Tool permissions and security settings
  - Retrieval system configuration

### 4. Memory Management (`agent/memory/`)
- **Manager** (`manager.py`): Placeholder for markdown scratchpads
- **Summarizer** (`summarizer.py`): GPT-4-nano powered content compression
- **Vector Store** (`vector_store.py`): ChromaDB integration for embeddings
- **Features**:
  - Automatic summarization when content exceeds thresholds
  - Archive management with timestamps
  - Vector search capabilities

### 5. Retrieval System (`agent/retrieval/`)
- **Hybrid Retriever** (`orchestrator.py`): Combines BM25 + vector search
- **BM25 Index** (`bm25_index.py`): TF-IDF based text search with sklearn
- **Pipeline**:
  1. BM25 retrieves top candidates
  2. Vector similarity reranks results
  3. Returns contextually relevant code chunks
- **Chunker** (`chunker.py`): Splits files into searchable segments
- **Embedder** (`embedder.py`): Creates vector representations

### 6. Task Management (`agent/tasks/`)
- **Schema** (`schema.py`): Pydantic models for structured planning
  - `Task`: Individual work units with acceptance tests
  - `Plan`: Collections of tasks with validation
  - `Budget`: Resource constraints (tokens, dollars, time)
- **Manager** (`manager.py`): Plan persistence and merging
  - YAML serialization for machine processing
  - Markdown rendering for human readability

### 7. Tool System (`agent/tools/`)
- **Core** (`core.py`): Safe execution framework
- **Permissions** (`permissions.py`): ACL-based access control
- **Security**: Firejail/Docker sandboxing for safe execution
- **Tool Wrappers** (`tools/`): Individual tool implementations
  - `read_file.py`: Safe file reading with range support
  - `grep.py`: Pattern matching with result limits
  - `run_tests.py`, `static_analyze.py`, etc.

### 8. CLI Interface (`cli/`)
- **Main** (`main.py`): Typer-based command interface
- **Commands**:
  - `chat`: Interactive session with Manager
  - `plan`: Task planning (placeholder)
  - `run`: Task execution (placeholder)
  - `usage`: Cost and usage tracking

## Execution Phases

The system is designed in progressive phases:

### Phase I-III: Foundation ✅
- Basic configuration and settings
- Memory management with summarization
- Vector storage integration

### Phase IV: Retrieval ✅
- BM25 + vector hybrid search
- Code chunking and indexing
- Context optimization

### Phase V: Planning (In Progress)
- Structured task decomposition
- Acceptance test DSL
- Plan persistence and merging

### Phase VI: Execution (Planned)
- ReAct loop implementation
- Tool orchestration
- Diff writing and rollback

### Phase VII+: Advanced Features (Planned)
- Reflexion and self-critique
- Skill library development
- Multi-agent coordination

## Security Model

### Sandboxed Execution
- **Primary**: Firejail containerization
- **Fallback**: Docker containers (`cokeydx-runner:latest`)
- **ACL System**: Configurable tool permissions

### Safe Tool Design
- JSON-based tool interfaces
- Timeout enforcement
- Resource limiting
- Input validation

## Data Flow

### Request Processing
```
Human Message → Manager.chat() → Analysis → Delegation Decision
    ↓
Simple: Direct Manager Response
Complex: Agent Delegation → Specialized Processing → Coordination → Response
```

### Memory Flow
```
Scratchpad Notes → Threshold Check → Summarization → Archive + Vector Storage
                                  ↓
                         Context Retrieval ← Query Processing
```

### Tool Execution
```
Tool Request → ACL Check → Wrapper Location → Sandbox Execution → Response
```

## Model Usage Strategy

- **Manager**: Claude Opus 4 (orchestration, high-level reasoning)
- **Planner**: O3 (when available), fallback to O1/Gemini Pro
- **Executor**: Claude Sonnet 4 (code implementation)
- **RAG Specialist**: GPT-4.1 (high context, cost-effective)
- **Summarizer**: GPT-4-nano (lightweight content compression)

## Current Status

### Implemented ✅
- Multi-provider LLM abstraction with Anthropic, OpenAI, Google support
- Configuration management with Pydantic
- Memory and vector storage foundations
- Hybrid retrieval system (BM25 + vector search)
- Task schema and planning structures
- Safe tool execution framework with sandboxing
- CLI interface with interactive chat
- Message broker for inter-agent communication
- Basic agent implementations (Manager, Planner, RAG, Executor)

### Partially Implemented 🚧
- **Multi-Agent Orchestration**: Agents exist but Manager uses deterministic routing instead of LLM-based tool calling
- **Planning Agent**: Creates plans but doesn't integrate with RAG or handle replanning
- **RAG Specialist**: Performs searches but lacks LLM synthesis capabilities
- **Executor Pool**: Generates code but missing detailed failure reporting and context integration
- **Inter-Agent Communication**: Message broker works but agents don't fully utilize it

### Key Gaps 🔴
- **Manager Orchestration**: Still uses `_parse_intent()` deterministic routing instead of LLM deciding tool calls
- **Agent Tools**: Manager lacks tools to properly orchestrate agents
- **Context Flow**: RAG context doesn't flow properly to Planning/Execution
- **Failure Handling**: No replanning on failures, limited error details
- **Tool Integration**: Agents have limited access to available tools

### Planned 📋
- Replace deterministic orchestration with LLM-based tool calling
- Implement proper Planning-RAG integration for codebase analysis
- Add failure handling and replanning capabilities
- Complete context flow from RAG to execution
- Reflexion capabilities for self-improvement
- Skill library development
- Production deployment features

The platform represents a comprehensive approach to AI-powered software development, emphasizing safety, modularity, and intelligent resource management.