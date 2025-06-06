#!/usr/bin/env python3
"""Test broker message delivery without LLM calls."""

import sys
sys.path.insert(0, '.')

from agent.communication.broker import MessageBroker
from agent.communication.protocol import AgentMessage, MessageType
import time
import threading

def simple_handler(message: AgentMessage):
    """Simple handler that responds immediately."""
    print(f"[Handler] Received message: {message.payload}")
    return {
        "status": "success",
        "echo": message.payload.get("test", "no test data")
    }

def test_simple_broker():
    """Test basic broker functionality."""
    print("=== Testing Simple Broker ===\n")
    
    # Create broker
    broker = MessageBroker()
    
    # Register a simple handler
    broker.register_agent("test_agent", simple_handler)
    
    # Send a request
    message = AgentMessage(
        sender="test",
        recipient="test_agent",
        message_type=MessageType.REQUEST,
        payload={"test": "hello broker"}
    )
    
    print("Sending message...")
    start = time.time()
    response = broker.send_request(message, timeout=5.0)
    elapsed = time.time() - start
    
    if response:
        print(f"Response received in {elapsed:.2f}s: {response.payload}")
    else:
        print(f"No response after {elapsed:.2f}s")
    
    # Check stats
    stats = broker.get_stats()
    print(f"\nBroker Stats: {stats}")

if __name__ == "__main__":
    test_simple_broker()