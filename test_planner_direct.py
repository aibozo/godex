#!/usr/bin/env python3
"""Test planner directly."""

import sys
sys.path.insert(0, '.')

from agent.specialists.planner_agent import PlannerAgent
from agent.communication.protocol import AgentMessage, MessageType

def test_planner_directly():
    """Test planner without broker."""
    print("=== Testing Planner Directly ===\n")
    
    # Create planner
    planner = PlannerAgent()
    
    # Create a test message
    message = AgentMessage(
        sender="test",
        recipient="planner",
        message_type=MessageType.REQUEST,
        payload={
            "action": "create_plan",
            "objective": "Create a simple hello world program"
        }
    )
    
    print("Calling planner handler directly...")
    try:
        result = planner.handle_request(message)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_planner_directly()