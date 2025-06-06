#!/usr/bin/env python3
"""Test the fixed message broker."""

import sys
sys.path.insert(0, '.')

from agent.orchestrator.orchestrating_manager import OrchestratingManager
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.executor_pool import ExecutorPool
from agent.communication.broker import MessageBroker

def test_broker_communication():
    """Test that agents can communicate through the broker."""
    print("=== Testing Message Broker Fix ===\n")
    
    # Create agents manually to use OrchestratingManager
    print("Creating agents...")
    
    # Create specialists first so they register with broker
    # Use Gemini 2.5 Flash for cost-effective testing
    planner = PlannerAgent(model="gemini-2.5-flash-preview-05-20")
    print("✓ Planner created (Gemini 2.5 Flash)")
    
    rag = RAGSpecialist(model="gemini-2.5-flash-preview-05-20")
    print("✓ RAG Specialist created (Gemini 2.5 Flash)")
    
    executor = ExecutorPool(model="gemini-2.5-flash-preview-05-20")
    print("✓ Executor Pool created (Gemini 2.5 Flash)")
    
    # Create orchestrating manager
    manager = OrchestratingManager()
    print("✓ Orchestrating Manager created\n")
    
    # Test simple query
    query = "Create a simple Python calculator"
    print(f"Query: {query}\n")
    
    try:
        result = manager.chat(query)
        print(f"\nResult: {result}\n")
        
        # Check broker stats
        broker = MessageBroker()
        stats = broker.get_stats()
        print(f"Broker Stats:")
        print(f"  Messages sent: {stats['messages_sent']}")
        print(f"  Messages delivered: {stats['messages_delivered']}")
        print(f"  Messages failed: {stats['messages_failed']}")
        print(f"  Responses matched: {stats['responses_matched']}")
        print(f"  Registered agents: {stats['registered_agents']}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_broker_communication()