"""
Message protocol definitions for inter-agent communication.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
import datetime


class MessageType(Enum):
    """Types of messages that can be sent between agents."""
    REQUEST = "request"           # Request for action/information
    RESPONSE = "response"         # Response to a request
    NOTIFICATION = "notification" # One-way notification
    STATUS_UPDATE = "status"      # Status/progress update
    ERROR = "error"              # Error notification
    BROADCAST = "broadcast"       # Message to all agents


class AgentMessage(BaseModel):
    """
    Standard message format for inter-agent communication.
    """
    
    # Message identification
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = Field(default=None)  # For request/response pairs
    
    # Routing information
    sender: str = Field(..., description="Sending agent component name")
    recipient: str = Field(..., description="Target agent component name")
    
    # Message content
    message_type: MessageType = Field(..., description="Type of message")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message content")
    
    # Metadata
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    priority: int = Field(default=1, description="Message priority (1=high, 5=low)")
    ttl_seconds: Optional[int] = Field(default=300, description="Time to live in seconds")
    
    # Response handling
    requires_response: bool = Field(default=False, description="Whether sender expects a response")
    response_timeout: Optional[int] = Field(default=30, description="Response timeout in seconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sender": "manager",
                "recipient": "planner", 
                "message_type": "request",
                "payload": {
                    "action": "create_plan",
                    "objective": "Add user authentication",
                    "context_hints": ["auth.py", "models.py"]
                },
                "requires_response": True,
                "response_timeout": 60
            }
        }
    }

    def create_response(self, payload: Dict[str, Any], message_type: MessageType = MessageType.RESPONSE) -> "AgentMessage":
        """
        Create a response message to this message.
        
        Args:
            payload: Response payload
            message_type: Type of response message
            
        Returns:
            New AgentMessage as response
        """
        return AgentMessage(
            correlation_id=self.message_id,
            sender=self.recipient,  # Swap sender/recipient
            recipient=self.sender,
            message_type=message_type,
            payload=payload,
            requires_response=False  # Responses don't need responses
        )
    
    def is_expired(self) -> bool:
        """Check if message has exceeded its TTL."""
        if self.ttl_seconds is None:
            return False
        
        age = (datetime.datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl_seconds