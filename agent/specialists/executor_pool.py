"""
Executor Pool - Code generation and task execution.

Uses LLM to generate code and execute tasks.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from agent.core.base_agent import BaseAgent
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker


class ExecutorAgent(BaseAgent):
    """Single executor agent with LLM capabilities."""
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model=model, component="executor")
        self.execution_history: List[Dict[str, Any]] = []
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming requests - required by BaseAgent."""
        # Executor agents are managed by the pool, not directly via messages
        return {"status": "received", "message": "Executor managed by pool"}
    
    def execute_task(self, task_id: str, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a task using LLM and tools."""
        
        # Create code generation prompt
        code_prompt = f"""You are an expert Python developer. Generate code for this task:

Task: {task_description}

Context: {json.dumps(context or {}, indent=2)}

Generate clean, working Python code. If you need to create files, use the write_diff tool.
Think step by step about what needs to be implemented."""

        try:
            # Use LLM to generate implementation plan
            response = self.chat_completion([
                {"role": "system", "content": "You are an expert Python developer. Generate clean, working code."},
                {"role": "user", "content": code_prompt}
            ], temperature=0.3)  # Use model's default max_tokens
            
            # For now, just track that we attempted
            self.execution_history.append({
                "task_id": task_id,
                "description": task_description,
                "timestamp": datetime.now(),
                "llm_response": response[:200] + "..." if len(response) > 200 else response
            })
            
            return {
                "status": "success",
                "task_id": task_id,
                "implementation": response,
                "files_modified": []  # Would track actual file changes
            }
            
        except Exception as e:
            print(f"[Executor] Error executing task: {e}")
            return {
                "status": "error",
                "task_id": task_id,
                "error": str(e)
            }


class ExecutorPool:
    """
    Pool of executor agents for parallel task execution.
    
    Manages multiple ExecutorAgent instances.
    """
    
    def __init__(self, pool_size: int = 2, model: str = "claude-sonnet-4-20250514"):
        self.pool_size = pool_size
        self.executors: List[ExecutorAgent] = []
        self.model = model
        
        # Create executor agents
        for i in range(pool_size):
            self.executors.append(ExecutorAgent(model=model))
        
        # Track overall execution history
        self.execution_history: List[Dict[str, Any]] = []
        
        # Register with message broker
        self.broker = MessageBroker()
        self.broker.register_agent("executor", self.handle_request)
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle incoming execution requests.
        """
        try:
            payload = message.payload
            action = payload.get("action", "unknown")
            
            if action == "execute_task":
                return self._handle_execution_request(payload)
            else:
                return {
                    "status": "received",
                    "message": f"Executor processed action: {action}",
                    "available_actions": ["execute_task"]
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing request: {str(e)}"
            }
    
    def _handle_execution_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task execution request using an available executor."""
        task_id = payload.get("task_id", "")
        task_description = payload.get("task_description", "")
        context = payload.get("context", {})
        
        # Get the least busy executor (simple round-robin for now)
        executor_index = len(self.execution_history) % self.pool_size
        executor = self.executors[executor_index]
        
        # Execute the task
        result = executor.execute_task(task_id, task_description, context)
        
        # Track in pool history
        self.execution_history.append({
            "task_id": task_id,
            "description": task_description,
            "timestamp": datetime.now(),
            "executor_index": executor_index,
            "result": result
        })
        
        return {
            "status": result.get("status", "error"),
            "task_id": task_id,
            "result": result,
            "total_executions": len(self.execution_history)
        }
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get execution status."""
        return {
            "pool_size": self.pool_size,
            "total_executions": len(self.execution_history),
            "status": "active"
        }