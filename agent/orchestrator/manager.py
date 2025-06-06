# Central Manager - The orchestrator that talks to human and delegates
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel
import uuid
from datetime import datetime

from agent.config import get_settings
from agent.llm import LLMClient
from agent.models import UsageTracker

class TaskType(Enum):
    PLANNING = "planning"
    CODING = "coding"  
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"

class AgentRole(Enum):
    PLANNER = "planner"
    EXECUTOR = "executor" 
    RAG_SPECIALIST = "rag_specialist"
    REVIEWER = "reviewer"

class WorkRequest(BaseModel):
    """A request from human to the manager"""
    id: str
    description: str
    task_type: TaskType
    priority: int = 1
    context_hints: List[str] = []
    estimated_complexity: int = 1  # 1-5 scale

class AgentTask(BaseModel):
    """A task dispatched to a specific agent"""
    id: str
    request_id: str
    agent_role: AgentRole
    description: str
    context_budget: int
    model_id: str
    parent_task: Optional[str] = None
    dependencies: List[str] = []

class Manager:
    """
    The central orchestrator that:
    1. Talks to the human
    2. Maintains conversation state
    3. Delegates work to specialized agents
    4. Coordinates between agents
    5. Optimizes for cost efficiency
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.conversation_history: List[Dict] = []
        self.active_requests: Dict[str, WorkRequest] = {}
        self.completed_tasks: Dict[str, AgentTask] = {}
        
        # Manager uses Opus 4 for orchestration
        self.llm = LLMClient("claude-opus-4-20250514", component="manager")
        self.usage_tracker = UsageTracker()
        
        # Agent model assignments
        self.agent_models = {
            AgentRole.PLANNER: "o3",  # When available, fallback to O1 or Gemini Pro
            AgentRole.EXECUTOR: "claude-sonnet-4-20250514", 
            AgentRole.RAG_SPECIALIST: "gpt-4.1",  # High context, cheaper
            AgentRole.REVIEWER: "claude-3.5-sonnet-20241022"
        }
    
    def chat(self, human_message: str) -> str:
        """
        Main interface - human talks to manager
        Manager decides whether to:
        1. Answer directly (lightweight)
        2. Delegate to planner
        3. Dispatch executors
        4. Coordinate between agents
        """
        # Add to conversation history
        self.conversation_history.append({
            "role": "human",
            "content": human_message,
            "timestamp": datetime.now()
        })
        
        # Analyze the request
        request_analysis = self._analyze_request(human_message)
        
        if request_analysis["needs_delegation"]:
            return self._handle_complex_request(request_analysis)
        else:
            return self._handle_simple_response(human_message)
    
    def _analyze_request(self, message: str) -> Dict[str, Any]:
        """
        Lightweight analysis to determine if we need to delegate
        Uses manager's model with minimal tokens
        """
        # For simple queries about the manager itself, don't delegate
        message_lower = message.lower()
        if any(word in message_lower for word in ["what model", "who are you", "hi", "hello", "test"]):
            return {
                "needs_delegation": False,
                "task_type": "chat",
                "complexity": 1,
                "estimated_tokens": 100,
                "requires_codebase_context": False,
                "quick_response": None
            }
        
        # For everything else, analyze properly
        analysis_prompt = f"""
        Analyze this request and determine delegation strategy:
        
        Request: {message}
        
        Respond with JSON:
        {{
            "needs_delegation": boolean,
            "task_type": "planning|coding|analysis|debugging|refactoring", 
            "complexity": 1-5,
            "estimated_tokens": number,
            "requires_codebase_context": boolean,
            "description": "brief description of the task"
        }}
        """
        
        response = self.llm.chat_completion([
            {"role": "system", "content": "You are a task analysis specialist. Respond only with valid JSON."},
            {"role": "user", "content": analysis_prompt}
        ], max_tokens=200)
        
        # Parse JSON response
        import json
        try:
            result = json.loads(response)
            result["quick_response"] = None
            return result
        except:
            # Fallback for parsing errors
            return {
                "needs_delegation": False,
                "task_type": "chat",
                "complexity": 1,
                "estimated_tokens": 1000,
                "requires_codebase_context": False,
                "quick_response": None,
                "description": message
            }
    
    def _handle_simple_response(self, message: str) -> str:
        """Handle simple questions that don't need delegation"""
        conversation_context = self._build_conversation_context(max_tokens=2000)
        
        system_msg = """You are the Manager of Cokeydx, a sophisticated coding agent system. 

You coordinate a team of specialized AI agents:
- Planner (uses O3/Gemini Pro for high-level reasoning)
- Executor (uses Claude Sonnet 4 for code implementation) 
- RAG Specialist (uses GPT-4.1 for context gathering)

You run on Claude Opus 4 and act as the central orchestrator. You maintain conversation state, 
decide when to delegate work, and coordinate between agents. Your role is to be helpful,
informative, and decide the best strategy for each request.

Answer naturally and conversationally. Mention your model (Claude Opus 4) if asked directly."""

        user_content = f"""Recent conversation: {conversation_context}

Current message: {message}

Please respond helpfully as the Manager."""
        
        response = self.llm.chat_completion([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content}
        ], max_tokens=500)
        
        self.conversation_history.append({
            "role": "manager", 
            "content": response,
            "timestamp": datetime.now()
        })
        
        return response
    
    def _handle_complex_request(self, analysis: Dict[str, Any]) -> str:
        """Handle complex requests that need delegation"""
        # Create work request
        request = WorkRequest(
            id=str(uuid.uuid4()),
            description=analysis.get("description", "Complex task"),
            task_type=TaskType(analysis["task_type"]),
            estimated_complexity=analysis["complexity"]
        )
        
        self.active_requests[request.id] = request
        
        # Use LLM to generate appropriate response based on task type
        delegation_prompt = f"""As the Manager, explain how you'll handle this request:

Task: {request.description}
Type: {request.task_type.value}
Complexity: {request.estimated_complexity}/5

Available agents:
- Planner (O3/Gemini Pro): For complex reasoning and task breakdown
- Executor (Claude Sonnet 4): For code implementation and tool usage
- RAG Specialist (GPT-4.1): For context gathering and code retrieval

Explain your delegation strategy and what the user can expect. Be conversational and helpful."""

        response = self.llm.chat_completion([
            {"role": "system", "content": "You are the Manager explaining your delegation strategy. Be helpful and clear."},
            {"role": "user", "content": delegation_prompt}
        ], max_tokens=400)
        
        return response
    
    def _delegate_to_planner(self, request: WorkRequest) -> str:
        """Delegate to high-level planner (O3/Gemini Pro)"""
        # This would create a planner task with appropriate context
        planner_task = AgentTask(
            id=str(uuid.uuid4()),
            request_id=request.id,
            agent_role=AgentRole.PLANNER,
            description=f"Create execution plan for: {request.description}",
            context_budget=50_000,
            model_id=self.agent_models[AgentRole.PLANNER]
        )
        
        # TODO: Actually invoke planner
        return f"I'm delegating this to the planner for detailed breakdown. Task ID: {planner_task.id}"
    
    def _orchestrate_coding_task(self, request: WorkRequest) -> str:
        """Orchestrate a coding task through the pipeline"""
        steps = [
            "1. RAG specialist will gather relevant code context",
            "2. Planner will create specific implementation steps", 
            "3. Executor(s) will implement the code",
            "4. I'll coordinate and monitor progress"
        ]
        
        return f"I'm orchestrating this coding task:\n" + "\n".join(steps)
    
    def _build_conversation_context(self, max_tokens: int = 5000) -> str:
        """Build minimal conversation context for manager"""
        # Keep only recent, relevant conversation
        recent_messages = self.conversation_history[-5:]  # Last 5 exchanges
        
        context_parts = []
        for msg in recent_messages:
            role = msg["role"]
            content = msg["content"][:200]  # Truncate to save tokens
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    def get_cost_summary(self) -> str:
        """Get current session cost breakdown by agent role"""
        total_cost = self.usage_tracker.get_today_cost()
        
        # Get breakdown by component
        # TODO: Implement component-wise breakdown
        
        return f"Today's cost: ${total_cost:.4f}"
    
    def get_active_tasks(self) -> str:
        """Get status of active tasks across all agents"""
        if not self.active_requests:
            return "No active tasks"
        
        status_lines = []
        for req_id, request in self.active_requests.items():
            status_lines.append(f"• {request.description} (complexity: {request.estimated_complexity})")
        
        return "Active tasks:\n" + "\n".join(status_lines)