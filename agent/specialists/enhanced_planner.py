"""
Enhanced Planner Agent - Integrates with RAG for codebase-aware planning.

This planner can:
- Request codebase analysis from RAG before planning
- Create context-aware plans for existing code
- Handle replanning based on failure feedback
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re

from agent.core.base_agent import BaseAgent
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker


class EnhancedPlannerAgent(BaseAgent):
    """
    Enhanced planner that integrates with RAG for context-aware planning.
    """
    
    PLANNING_SYSTEM_PROMPT = """You are an expert software architect and project planner.
Your role is to create detailed, actionable task breakdowns for software projects.

Key principles:
1. Break down complex tasks into specific, measurable subtasks
2. Consider existing code structure and patterns when available
3. Ensure tasks have clear acceptance criteria
4. Order tasks by logical dependencies
5. Each task should be independently testable"""
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model=model, component="planner")
        
        # Enhanced state tracking
        self.planning_history: List[Dict[str, Any]] = []
        self.codebase_context: Optional[Dict[str, Any]] = None
        self.active_plans: Dict[str, Dict[str, Any]] = {}
        
        # Register with message broker
        self.broker = MessageBroker()
        self.broker.register_agent("planner", self.handle_request)
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming planning requests."""
        try:
            payload = message.payload
            action = payload.get("action", "unknown")
            
            if action == "create_plan":
                return self._handle_plan_creation(payload)
            elif action == "replan":
                return self._handle_replanning(payload)
            elif action == "analyze_existing":
                return self._handle_existing_analysis(payload)
            elif action == "get_status":
                return self._get_status()
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "available_actions": ["create_plan", "replan", "analyze_existing", "get_status"]
                }
                
        except Exception as e:
            import traceback
            return {
                "status": "error",
                "message": f"Error processing request: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    def _handle_plan_creation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new plan, optionally using codebase context."""
        objective = payload.get("objective", "")
        context = payload.get("context", {})
        
        # Check if we need codebase analysis
        codebase_context = context.get("codebase_context")
        if codebase_context:
            # We have context from RAG
            self.codebase_context = codebase_context
        elif self._should_analyze_codebase(objective):
            # Request codebase analysis from RAG
            rag_context = self._request_rag_analysis(objective)
            if rag_context:
                self.codebase_context = rag_context
        
        # Create the plan with available context
        plan = self._create_detailed_plan(objective, context)
        
        # Store the plan
        plan_id = f"PLAN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.active_plans[plan_id] = {
            "objective": objective,
            "plan": plan,
            "created_at": datetime.now(),
            "context": context
        }
        
        return {
            "status": "success",
            "plan_id": plan_id,
            "objective": objective,
            "plan": plan,
            "used_codebase_context": self.codebase_context is not None
        }
    
    def _handle_replanning(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle replanning based on failure feedback."""
        plan_id = payload.get("plan_id")
        failure_info = payload.get("context", {}).get("failure_info", "")
        failed_task_id = payload.get("failed_task_id")
        
        if not plan_id or plan_id not in self.active_plans:
            return {
                "status": "error",
                "message": f"Plan {plan_id} not found"
            }
        
        original_plan = self.active_plans[plan_id]
        
        # Create replanning prompt
        replanning_prompt = f"""A task has failed and we need to adjust the plan.

Original objective: {original_plan['objective']}

Failed task: {failed_task_id}
Failure reason: {failure_info}

Original plan:
{json.dumps(original_plan['plan'], indent=2)}

Create a revised plan that:
1. Addresses the failure reason
2. Provides alternative approaches if the original approach is not viable
3. Maintains the original objective
4. Includes any necessary cleanup or rollback tasks

Return ONLY a JSON object with the revised plan structure."""

        try:
            # Use LLM to create revised plan
            response = self.chat_completion([
                {"role": "system", "content": self.PLANNING_SYSTEM_PROMPT},
                {"role": "user", "content": replanning_prompt}
            ], temperature=0.3)
            
            # Parse response
            revised_plan = self._parse_json_response(response)
            
            # Update the plan
            self.active_plans[plan_id]["plan"] = revised_plan
            self.active_plans[plan_id]["revised_at"] = datetime.now()
            self.active_plans[plan_id]["revision_reason"] = failure_info
            
            return {
                "status": "success",
                "plan_id": plan_id,
                "revised_plan": revised_plan,
                "revision_reason": failure_info
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create revised plan: {str(e)}"
            }
    
    def _handle_existing_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze existing codebase before planning."""
        objective = payload.get("objective", "")
        
        # Request comprehensive analysis from RAG
        rag_context = self._request_rag_analysis(objective, comprehensive=True)
        
        if not rag_context:
            return {
                "status": "error",
                "message": "Failed to analyze codebase"
            }
        
        # Create analysis summary
        analysis_prompt = f"""Based on the codebase analysis, provide insights for planning this objective:

Objective: {objective}

Codebase context:
{json.dumps(rag_context, indent=2)}

Provide:
1. Key existing components that can be reused
2. Patterns and conventions to follow
3. Potential integration points
4. Suggested approach based on existing architecture

Return a JSON object with these insights."""

        try:
            response = self.chat_completion([
                {"role": "system", "content": "You are a software architect analyzing an existing codebase."},
                {"role": "user", "content": analysis_prompt}
            ], temperature=0.3)
            
            insights = self._parse_json_response(response)
            
            return {
                "status": "success",
                "objective": objective,
                "insights": insights,
                "raw_context": rag_context
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to analyze codebase: {str(e)}"
            }
    
    def _should_analyze_codebase(self, objective: str) -> bool:
        """Determine if codebase analysis would be helpful."""
        keywords = ["refactor", "modify", "update", "enhance", "fix", "integrate", "extend", "existing"]
        objective_lower = objective.lower()
        return any(keyword in objective_lower for keyword in keywords)
    
    def _request_rag_analysis(self, objective: str, comprehensive: bool = False) -> Optional[Dict[str, Any]]:
        """Request codebase analysis from RAG specialist."""
        try:
            # Send request to RAG
            message = AgentMessage(
                sender="planner",
                recipient="rag_specialist",
                message_type=MessageType.REQUEST,
                payload={
                    "action": "analyze_codebase" if comprehensive else "hybrid_search",
                    "query": objective,
                    "max_results": 10 if comprehensive else 5,
                    "analysis_type": "planning"
                }
            )
            
            response = self.broker.send_request(message, timeout=15.0)
            
            if response and response.payload.get("status") == "success":
                return {
                    "results": response.payload.get("results", []),
                    "patterns": response.payload.get("patterns", []),
                    "summary": response.payload.get("summary", "")
                }
            else:
                print(f"[Planner] RAG analysis failed: {response}")
                return None
                
        except Exception as e:
            print(f"[Planner] Error requesting RAG analysis: {e}")
            return None
    
    def _create_detailed_plan(self, objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a detailed plan using LLM with all available context."""
        # Build planning prompt
        planning_prompt = f"""Create a detailed task breakdown for this objective:

Objective: {objective}"""

        if self.codebase_context:
            planning_prompt += f"""

Existing codebase context:
- Found {len(self.codebase_context.get('results', []))} relevant files
- Key patterns: {', '.join(self.codebase_context.get('patterns', ['None identified']))}
- Summary: {self.codebase_context.get('summary', 'No summary available')}

Consider the existing code structure and patterns when planning tasks."""

        if context.get("requirements"):
            planning_prompt += f"""

Additional requirements:
{context['requirements']}"""

        planning_prompt += """

Create a task breakdown with:
1. Specific, actionable tasks (each completable in 1-2 hours)
2. Clear dependencies between tasks
3. Acceptance criteria for each task
4. Integration points with existing code (if applicable)

Return ONLY a JSON object in this format:
{
    "summary": "Brief summary of the plan",
    "tasks": [
        {
            "id": "T-001",
            "title": "Short task title",
            "description": "Detailed description of what needs to be done",
            "dependencies": ["T-XXX"],
            "acceptance_criteria": ["Criterion 1", "Criterion 2"],
            "estimated_hours": 1.5,
            "requires_context": true,
            "integration_points": ["file1.py", "file2.py"]
        }
    ],
    "total_estimated_hours": 10.5
}"""

        try:
            # Use LLM to create plan
            response = self.chat_completion([
                {"role": "system", "content": self.PLANNING_SYSTEM_PROMPT},
                {"role": "user", "content": planning_prompt}
            ], temperature=0.3)
            
            # Parse and validate plan
            plan = self._parse_json_response(response)
            
            # Ensure required fields
            if "tasks" not in plan:
                plan["tasks"] = []
            if "summary" not in plan:
                plan["summary"] = f"Task breakdown for: {objective[:100]}"
            
            # Add IDs if missing
            for i, task in enumerate(plan["tasks"]):
                if "id" not in task:
                    task["id"] = f"T-{i+1:03d}"
                if "dependencies" not in task:
                    task["dependencies"] = []
                if "acceptance_criteria" not in task:
                    task["acceptance_criteria"] = ["Task completed successfully"]
            
            # Add to history
            self.planning_history.append({
                "objective": objective,
                "plan": plan,
                "timestamp": datetime.now(),
                "used_context": bool(self.codebase_context)
            })
            
            return plan
            
        except Exception as e:
            print(f"[Planner] Error creating plan: {e}")
            # Return minimal plan as fallback
            return {
                "summary": f"Basic plan for: {objective[:100]}",
                "tasks": [{
                    "id": "T-001",
                    "title": "Implement objective",
                    "description": objective,
                    "dependencies": [],
                    "acceptance_criteria": ["Objective completed"],
                    "estimated_hours": 4.0
                }],
                "total_estimated_hours": 4.0
            }
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling common issues."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON from response")
    
    def _get_status(self) -> Dict[str, Any]:
        """Get current planner status."""
        return {
            "status": "active",
            "total_plans_created": len(self.planning_history),
            "active_plans": len(self.active_plans),
            "has_codebase_context": self.codebase_context is not None,
            "recent_plans": [
                {
                    "objective": plan["objective"][:100],
                    "created_at": plan["timestamp"].isoformat(),
                    "task_count": len(plan["plan"].get("tasks", []))
                }
                for plan in self.planning_history[-5:]
            ]
        }