"""
Inter-agent communication system for Cokeydx.

Provides message protocols and routing for agent-to-agent communication.
"""

from .protocol import AgentMessage, MessageType
from .broker import MessageBroker

__all__ = ["AgentMessage", "MessageType", "MessageBroker"]