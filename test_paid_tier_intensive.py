#!/usr/bin/env python3
"""Test paid tier with multiple rapid requests."""

import sys
sys.path.insert(0, '.')

from agent.orchestrator.orchestrating_manager import OrchestratingManager
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.executor_pool import ExecutorPool
from agent.communication.broker import MessageBroker
import time

def test_intensive_requests():
    """Test with multiple requests that would exceed free tier limits."""
    print("=== Testing Paid Tier with Intensive Requests ===\n")
    
    # Create agents
    print("Creating agents...")
    planner = PlannerAgent()
    rag = RAGSpecialist()
    executor = ExecutorPool()
    manager = OrchestratingManager()
    print("✓ All agents created\n")
    
    # Test queries that would exceed free tier (10 requests/minute)
    queries = [
        "Create a web scraping tool",
        "Build a REST API server", 
        "Implement a database ORM",
        "Create a machine learning pipeline",
        "Build a real-time chat application",
        "Implement a file encryption tool",
        "Create a task scheduler",
        "Build a data visualization dashboard",
        "Implement a caching system",
        "Create a testing framework",
        "Build a logging system",
        "Implement a configuration manager"
    ]
    
    print(f"Sending {len(queries)} requests rapidly (would exceed free tier limit of 10/minute)...\n")
    
    success_count = 0
    error_count = 0
    free_tier_errors = 0
    
    for i, query in enumerate(queries):
        print(f"\n[Request {i+1}/{len(queries)}] {query}")
        try:
            start = time.time()
            result = manager.chat(query)
            elapsed = time.time() - start
            
            if "error" in result.lower() or "failed" in result.lower():
                error_count += 1
                print(f"❌ Error in response (took {elapsed:.2f}s)")
            else:
                success_count += 1
                print(f"✅ Success (took {elapsed:.2f}s)")
                
        except Exception as e:
            error_count += 1
            error_str = str(e)
            if "free_tier" in error_str.lower() or "quota" in error_str.lower():
                free_tier_errors += 1
                print(f"❌ FREE TIER ERROR: {error_str[:100]}...")
            else:
                print(f"❌ Error: {error_str[:100]}...")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"SUMMARY:")
    print(f"  Total requests: {len(queries)}")
    print(f"  Successful: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"  Free tier errors: {free_tier_errors}")
    
    if free_tier_errors > 0:
        print(f"\n⚠️  DETECTED {free_tier_errors} FREE TIER ERRORS!")
        print("This suggests the API key is still on free tier.")
    else:
        print(f"\n✅ NO FREE TIER ERRORS!")
        print("This confirms we're using the PAID API successfully.")
    
    # Check broker stats
    broker = MessageBroker()
    stats = broker.get_stats()
    print(f"\nBroker Stats:")
    print(f"  Messages sent: {stats['messages_sent']}")
    print(f"  Messages delivered: {stats['messages_delivered']}")

if __name__ == "__main__":
    test_intensive_requests()