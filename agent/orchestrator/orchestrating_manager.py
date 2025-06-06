"""
Orchestrating Manager - Full orchestration implementation.

This Manager can:
- Parse user intent
- Delegate to appropriate agents
- Track task progress
- Aggregate results
- Maintain conversation context
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
import json
import re

from agent.core.base_agent import BaseAgent
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker


class OrchestratingManager(BaseAgent):
    """
    Manager that actually orchestrates the multi-agent system.
    """
    
    def __init__(self, model: str = "gemini-2.5-flash-preview-05-20"):
        super().__init__(
            model=model,
            component="manager"
        )
        
        # Manager state
        self.conversation_history: List[Dict[str, Any]] = []
        self.registered_agents: Set[str] = set()
        self.agent_summaries: Dict[str, Dict[str, Any]] = {}
        self.active_project: Optional[Dict[str, Any]] = None
        self.task_progress: Dict[str, Dict[str, Any]] = {}
        
        # Initialize broker
        self.broker = MessageBroker()
        self.broker.register_agent("manager", self.handle_request)
        
        # Session tracking
        self.session_start = datetime.now()
        self.total_requests = 0
    
    def register_agent(self, agent_type: str) -> None:
        """Register an agent with the manager."""
        self.registered_agents.add(agent_type)
        print(f"[Manager] Registered agent: {agent_type}")
    
    def chat(self, human_message: str) -> str:
        """
        Process user message and orchestrate agents to fulfill the request.
        """
        self.total_requests += 1
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "human",
            "content": human_message,
            "timestamp": datetime.now()
        })
        
        # Parse intent
        intent = self._parse_intent(human_message)
        print(f"[Manager] Parsed intent: {intent['type']}")
        
        # Orchestrate based on intent
        if intent["type"] == "create_project":
            response = self._handle_create_project(intent)
        elif intent["type"] == "add_feature":
            response = self._handle_add_feature(intent)
        elif intent["type"] == "get_status":
            response = self._handle_get_status(intent)
        elif intent["type"] == "search_codebase":
            response = self._handle_search_codebase(intent)
        else:
            response = self._handle_general_request(intent)
        
        # Add response to history
        self.conversation_history.append({
            "role": "manager",
            "content": response,
            "timestamp": datetime.now()
        })
        
        return response
    
    def _parse_intent(self, message: str) -> Dict[str, Any]:
        """Parse user message to determine intent."""
        message_lower = message.lower()
        
        # Check for codebase search/query requests
        if any(word in message_lower for word in ["search", "query", "find", "understand", "analyze", "look for"]):
            if any(word in message_lower for word in ["codebase", "code", "files", "project", "implementation"]):
                return {
                    "type": "search_codebase",
                    "description": message
                }
        
        # Check for project creation
        if any(word in message_lower for word in ["create", "build", "make", "need"]):
            if any(word in message_lower for word in ["calculator", "app", "project", "program"]):
                return {
                    "type": "create_project",
                    "description": message,
                    "project_type": self._extract_project_type(message)
                }
        
        # Check for feature addition
        if any(word in message_lower for word in ["add", "implement", "include"]):
            return {
                "type": "add_feature",
                "description": message
            }
        
        # Check for status request
        if any(word in message_lower for word in ["status", "progress", "how"]):
            return {
                "type": "get_status",
                "description": message
            }
        
        # Default to general request
        return {
            "type": "general",
            "description": message
        }
    
    def _extract_project_type(self, message: str) -> str:
        """Extract project type from message."""
        if "calculator" in message.lower():
            return "calculator"
        elif "todo" in message.lower():
            return "todo"
        elif "api" in message.lower():
            return "api"
        else:
            return "general"
    
    def _handle_create_project(self, intent: Dict[str, Any]) -> str:
        """Handle project creation request."""
        print("[Manager] Handling project creation...")
        
        # Step 1: Ask Planner to create a plan
        plan = self._get_plan_from_planner(intent["description"])
        
        if not plan:
            return "I encountered an issue creating a plan for your project."
        
        # Step 2: Create project structure
        project_name = f"{intent['project_type']}_project"
        project_created = self._create_project_structure(project_name, intent["project_type"])
        
        if not project_created:
            return "I encountered an issue creating the project structure."
        
        # Step 3: Get context from RAG
        context = self._get_context_from_rag(intent["description"])
        
        # Step 4: Execute tasks with Executor
        results = self._execute_tasks(plan["tasks"], context)
        
        # Step 5: Summarize results
        summary = self._summarize_results(project_name, plan, results)
        
        return summary
    
    def _get_plan_from_planner(self, description: str) -> Optional[Dict[str, Any]]:
        """Request a plan from the Planner agent."""
        try:
            message = AgentMessage(
                sender="manager",
                recipient="planner",
                message_type=MessageType.REQUEST,
                payload={
                    "action": "create_plan",
                    "objective": description
                }
            )
            
            response = self.broker.send_request(message, timeout=30.0)
            
            if response:
                # Response is now an AgentMessage object
                response_payload = response.payload
                if response_payload.get("status") == "success":
                    return response_payload.get("plan", {})
                else:
                    print(f"[Manager] Planner failed: {response_payload}")
            else:
                print(f"[Manager] No response from Planner")
                return None
                
        except Exception as e:
            print(f"[Manager] Error getting plan: {e}")
            return None
    
    def _create_project_structure(self, project_name: str, project_type: str) -> bool:
        """Create project structure using create_project tool."""
        try:
            result = self.execute_tool("create_project", {
                "project_name": project_name,
                "project_type": "python",
                "project_path": "./workspace"
            })
            
            if result.get("exit_code") == 0:
                # Parse created structure
                stdout_data = json.loads(result["stdout"])
                created_data = json.loads(stdout_data["stdout"])
                
                self.active_project = {
                    "name": project_name,
                    "type": project_type,
                    "path": created_data.get("project_path"),
                    "created_at": datetime.now()
                }
                
                print(f"[Manager] Created project at: {self.active_project['path']}")
                return True
            else:
                print(f"[Manager] Failed to create project: {result.get('stderr')}")
                return False
                
        except Exception as e:
            print(f"[Manager] Error creating project: {e}")
            return False
    
    def _get_context_from_rag(self, description: str) -> Dict[str, Any]:
        """Get relevant context from RAG specialist."""
        try:
            message = AgentMessage(
                sender="manager",
                recipient="rag_specialist",
                message_type=MessageType.REQUEST,
                payload={
                    "action": "hybrid_search",
                    "query": description,
                    "max_results": 5
                }
            )
            
            response = self.broker.send_request(message, timeout=30.0)
            
            if response:
                # Response is now an AgentMessage object
                response_payload = response.payload
                if response_payload.get("status") == "success":
                    return {
                        "results": response_payload.get("results", []),
                        "total_found": response_payload.get("total_searches", 0)
                    }
                else:
                    print(f"[Manager] RAG failed: {response_payload}")
                    return {"results": [], "total_found": 0}
            else:
                print(f"[Manager] No response from RAG")
                return {"results": [], "total_found": 0}
                
        except Exception as e:
            print(f"[Manager] Error getting context: {e}")
            return {"results": [], "total_found": 0}
    
    def _execute_tasks(self, tasks: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute tasks using Executor pool."""
        results = []
        
        for task in tasks:
            try:
                message = AgentMessage(
                    sender="manager",
                    recipient="executor",
                    message_type=MessageType.REQUEST,
                    payload={
                        "action": "execute_task",
                        "task_id": task.get("id", "T-001"),
                        "task_description": task.get("description", ""),
                        "context": context
                    }
                )
                
                response = self.broker.send_request(message, timeout=30.0)
                
                if response:
                    # Response is now an AgentMessage object
                    response_payload = response.payload
                    if response_payload.get("status") == "success":
                        results.append({
                            "task_id": task.get("id"),
                            "status": "completed",
                            "result": response_payload
                        })
                        
                        # Track progress
                        self.task_progress[task.get("id")] = {
                            "status": "completed",
                            "completed_at": datetime.now()
                        }
                    else:
                        results.append({
                            "task_id": task.get("id"),
                            "status": "failed",
                            "error": response_payload.get("error", "Unknown error")
                        })
                else:
                    results.append({
                        "task_id": task.get("id"),
                        "status": "failed",
                        "error": "Timeout - no response from executor"
                    })
                    
            except Exception as e:
                print(f"[Manager] Error executing task {task.get('id')}: {e}")
                results.append({
                    "task_id": task.get("id"),
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def _summarize_results(self, project_name: str, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Summarize the results of project creation."""
        completed = sum(1 for r in results if r["status"] == "completed")
        total = len(results)
        
        summary = f"✅ Created project: {project_name}\n\n"
        summary += f"📋 Plan executed with {completed}/{total} tasks completed:\n"
        
        for i, (task, result) in enumerate(zip(plan.get("tasks", []), results), 1):
            status_icon = "✅" if result["status"] == "completed" else "❌"
            summary += f"   {status_icon} Task {i}: {task.get('description', 'Unknown')}\n"
        
        if self.active_project:
            summary += f"\n📁 Project location: {self.active_project['path']}"
        
        return summary
    
    def _handle_search_codebase(self, intent: Dict[str, Any]) -> str:
        """Handle codebase search requests."""
        print("[Manager] Handling codebase search...")
        
        # Get context from RAG
        context = self._get_context_from_rag(intent["description"])
        
        if context["total_found"] == 0:
            return "I searched the codebase but didn't find any relevant results. Try rephrasing your query or being more specific."
        
        # Format the results
        response = f"I found {context['total_found']} relevant results in the codebase:\n\n"
        
        for i, result in enumerate(context["results"], 1):
            file_path = result.get("file", "Unknown file")
            content = result.get("content", "")
            score = result.get("score", 0)
            
            response += f"**{i}. {file_path}** (relevance: {score:.2f})\n"
            if content:
                # Show a preview of the content
                preview = content[:200] + "..." if len(content) > 200 else content
                response += f"   {preview}\n\n"
        
        return response
    
    def _handle_add_feature(self, intent: Dict[str, Any]) -> str:
        """Handle feature addition to existing project."""
        if not self.active_project:
            return "No active project. Please create a project first."
        
        # Similar flow: plan -> context -> execute
        return f"Adding feature to {self.active_project['name']}: {intent['description']}"
    
    def _handle_get_status(self, intent: Dict[str, Any]) -> str:
        """Handle status request."""
        status = self.get_system_status()
        
        response = "📊 System Status:\n"
        response += f"   Active agents: {len(self.registered_agents)}\n"
        response += f"   Session duration: {status['manager_status']['session_duration']:.1f}s\n"
        response += f"   Tasks completed: {len([t for t in self.task_progress.values() if t['status'] == 'completed'])}\n"
        
        if self.active_project:
            response += f"\n📁 Active project: {self.active_project['name']}"
        
        return response
    
    def _handle_general_request(self, intent: Dict[str, Any]) -> str:
        """Handle general requests using LLM."""
        try:
            # Build context from conversation history
            context = []
            for msg in self.conversation_history[-5:]:  # Last 5 messages for context
                if msg.get("role") == "human":
                    context.append({"role": "user", "content": msg["content"]})
                elif msg.get("role") == "manager":
                    context.append({"role": "assistant", "content": msg["content"]})
            
            # Create system prompt with awareness of capabilities
            system_prompt = """You are the Orchestrating Manager of a multi-agent coding system called Cokeydx. 
You coordinate between specialized agents:
- Planner: Creates detailed task breakdowns and project plans
- RAG Specialist: Searches the codebase and retrieves relevant context
- Executor Pool: Implements code and executes tasks

When users ask about the codebase or want to run queries, you should delegate to the appropriate agent.
For general questions, provide helpful and informative responses.
Be concise but friendly.

If the user wants to understand or query the codebase, mention that you can use the RAG Specialist to search for information."""
            
            # Add system message at the beginning
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation context (excluding the current message which is already in history)
            if len(context) > 1:
                messages.extend(context[:-1])
            
            # Add current message
            messages.append({"role": "user", "content": intent["description"]})
            
            # Get LLM response
            response = self.chat_completion(messages, temperature=0.7)
            
            # Check if the response suggests we should delegate
            lower_response = response.lower()
            if any(phrase in lower_response for phrase in ["rag specialist", "search the codebase", "query the codebase", "i can search", "i'll search"]):
                # User likely wants us to actually do a search
                # Parse their original request to see if we should change intent
                user_msg = intent["description"].lower()
                if any(word in user_msg for word in ["search", "query", "find", "understand", "analyze", "look"]):
                    # Get context from RAG
                    context = self._get_context_from_rag(intent["description"])
                    if context["total_found"] > 0:
                        response += f"\n\nI've searched the codebase and found {context['total_found']} relevant results. "
                        response += "The search included information about:\n"
                        for i, result in enumerate(context["results"][:3], 1):
                            response += f"{i}. {result.get('file', 'Unknown file')}\n"
            
            return response
            
        except Exception as e:
            print(f"[Manager] Error in LLM call: {e}")
            import traceback
            traceback.print_exc()
            # Fallback response
            return "I encountered an error processing your request. Please try again."
    
    def handle_request(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming messages from other agents."""
        try:
            payload = message.payload
            action = payload.get("action", "unknown")
            
            if action == "submit_summary":
                return self._handle_summary_submission(payload)
            elif action == "get_status":
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
    
    def _handle_summary_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent summary submissions."""
        try:
            summary = payload.get("summary", {})
            agent_id = summary.get("agent_id", "unknown")
            self.agent_summaries[agent_id] = summary
            
            return {"status": "received", "timestamp": datetime.now()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "manager_status": {
                "session_duration": (datetime.now() - self.session_start).total_seconds(),
                "total_requests": self.total_requests,
                "conversation_turns": len(self.conversation_history),
                "registered_agents": list(self.registered_agents),
                "active_project": self.active_project
            },
            "agent_summaries": self.agent_summaries,
            "task_progress": self.task_progress
        }