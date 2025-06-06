"""
LLM-based Orchestrating Manager - True orchestration using LLM tool calling.

This Manager uses the LLM to decide which agents to invoke rather than
deterministic routing, enabling dynamic workflow based on conversation context.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import json
import traceback
from pathlib import Path

from agent.core.base_agent import BaseAgent
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker


class LLMOrchestratingManager(BaseAgent):
    """
    Manager that uses LLM-based tool calling for true orchestration.
    """
    
    SYSTEM_PROMPT = """You are the Orchestrating Manager of Cokeydx, a sophisticated multi-agent coding system.

## YOUR ROLE
You are the central orchestrator and the ONLY agent that communicates with the user. Your job is to:
1. Understand user requests through natural conversation
2. Intelligently route tasks to specialized agents based on the request
3. Coordinate multi-agent workflows when needed
4. Monitor progress and handle failures gracefully
5. Present all results back to the user in a clear, conversational manner

## YOUR SPECIALIZED AGENTS

### 1. RAG Agent (Retrieval-Augmented Generation Specialist)
**Capabilities:**
- Searches through the entire codebase using hybrid search (semantic + keyword)
- Analyzes code patterns, architecture, and conventions
- Understands relationships between files and components
- Provides contextual information about existing code
- Can do deep dives into specific files or broad analysis across the project

**When to use RAG:**
- User asks about existing code ("how does X work?", "where is Y implemented?")
- Before making changes to understand current implementation
- To gather context for the Executor (find similar code, patterns, dependencies)
- To analyze the overall architecture or specific subsystems
- When you need to understand coding conventions and patterns

### 2. Planner Agent
**Capabilities:**
- Breaks down complex requests into manageable tasks
- Creates structured project plans with dependencies
- Can request codebase analysis from RAG for informed planning
- Handles replanning when tasks fail
- Understands task sequencing and prerequisites

**When to use Planner:**
- User requests a complex feature requiring multiple steps
- Projects that need careful sequencing (e.g., "refactor the auth system")
- When you need to break down vague requests into concrete tasks
- For anything requiring more than 2-3 implementation steps
- When dependencies between tasks need to be managed

### 3. Executor Agent
**Capabilities:**
- Writes actual code based on specifications
- Modifies existing files or creates new ones
- Runs tests and validates implementations
- Uses various coding tools (read, write, grep, static analysis)
- Can work with context from RAG to match coding patterns

**When to use Executor DIRECTLY (skip planning):**
- Simple, well-defined coding tasks ("add a function to do X")
- Bug fixes with clear descriptions
- Small feature additions (single file/function)
- Code formatting or simple refactoring
- When the user gives specific implementation instructions

**When to use Executor AFTER planning:**
- When implementing tasks from a plan
- Complex features requiring multiple file changes
- When you have context from RAG about patterns to follow

## YOUR TOOLS

### message_rag
Use this to request codebase analysis. The RAG agent can:
- **"search"**: Find specific code, functions, classes
- **"analyze"**: Deep analysis of architecture, patterns, or subsystems  
- **"build_context"**: Gather all relevant context for a specific task

Examples:
- "Search for authentication implementations"
- "Analyze the database layer architecture"
- "Build context for adding a new API endpoint"

### message_planner
Use this to create or modify plans. The planner can:
- **"create_plan"**: Break down a complex request
- **"replan"**: Adjust plan based on failures
- **"analyze_existing"**: Review and improve an existing plan

Examples:
- "Create a plan to add user notifications feature"
- "Replan after test failures in task 3"

### message_executor
Use this to implement code. Send:
- **task_id**: Unique identifier for tracking
- **task_description**: Clear, specific instructions
- **context**: (Optional) Context from RAG about patterns, dependencies
- **acceptance_criteria**: (Optional) How to verify success

Examples:
- Simple: "Create a utils function to validate email addresses"
- With context: "Add a new endpoint following the existing patterns"

### coordinate_agents
Use this for complex multi-agent workflows:
- **"plan_with_context"**: RAG analysis → Planning
- **"execute_with_validation"**: Implementation → Testing
- **"analyze_and_refactor"**: Analysis → Refactoring plan

### get_agent_status
Quick health check on any agent. Useful for debugging.

## DECISION FLOWCHART

