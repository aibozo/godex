#!/usr/bin/env python3
"""Test LLM Orchestrator with message_rag tool."""

import sys
sys.path.insert(0, '.')

from agent.orchestrator.llm_orchestrator import LLMOrchestratingManager
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.executor_pool import ExecutorPool
from agent.communication.broker import MessageBroker

def test_llm_orchestrator():
    """Test LLM orchestrator calling message_rag."""
    print("=== Testing LLM Orchestrator with message_rag ===\n")
    
    # Create agents
    print("Creating agents...")
    planner = PlannerAgent(model="gemini-2.5-flash-preview-05-20")
    print("✓ Planner created")
    
    rag = RAGSpecialist(model="gemini-2.5-flash-preview-05-20")
    print("✓ RAG Specialist created")
    
    executor = ExecutorPool(model="gemini-2.5-flash-preview-05-20")
    print("✓ Executor Pool created")
    
    # Create LLM orchestrating manager with Claude for testing (supports tool calling)
    manager = LLMOrchestratingManager(model="claude-sonnet-4-20250514")
    print("✓ LLM Orchestrating Manager created\n")
    
    # Register agents with manager
    manager.register_agent("planner")
    manager.register_agent("rag_specialist")
    manager.register_agent("executor")
    
    # Check broker stats
    broker = MessageBroker()
    stats = broker.get_stats()
    print(f"Initial Broker Stats:")
    print(f"  Registered agents: {stats['registered_agents']}\n")
    
    # Test a query that should trigger RAG search
    query = "Search the codebase for calculator implementations"
    print(f"Query: {query}\n")
    
    try:
        result = manager.chat(query)
        print(f"\nManager Response:\n{result}\n")
        
        # Check final broker stats
        final_stats = broker.get_stats()
        print(f"Final Broker Stats:")
        print(f"  Messages sent: {final_stats['messages_sent']}")
        print(f"  Messages delivered: {final_stats['messages_delivered']}")
        print(f"  Messages failed: {final_stats['messages_failed']}")
        print(f"  Registered agents: {final_stats['registered_agents']}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_orchestrator()