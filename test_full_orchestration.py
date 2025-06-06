#!/usr/bin/env python3
"""Test full orchestration with all agents."""

import sys
sys.path.insert(0, '.')

import time
import threading
from agent.communication.broker import MessageBroker
from agent.communication.monitor import get_message_monitor
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.executor_pool import ExecutorPool
from agent.orchestrator.orchestrating_manager import OrchestratingManager

def test_full_orchestration():
    """Test full orchestration with all agents."""
    print("Testing full orchestration...")
    
    # Initialize monitor
    monitor = get_message_monitor()
    monitor.enable_console_output = True
    
    # Initialize broker
    broker = MessageBroker()
    
    # Initialize all agents
    print("\n1. Initializing all agents...")
    
    # Create specialists first
    planner = PlannerAgent(model="gemini-2.5-flash-preview-05-20")
    print("✓ Planner created")
    
    rag = RAGSpecialist(model="gemini-2.5-flash-preview-05-20")
    print("✓ RAG Specialist created")
    
    executor = ExecutorPool(model="gemini-2.5-flash-preview-05-20")
    print("✓ Executor Pool created")
    
    # Create manager
    manager = OrchestratingManager(model="gemini-2.5-flash-preview-05-20")
    print("✓ Manager created")
    
    # Register agents
    manager.register_agent("planner")
    manager.register_agent("rag_specialist")
    manager.register_agent("executor")
    
    # Wait for all registrations
    time.sleep(1.0)
    
    # Check registered handlers
    print("\n2. Checking broker registrations...")
    stats = broker.get_stats()
    print(f"Registered agents: {stats['registered_agents']}")
    
    # Test project creation which involves all agents
    print("\n3. Testing project creation flow...")
    
    query = "Create a simple Python calculator"
    print(f"Query: {query}")
    
    # Run in a thread with timeout monitoring
    result = [None]
    error = [None]
    
    def run_manager():
        try:
            result[0] = manager.chat(query)
        except Exception as e:
            error[0] = e
            import traceback
            traceback.print_exc()
    
    thread = threading.Thread(target=run_manager)
    start = time.time()
    thread.start()
    
    # Monitor progress
    timeout = 60  # 60 second timeout
    check_interval = 5
    elapsed = 0
    
    while thread.is_alive() and elapsed < timeout:
        time.sleep(check_interval)
        elapsed = time.time() - start
        print(f"  ... still running ({elapsed:.1f}s)")
        
        # Check broker stats
        stats = broker.get_stats()
        print(f"      Messages: sent={stats['messages_sent']}, delivered={stats['messages_delivered']}, failed={stats['messages_failed']}")
    
    # Final wait
    thread.join(timeout=1)
    
    total_time = time.time() - start
    
    if thread.is_alive():
        print(f"\n❌ Manager call timed out after {total_time:.2f}s")
    else:
        print(f"\n✅ Manager call completed in {total_time:.2f}s")
        if error[0]:
            print(f"Error: {error[0]}")
        elif result[0]:
            print(f"Result: {result[0]}")
    
    # Final stats
    print("\n4. Final Broker Stats:")
    stats = broker.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Monitor summary
    print("\n5. Monitor Summary:")
    monitor.print_summary()
    
    # Recent failures
    failures = monitor.get_recent_failures()
    if failures:
        print("\nRecent failure details:")
        for trace in failures[:3]:
            print(f"\nMessage {trace.message_id[:8]}... ({trace.sender} -> {trace.recipient}):")
            for event in trace.events:
                print(f"  [{event.timestamp.strftime('%H:%M:%S.%f')[:-3]}] {event.status.value}: {event.details}")
                if event.error:
                    print(f"    Error: {event.error}")

if __name__ == "__main__":
    test_full_orchestration()