1. **User asks about existing code?** → Use RAG to search/analyze
2. **User requests a simple coding task?** → Use Executor directly
3. **User requests a complex feature?** → Use Planner → RAG (for context) → Executor
4. **User reports an error?** → Use RAG to investigate → Executor to fix
5. **User wants refactoring?** → RAG (analyze) → Planner → Executor

## IMPORTANT PATTERNS

### Pattern 1: Simple Task (Direct to Executor)
User: "Add a function to calculate the fibonacci sequence"
You: message_executor with clear task description

### Pattern 2: Contextual Task (RAG → Executor)
User: "Add a new endpoint like the existing ones"
You: message_rag to find patterns → message_executor with context

### Pattern 3: Complex Feature (Full Pipeline)
User: "Add a caching layer to the application"
You: message_planner to break down → message_rag for each component → message_executor for implementation

### Pattern 4: Investigation (RAG-heavy)
User: "Why is the login slow?"
You: message_rag to analyze auth flow → identify bottlenecks → suggest fixes

## ERROR HANDLING

- If RAG times out: It's analyzing a lot of code. Be patient or narrow the search
- If Planner fails: Usually needs clearer objectives or context
- If Executor fails: Often needs better context or clearer requirements
- Always explain failures to the user and suggest next steps

## CONVERSATION STYLE

- Be conversational but concise
- Explain what you're doing and why
- Share interesting findings from the agents
- If something will take time, set expectations
- Present technical information in an accessible way

