"""
RAG Specialist Agent - Context retrieval and knowledge synthesis.

Simplified version for testing.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from agent.core.base_agent import BaseAgent
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker


class RAGSpecialist(BaseAgent):
    """
    RAG Specialist agent for context retrieval and knowledge synthesis.
    
    Simplified for testing - focuses on basic search functionality.
    """
    
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model=model, component="rag_specialist")
        
        # RAG-specific state
        self.search_history: List[Dict[str, Any]] = []
        
        # Register with message broker
        self.broker = MessageBroker()
        self.broker.register_agent("rag_specialist", self.handle_request)
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle incoming requests for context and search services.
        """
        try:
            payload = message.payload
            action = payload.get("action", "unknown")
            
            if action == "hybrid_search":
                return self._handle_search_request(payload)
            else:
                return {
                    "status": "received",
                    "message": f"RAG processed action: {action}",
                    "available_actions": ["hybrid_search"]
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing request: {str(e)}"
            }
    
    def _handle_search_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle hybrid search requests."""
        query = payload.get("query", "")
        file_hints = payload.get("file_hints", [])
        max_results = payload.get("max_results", 5)
        
        # Execute actual hybrid search tool
        try:
            result = self.execute_tool("hybrid_search", {
                "query": query,
                "file_hints": file_hints,
                "max_results": max_results
            })
            
            if result.get("exit_code") == 0:
                # Parse the results
                import json
                search_results = json.loads(result.get("stdout", "{}"))
                
                # Track search history
                self.search_history.append({
                    "query": query,
                    "timestamp": datetime.now(),
                    "results_count": len(search_results.get("results", []))
                })
                
                return {
                    "status": "success",
                    "query": query,
                    "results": search_results.get("results", []),
                    "total_searches": len(self.search_history),
                    "tool_response": search_results
                }
            else:
                return {
                    "status": "error",
                    "query": query,
                    "error": result.get("stderr", "Unknown error"),
                    "total_searches": len(self.search_history)
                }
                
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "total_searches": len(self.search_history)
            }