"""
Planner Agent - High-level reasoning and task decomposition.

Uses LLM to create detailed task breakdowns.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re

from agent.core.base_agent import BaseAgent
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker


class PlannerAgent(BaseAgent):
    """
    Planner agent for high-level reasoning and task decomposition.
    
    Uses LLM to analyze requests and create detailed task breakdowns.
    """
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model=model, component="planner")
        
        # Planner-specific state
        self.planning_history: List[Dict[str, Any]] = []
        
        # Register with message broker
        self.broker = MessageBroker()
        self.broker.register_agent("planner", self.handle_request)
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle incoming planning requests.
        """
        try:
            payload = message.payload
            action = payload.get("action", "unknown")
            
            if action == "create_plan":
                return self._handle_plan_creation(payload)
            else:
                return {
                    "status": "received",
                    "message": f"Planner processed action: {action}",
                    "available_actions": ["create_plan"]
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing request: {str(e)}"
            }
    
    def _handle_plan_creation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plan creation requests using LLM."""
        objective = payload.get("objective", "")
        
        # Create planning prompt
        planning_prompt = f"""You are a technical project planner. Break down this request into specific, actionable tasks.

Request: {objective}

Create a detailed task breakdown with:
1. Clear, specific tasks (not vague like "implement everything")
2. Logical order of execution
3. Each task should be independently completable

Return ONLY a JSON object in this exact format (no other text):
{{
    "tasks": [
        {{
            "id": "T-001",
            "description": "specific task description",
            "dependencies": [],
            "estimated_complexity": "low|medium|high"
        }}
    ]
}}"""

        try:
            # Use LLM to create plan
            response = self.chat_completion([
                {"role": "system", "content": "You are a technical project planner. Return only valid JSON."},
                {"role": "user", "content": planning_prompt}
            ], temperature=0.3)  # Use model's default max_tokens
            
            
            # Parse the response
            try:
                plan_data = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    plan_data = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse plan from LLM response")
            
            # Validate plan structure
            if "tasks" not in plan_data or not isinstance(plan_data["tasks"], list):
                raise ValueError("Invalid plan structure")
            
            # Add to history
            self.planning_history.append({
                "objective": objective,
                "plan": plan_data,
                "timestamp": datetime.now()
            })
            
            return {
                "status": "success",
                "objective": objective,
                "plan": plan_data,
                "total_plans": len(self.planning_history)
            }
            
        except Exception as e:
            print(f"[Planner] Error creating plan: {e}")
            
            # Fallback to simple plan
            fallback_plan = {
                "tasks": [
                    {
                        "id": "T-001",
                        "description": f"Implement {objective[:50]}...",
                        "dependencies": [],
                        "estimated_complexity": "medium"
                    }
                ]
            }
            
            self.planning_history.append({
                "objective": objective,
                "plan": fallback_plan,
                "timestamp": datetime.now(),
                "error": str(e)
            })
            
            return {
                "status": "partial",
                "objective": objective,
                "plan": fallback_plan,
                "error": str(e),
                "total_plans": len(self.planning_history)
            }