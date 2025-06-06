"""
Base agent class providing common functionality for all specialized agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
import uuid
import datetime

from agent.config import get_settings
from agent.llm import LLMClient
from agent.tools.core import invoke_tool
from agent.tools.registries import get_agent_tools


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the Cokeydx system.
    
    Provides common functionality:
    - Tool execution with permission checking
    - Communication with other agents
    - LLM interaction
    - State management
    """
    
    def __init__(self, model: str, component: str):
        """
        Initialize base agent.
        
        Args:
            model: LLM model to use for this agent
            component: Component name for usage tracking
        """
        self.model = model
        self.component = component
        self.agent_id = str(uuid.uuid4())
        self.settings = get_settings()
        
        # Initialize LLM client
        self.llm = LLMClient(model=model, component=component)
        
        # Get allowed tools for this agent type
        self.allowed_tools = get_agent_tools(component)
        
        # State tracking
        self.conversation_history: List[Dict[str, Any]] = []
        self.active_tasks: Dict[str, Any] = {}
        self.created_at = datetime.datetime.now()
    
    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with permission checking.
        
        Args:
            tool_name: Name of the tool to execute
            args: Arguments to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            PermissionError: If tool not allowed for this agent
            ValueError: If tool execution fails
        """
        # Check if tool is allowed for this agent
        if tool_name not in self.allowed_tools:
            raise PermissionError(
                f"Tool '{tool_name}' not allowed for agent type '{self.component}'"
            )
        
        # Prepare tool request
        tool_request = {
            "name": tool_name,
            "args": args,
            "secure": self._is_secure_tool(tool_name),
            "timeout_seconds": self._get_tool_timeout(tool_name)
        }
        
        # Execute tool
        try:
            import json
            # Convert tool_request dict to JSON string for invoke_tool
            result_json = invoke_tool(json.dumps(tool_request))
            result = json.loads(result_json)
            
            # Log tool execution
            self._log_tool_execution(tool_name, args, result)
            
            return result
        except Exception as e:
            error_result = {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Tool execution failed: {str(e)}"
            }
            self._log_tool_execution(tool_name, args, error_result)
            return error_result
    
    def communicate_with_agent(self, target_agent: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to another agent via the message broker.
        
        Args:
            target_agent: Target agent component name
            message: Message payload
            
        Returns:
            Response from target agent
        """
        # Import here to avoid circular imports
        from agent.communication.broker import MessageBroker
        from agent.communication.protocol import AgentMessage, MessageType
        
        # Create message
        agent_message = AgentMessage(
            sender=self.component,
            recipient=target_agent,
            message_type=MessageType.REQUEST,
            payload=message
        )
        
        # Send via broker
        broker = MessageBroker()
        response = broker.route_message(agent_message)
        
        # Log communication
        self._log_communication(target_agent, message, response)
        
        return response
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Get chat completion from LLM with conversation tracking.
        
        Args:
            messages: Messages in OpenAI format
            **kwargs: Additional arguments for LLM
            
        Returns:
            LLM response content
        """
        # Add agent context to system message if provided
        if messages and messages[0].get("role") == "system":
            system_msg = messages[0]["content"]
            enhanced_system = f"""{system_msg}

You are the {self.component} agent in the Cokeydx multi-agent system.
Your available tools: {', '.join(self.allowed_tools)}
Agent ID: {self.agent_id}"""
            messages[0]["content"] = enhanced_system
        
        # Get response from LLM
        response = self.llm.chat_completion(messages, **kwargs)
        
        # Track conversation
        self.conversation_history.append({
            "timestamp": datetime.datetime.now(),
            "messages": messages,
            "response": response,
            "kwargs": kwargs
        })
        
        return response
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of this agent."""
        return {
            "agent_id": self.agent_id,
            "component": self.component,
            "model": self.model,
            "created_at": self.created_at,
            "active_tasks": len(self.active_tasks),
            "conversation_turns": len(self.conversation_history),
            "allowed_tools": self.allowed_tools
        }
    
    def _is_secure_tool(self, tool_name: str) -> bool:
        """Determine if a tool requires sandboxed execution."""
        # Tools that modify filesystem or execute code need sandboxing
        risky_tools = {
            "write_diff", "run_tests", "static_analyze", 
            "git_operations", "run_command"
        }
        return tool_name in risky_tools
    
    def _get_tool_timeout(self, tool_name: str) -> int:
        """Get timeout for specific tool."""
        # Default timeouts by tool type
        timeouts = {
            "run_tests": 300,  # 5 minutes for tests
            "static_analyze": 120,  # 2 minutes for analysis
            "hybrid_search": 60,  # 1 minute for search
            "build_context": 120,  # 2 minutes for context building
        }
        return timeouts.get(tool_name, 30)  # 30 second default
    
    def _log_tool_execution(self, tool_name: str, args: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Log tool execution for debugging and monitoring."""
        # In production, this could write to structured logs
        if result.get("exit_code", 0) != 0:
            print(f"[{self.component}] Tool {tool_name} failed: {result.get('stderr', 'Unknown error')}")
    
    def _log_communication(self, target: str, message: Dict[str, Any], response: Dict[str, Any]) -> None:
        """Log inter-agent communication."""
        # In production, this could write to structured logs
        print(f"[{self.component}] → [{target}]: {message.get('type', 'message')}")
    
    @abstractmethod
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming requests from other agents or the system.
        
        Must be implemented by each specialized agent.
        
        Args:
            request: Request payload
            
        Returns:
            Response payload
        """
        pass


class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass


class ToolPermissionError(AgentError):
    """Raised when agent tries to use unauthorized tool."""
    pass


class CommunicationError(AgentError):
    """Raised when agent communication fails."""
    pass