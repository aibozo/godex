# Cokeydex Multi-Agent Architecture

## Overview

Cokeydex is a multi-agent coding system where specialized AI agents collaborate to understand, plan, and implement software projects. The system uses a central orchestrator pattern with message-based communication between agents.

## Core Principles

1. **Single User Interface**: Only the Manager talks to the user
2. **Message-Based Communication**: Agents communicate through a message broker
3. **Iterative Planning**: Plans can be adjusted based on execution feedback
4. **Context-Aware Execution**: Each coding task gets relevant context from RAG

## Agent Roles

### 1. Manager (Orchestrator)
- **Purpose**: Central coordinator and sole user interface
- **Responsibilities**:
  - Communicate with the user
  - Orchestrate other agents via tool calls
  - Monitor task progress
  - Handle success/failure flows
  - Request plan adjustments when needed

### 2. Planning Agent
- **Purpose**: High-level reasoning and task decomposition
- **Responsibilities**:
  - Create task trees for new projects
  - Analyze existing codebases (using RAG) for refactoring
  - Restructure plans based on failure feedback
  - Produce detailed, executable task breakdowns

### 3. RAG Agent(s)
- **Purpose**: Context retrieval and knowledge synthesis
- **Responsibilities**:
  - Index and search existing codebases
  - Build context for Planning Agent (understanding current structure)
  - Build context for Coding Agents (relevant code for each task)
  - Provide semantic search across project files

### 4. Coding Agent(s)
- **Purpose**: Code generation and task execution
- **Responsibilities**:
  - Execute individual tasks from the plan
  - Generate, modify, or refactor code
  - Report success/failure with detailed summaries
  - Use provided context to make informed changes

## Workflow

### Phase 1: Project Discussion
```
User <-> Manager
```
- User describes the project or changes needed
- Manager understands requirements through conversation
- Manager determines if this is a new project or changes to existing code

### Phase 2: Planning
```
Manager -> Planning Agent
Planning Agent -> RAG Agent (if existing codebase)
RAG Agent -> Planning Agent (context about current code)
Planning Agent -> Manager (task tree)
```
- Manager requests a plan from Planning Agent
- For existing codebases:
  - Planning Agent requests codebase analysis from RAG
  - RAG provides understanding of current structure
- Planning Agent creates detailed task tree
- Manager receives completed plan

### Phase 3: User Approval
```
Manager -> User (plan summary)
User -> Manager (approval to proceed)
```
- Manager presents plan summary to user
- User reviews and approves execution
- Execution proceeds in series (for simplicity)

### Phase 4: Task Execution
For each task in series:
```
Manager -> RAG Agent (build context for task N)
RAG Agent -> Manager (relevant context)
Manager -> Coding Agent (task N + context)
Coding Agent -> Manager (success/failure + summary)
```
- Manager requests context for current task
- RAG builds focused context for the specific task
- Manager spawns/messages Coding Agent with task + context
- Coding Agent executes and reports result

### Phase 5: Failure Handling
If a task fails:
```
Manager -> Planning Agent (task failed + reason)
Planning Agent -> Manager (revised plan)
Manager -> User (explain issue + proposed solution)
User -> Manager (approval to continue)
```
- Manager receives failure summary from Coding Agent
- Manager sends failure details to Planning Agent
- Planning Agent restructures remaining tasks
- Manager discusses with user before proceeding

### Phase 6: Success Flow
If a task succeeds:
```
Manager -> User (task completed)
User -> Manager (continue/stop)
```
- Manager informs user of progress
- User decides whether to continue with next task

## Communication Protocol

### Message Types
1. **Task Request**: Manager -> Agent (work to be done)
2. **Context Request**: Manager/Planning -> RAG (need information)
3. **Result Response**: Agent -> Manager (work completed/failed)
4. **Plan Update**: Planning -> Manager (revised task tree)

### Message Flow Rules
- All user communication goes through Manager
- Agents never talk directly to user
- Manager initiates all workflows via tool calls
- Agents respond with structured results
- Failure summaries include enough detail for replanning

## Implementation Notes

### Tool Calling Strategy
- Manager uses LLM-based tool calling (not deterministic parsing)
- Manager decides which agents to invoke based on conversation context
- Tool calls are the primary orchestration mechanism

### Context Management
- RAG maintains indexed codebase for searching
- Context is built specifically for each task
- Context budget is managed to stay within model limits

### Error Handling
- Every agent reports structured success/failure
- Failures include actionable information for replanning
- System maintains resilience through iterative adjustment

## Benefits of This Architecture

1. **Clear Separation of Concerns**: Each agent has a specific role
2. **Flexible Planning**: Plans can adapt based on execution reality
3. **Context-Aware**: Every action is informed by relevant context
4. **User Control**: User approves major decisions through Manager
5. **Resilient**: Failures lead to replanning, not system failure