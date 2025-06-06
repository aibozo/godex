"""
Enhanced Manager - Advanced orchestrator with multi-agent coordination.

Simplified version for testing. Builds on the base Manager but adds:
- BaseAgent integration
- Agent summary collection and management
- Project creation and planning orchestration
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import uuid

from agent.config import get_settings
from agent.core.base_agent import BaseAgent
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker


class EnhancedManager(BaseAgent):
    """
    Enhanced Manager that orchestrates the entire multi-agent system.
    
    Simplified for testing - focuses on basic orchestration and communication.
    """
    
    def __init__(self):
        # Initialize as manager agent
        super().__init__(
            model="gemini-2.5-flash-preview-05-20",  # Using Gemini 2.5 Flash for cheap testing
            component="manager"
        )
        
        # Manager-specific state
        self.conversation_history: List[Dict[str, Any]] = []
        self.registered_agents: Set[str] = set()
        self.agent_summaries: Dict[str, Dict[str, Any]] = {}
        
        # Initialize message broker and register self
        self.broker = MessageBroker()
        self.broker.register_agent("manager", self.handle_request)
        
        # Session tracking
        self.session_start = datetime.now()
        self.total_requests = 0
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle incoming messages from other agents or the system.
        """
        try:
            payload = message.payload
            action = payload.get("action", "unknown")
            
            if action == "submit_summary":
                return self._handle_summary_submission(payload)
            elif action == "get_status":
                return self._handle_status_request(payload)
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
    
    def chat(self, human_message: str) -> str:
        """
        Enhanced chat function that maintains context and orchestrates agents.
        """
        self.total_requests += 1
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "human",
            "content": human_message,
            "timestamp": datetime.now()
        })
        
        # Simple response for now
        response = f"Enhanced Manager received: {human_message}. Registered agents: {list(self.registered_agents)}"
        
        # Add response to conversation history
        self.conversation_history.append({
            "role": "manager",
            "content": response,
            "timestamp": datetime.now()
        })
        
        return response
    
    def register_agent(self, agent_type: str) -> None:
        """Register an agent with the manager."""
        self.registered_agents.add(agent_type)
        print(f"Manager: Registered agent {agent_type}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the entire system.
        """
        return {
            "manager_status": {
                "session_duration": (datetime.now() - self.session_start).total_seconds(),
                "total_requests": self.total_requests,
                "conversation_turns": len(self.conversation_history),
                "registered_agents": list(self.registered_agents)
            },
            "agent_summaries": self.agent_summaries
        }
    
    def _handle_summary_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent summary submissions."""
        try:
            summary = payload.get("summary", {})
            agent_id = summary.get("agent_id", "unknown")
            self.agent_summaries[agent_id] = summary
            
            return {"status": "received", "timestamp": datetime.now()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _handle_status_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status requests from agents."""
        return self.get_system_status()