Remember: You're the conductor of this orchestra. Use your agents wisely, and always keep the user informed about what's happening behind the scenes."""

    def __init__(self, model: str = "gemini-2.5-flash-preview-05-20"):
        # This manager now supports both Claude and Gemini for tool calling
        super().__init__(
            model=model,
            component="manager"
        )
        
        # Manager state
        self.conversation_history: List[Dict[str, Any]] = []
        self.registered_agents: Set[str] = set()
        self.active_plan: Optional[Dict[str, Any]] = None
        self.task_progress: Dict[str, Dict[str, Any]] = {}
        self.current_context: Optional[Dict[str, Any]] = None
        
        # Initialize broker
        self.broker = MessageBroker()
        self.broker.register_agent("manager", self.handle_request)
        
        # Session tracking
        self.session_start = datetime.now()
        self.total_requests = 0
        
        # Tool definitions for LLM
        self.tool_definitions = self._get_tool_definitions()
    
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Define tools available to the Manager for LLM tool calling."""
        return [
            {
                "name": "message_planner",
                "description": "Send a request to the Planning Agent to break down complex tasks into manageable steps. Use for multi-step features, refactoring projects, or anything requiring careful sequencing. NOT needed for simple one-off coding tasks.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create_plan", "replan", "analyze_existing"],
                            "description": "Action for the planner"
                        },
                        "objective": {
                            "type": "string",
                            "description": "The objective or task description"
                        },
                        "context": {
                            "type": "object",
                            "description": "Optional context (e.g., failure info, codebase analysis)",
                            "properties": {
                                "failure_info": {"type": "string"},
                                "codebase_context": {"type": "object"},
                                "existing_plan": {"type": "object"}
                            }
                        }
                    },
                    "required": ["action", "objective"]
                }
            },
            {
                "name": "message_rag",
                "description": "Send a request to the RAG Specialist to search and analyze the codebase. Use to understand existing code, find implementations, discover patterns, or gather context before making changes. Essential for 'how does X work?' or 'where is Y?' questions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["search", "analyze", "build_context"],
                            "description": "Action for the RAG agent"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query or analysis request"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5
                        },
                        "context_type": {
                            "type": "string",
                            "enum": ["planning", "execution", "general"],
                            "description": "Type of context needed"
                        }
                    },
                    "required": ["action", "query"]
                }
            },
            {
                "name": "message_executor",
                "description": "Send a coding task DIRECTLY to the Executor Agent. Use this for ANY coding request: writing functions, fixing bugs, adding features, modifying files. Can handle both simple tasks ('add a function') and complex implementations (when you have a plan or context). This is your primary tool for getting code written.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Unique task identifier"
                        },
                        "task_description": {
                            "type": "string",
                            "description": "Detailed task description"
                        },
                        "context": {
                            "type": "object",
                            "description": "Relevant context from RAG",
                            "properties": {
                                "relevant_files": {"type": "array", "items": {"type": "object"}},
                                "patterns": {"type": "array", "items": {"type": "string"}},
                                "dependencies": {"type": "array", "items": {"type": "string"}}
                            }
                        },
                        "acceptance_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Criteria for task completion"
                        }
                    },
                    "required": ["task_id", "task_description"]
                }
            },
            {
                "name": "get_agent_status",
                "description": "Check if a specific agent is running and available. Mainly for debugging when agents aren't responding. Not typically needed during normal operations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_type": {
                            "type": "string",
                            "enum": ["planner", "rag", "executor"],
                            "description": "Type of agent to check"
                        }
                    },
                    "required": ["agent_type"]
                }
            },
            {
                "name": "coordinate_agents",
                "description": "Coordinate multiple agents in a pre-defined workflow. Use this for common patterns like 'analyze then plan' or 'implement then validate'. This is a convenience tool for workflows that require specific agent sequencing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workflow_type": {
                            "type": "string",
                            "enum": ["plan_with_context", "execute_with_validation", "analyze_and_refactor"],
                            "description": "Type of multi-agent workflow"
                        },
                        "workflow_data": {
                            "type": "object",
                            "description": "Data specific to the workflow"
                        }
                    },
                    "required": ["workflow_type", "workflow_data"]
                }
            }
        ]
    
    def chat(self, human_message: str) -> str:
        """
        Process user message using LLM-based orchestration.
        """
        self.total_requests += 1
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "human",
            "content": human_message,
            "timestamp": datetime.now()
        })
        
        try:
            # Build messages for LLM
            messages = self._build_conversation_messages()
            
            # Get LLM response with tool calling
            response, had_tool_calls = self._get_llm_response_with_tools(messages)
            
            # Add response to history
            self.conversation_history.append({
                "role": "manager",
                "content": response,
                "timestamp": datetime.now(),
                "had_tool_calls": had_tool_calls
            })
            
            return response
            
        except Exception as e:
            error_msg = f"I encountered an error processing your request: {str(e)}"
            print(f"[Manager] Error in chat: {e}")
            traceback.print_exc()
            
            # Add error response to history to maintain conversation flow
            self.conversation_history.append({
                "role": "manager",
                "content": error_msg,
                "timestamp": datetime.now(),
                "had_tool_calls": False
            })
            
            return error_msg
    
    def _build_conversation_messages(self) -> List[Dict[str, Any]]:
        """Build message list for LLM including conversation history."""
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        # Add recent conversation history (last 10 messages)
        # We need to ensure proper user/assistant alternation
        history_entries = self.conversation_history[-10:]
        
        # Process history to ensure proper message alternation
        last_role = "system"
        for entry in history_entries:
            if entry["role"] == "human":
                # Always add user messages
                messages.append({"role": "user", "content": entry["content"]})
                last_role = "user"
            elif entry["role"] == "manager":
                # Only add manager messages if the last message was from user
                # This prevents having assistant messages without intervening user messages
                if last_role == "user":
                    messages.append({
                        "role": "assistant", 
                        "content": str(entry["content"])
                    })
                    last_role = "assistant"
        
        # Ensure we don't end with an assistant message
        # The current human message will be added as the last message
        if len(messages) > 1 and messages[-1]["role"] == "assistant":
            # Keep messages up to the last user message
            for i in range(len(messages) - 1, 0, -1):
                if messages[i]["role"] == "user":
                    messages = messages[:i + 1]
                    break
        
        return messages
    
    def _get_llm_response_with_tools(self, messages: List[Dict[str, Any]]) -> tuple[str, bool]:
        """Get LLM response, handling multiple rounds of tool calls if needed.
        Returns: (response_text, had_tool_calls)
        """
        # Create a deep copy of messages for tool execution to avoid polluting history
        import copy
        tool_messages = copy.deepcopy(messages)
        
        # Track if we made any tool calls
        made_tool_calls = False
        
        # Allow up to 5 rounds of tool calls to prevent infinite loops
        max_rounds = 5
        rounds = 0
        
        while rounds < max_rounds:
            rounds += 1
            
            # Get response from LLM with tools available
            response = self.llm.chat_completion(
                tool_messages,
                tools=self.tool_definitions,
                temperature=0.7
            )
            
            # Check if LLM wants to use tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                made_tool_calls = True
                
                # Process tool calls
                tool_results = []
                tool_calls_list = []
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    print(f"[Manager] Round {rounds} - Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Execute the tool
                    result = self._execute_orchestration_tool(tool_name, tool_args)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(result)
                    })
                    
                    # Store tool call info for message history
                    tool_calls_list.append({
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args)
                        }
                    })
                
                # Add assistant message with tool calls to tool_messages
                tool_messages.append({
                    "role": "assistant",
                    "content": response.content if hasattr(response, 'content') and response.content else "",
                    "tool_calls": tool_calls_list
                })
                
                # Add tool results to tool_messages
                for result in tool_results:
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["output"]
                    })
                
                # Continue loop to potentially make more tool calls
                continue
            
            else:
                # No tool calls - return the response
                if isinstance(response, str):
                    return response, made_tool_calls
                elif hasattr(response, 'content'):
                    return response.content or "", made_tool_calls
                else:
                    return str(response), made_tool_calls
        
        # Max rounds reached - get final response without tools
        print(f"[Manager] Reached max rounds ({max_rounds}) of tool calls")
        final_response = self.llm.chat_completion(tool_messages, temperature=0.7)
        
        if isinstance(final_response, str):
            return final_response, made_tool_calls
        elif hasattr(final_response, 'content'):
            return final_response.content or "", made_tool_calls
        else:
            return str(final_response), made_tool_calls
    
    def _execute_orchestration_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an orchestration tool."""
        try:
            if tool_name == "message_planner":
                return self._message_planner(args)
            elif tool_name == "message_rag":
                return self._message_rag(args)
            elif tool_name == "message_executor":
                return self._message_executor(args)
            elif tool_name == "get_agent_status":
                return self._get_agent_status(args)
            elif tool_name == "coordinate_agents":
                return self._coordinate_agents(args)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}", "traceback": traceback.format_exc()}
    
    def _message_planner(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to Planning Agent."""
        try:
            message = AgentMessage(
                sender="manager",
                recipient="planner",
                message_type=MessageType.REQUEST,
                payload={
                    "action": args["action"],
                    "objective": args["objective"],
                    "context": args.get("context", {})
                }
            )
            
            response = self.broker.send_request(message, timeout=180.0)  # 3 minutes for complex planning operations
            
            if response:
                result = response.payload
                # Store plan if created
                if result.get("status") == "success" and "plan" in result:
                    self.active_plan = result["plan"]
                return result
            else:
                return {"status": "error", "message": "No response from Planner"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _message_rag(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to RAG Specialist."""
        try:
            # Map high-level actions to specific tool calls
            if args["action"] == "search":
                payload = {
                    "action": "hybrid_search",
                    "query": args["query"],
                    "max_results": args.get("max_results", 5)
                }
            elif args["action"] == "analyze":
                payload = {
                    "action": "analyze_codebase",
                    "query": args["query"],
                    "analysis_type": args.get("context_type", "general")
                }
            elif args["action"] == "build_context":
                payload = {
                    "action": "build_context",
                    "task_description": args["query"],  # RAG expects task_description not query
                    "context_type": args.get("context_type", "execution")
                }
            else:
                payload = args
            
            message = AgentMessage(
                sender="manager",
                recipient="rag_specialist",
                message_type=MessageType.REQUEST,
                payload=payload
            )
            
            response = self.broker.send_request(message, timeout=120.0)  # 2 minutes for complex RAG operations
            
            if response:
                result = response.payload
                # Store context if built
                if result.get("status") == "success" and "context" in result:
                    self.current_context = result["context"]
                return result
            else:
                return {"status": "error", "message": "No response from RAG"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _message_executor(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to Executor Agent."""
        try:
            # Include current context if available
            if self.current_context and "context" not in args:
                args["context"] = self.current_context
            
            message = AgentMessage(
                sender="manager",
                recipient="executor",
                message_type=MessageType.REQUEST,
                payload={
                    "action": "execute_task",
                    **args
                }
            )
            
            response = self.broker.send_request(message, timeout=180.0)  # 3 minutes for complex execution tasks
            
            if response:
                result = response.payload
                # Track task progress
                self.task_progress[args["task_id"]] = {
                    "status": result.get("status", "unknown"),
                    "completed_at": datetime.now() if result.get("status") == "success" else None,
                    "error": result.get("error") if result.get("status") == "failed" else None
                }
                return result
            else:
                return {"status": "error", "message": "No response from Executor"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _get_agent_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get status of a specific agent."""
        try:
            agent_type = args["agent_type"]
            
            # Check if agent is registered
            if agent_type not in self.registered_agents:
                return {"status": "not_registered", "agent_type": agent_type}
            
            # Send status request
            message = AgentMessage(
                sender="manager",
                recipient=agent_type,
                message_type=MessageType.REQUEST,
                payload={"action": "get_status"}
            )
            
            response = self.broker.send_request(message, timeout=5.0)
            
            if response:
                return response.payload
            else:
                return {"status": "no_response", "agent_type": agent_type}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _coordinate_agents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate multiple agents for complex workflows."""
        workflow_type = args["workflow_type"]
        workflow_data = args["workflow_data"]
        
        try:
            if workflow_type == "plan_with_context":
                # First get context, then create plan
                rag_result = self._message_rag({
                    "action": "analyze",
                    "query": workflow_data.get("objective", ""),
                    "context_type": "planning"
                })
                
                if rag_result.get("status") == "success":
                    planner_result = self._message_planner({
                        "action": "create_plan",
                        "objective": workflow_data.get("objective", ""),
                        "context": {"codebase_context": rag_result}
                    })
                    return {
                        "status": "success",
                        "rag_result": rag_result,
                        "planner_result": planner_result
                    }
                else:
                    return {"status": "failed", "error": "RAG analysis failed"}
                    
            elif workflow_type == "execute_with_validation":
                # Execute task and validate results
                executor_result = self._message_executor(workflow_data)
                
                if executor_result.get("status") == "success":
                    # Could add validation step here
                    return {
                        "status": "success",
                        "executor_result": executor_result
                    }
                else:
                    return {"status": "failed", "error": "Execution failed", "details": executor_result}
                    
            elif workflow_type == "analyze_and_refactor":
                # Analyze codebase and plan refactoring
                rag_result = self._message_rag({
                    "action": "analyze",
                    "query": workflow_data.get("analysis_query", ""),
                    "context_type": "refactoring"
                })
                
                if rag_result.get("status") == "success":
                    planner_result = self._message_planner({
                        "action": "create_plan",
                        "objective": f"Refactor based on: {workflow_data.get('refactor_goal', '')}",
                        "context": {"analysis": rag_result}
                    })
                    return {
                        "status": "success",
                        "analysis": rag_result,
                        "refactor_plan": planner_result
                    }
                else:
                    return {"status": "failed", "error": "Analysis failed"}
                    
            else:
                return {"status": "error", "message": f"Unknown workflow type: {workflow_type}"}
                
        except Exception as e:
            return {"status": "error", "message": f"Workflow failed: {str(e)}"}
    
    def register_agent(self, agent_type: str) -> None:
        """Register an agent with the manager."""
        self.registered_agents.add(agent_type)
        print(f"[Manager] Registered agent: {agent_type}")
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming messages from other agents."""
        try:
            payload = message.payload
            action = payload.get("action", "unknown")
            
            if action == "report_progress":
                return self._handle_progress_report(payload)
            elif action == "report_failure":
                return self._handle_failure_report(payload)
            elif action == "get_system_status":
                return self.get_system_status()
            else:
                return {
                    "status": "received",
                    "message": f"Processed action: {action}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error handling request: {str(e)}"
            }
    
    def _handle_progress_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle progress reports from agents."""
        task_id = payload.get("task_id")
        progress = payload.get("progress", {})
        
        if task_id:
            self.task_progress[task_id] = {
                **self.task_progress.get(task_id, {}),
                **progress,
                "last_update": datetime.now()
            }
        
        return {"status": "acknowledged"}
    
    def _handle_failure_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failure reports from agents."""
        task_id = payload.get("task_id")
        error_info = payload.get("error_info", {})
        
        if task_id:
            self.task_progress[task_id] = {
                "status": "failed",
                "error": error_info,
                "failed_at": datetime.now()
            }
        
        # Could trigger replanning here
        return {"status": "acknowledged", "action": "will_consider_replanning"}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "manager_status": {
                "session_duration": (datetime.now() - self.session_start).total_seconds(),
                "total_requests": self.total_requests,
                "conversation_turns": len(self.conversation_history),
                "registered_agents": list(self.registered_agents),
                "active_plan": self.active_plan is not None,
                "tasks_in_progress": len([t for t in self.task_progress.values() if t.get("status") == "in_progress"]),
                "tasks_completed": len([t for t in self.task_progress.values() if t.get("status") == "success"]),
                "tasks_failed": len([t for t in self.task_progress.values() if t.get("status") == "failed"])
            },
            "task_progress": self.task_progress
        }