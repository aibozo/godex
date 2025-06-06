#!/usr/bin/env python3
"""
Test the orchestrating manager with real workflows.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from agent.factory import AgentFactory
from agent.orchestrator.orchestrating_manager import OrchestratingManager
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.executor_pool import ExecutorPool


def test_orchestrating_manager():
    """Test the new orchestrating manager."""
    
    print("🚀 Testing Orchestrating Manager")
    print("="*60)
    
    # Create agents
    print("\n1. Creating agents...")
    manager = OrchestratingManager()
    rag = RAGSpecialist()
    planner = PlannerAgent()
    executor = ExecutorPool()
    
    # Register agents with manager
    manager.register_agent("rag_specialist")
    manager.register_agent("planner")
    manager.register_agent("executor")
    
    print("✅ Agents created and registered")
    
    # Test 1: Simple echo
    print("\n2. Testing basic chat...")
    response = manager.chat("Hello")
    print(f"   Response: {response}")
    
    # Test 2: Project creation
    print("\n3. Testing project creation...")
    response = manager.chat("Create a simple Python calculator that can add and subtract numbers")
    print(f"   Response:\n{response}")
    
    # Test 3: Status check
    print("\n4. Testing status check...")
    response = manager.chat("What's the current status?")
    print(f"   Response:\n{response}")
    
    # Check final state
    status = manager.get_system_status()
    print(f"\n5. Final system state:")
    print(f"   Total requests: {status['manager_status']['total_requests']}")
    print(f"   Conversation turns: {status['manager_status']['conversation_turns']}")
    print(f"   Active project: {status['manager_status']['active_project']}")
    
    print("\n✅ Test complete")


if __name__ == "__main__":
    test_orchestrating_manager()