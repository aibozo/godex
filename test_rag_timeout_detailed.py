#!/usr/bin/env python3
"""Test RAG agent timeout issue with detailed logging."""

import sys
sys.path.insert(0, '.')

import time
import threading
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker
from agent.communication.monitor import get_message_monitor
from agent.specialists.rag_agent import RAGSpecialist
from agent.orchestrator.orchestrating_manager import OrchestratingManager

def test_orchestration_timeout():
    """Test the orchestration scenario that times out."""
    print("Testing orchestration timeout scenario...")
    
    # Initialize monitor
    monitor = get_message_monitor()
    monitor.enable_console_output = True
    
    # Initialize broker
    broker = MessageBroker()
    
    # Initialize agents
    print("\n1. Initializing agents...")
    rag = RAGSpecialist(model="gemini-2.5-flash-preview-05-20")
    print("RAG initialized")
    
    manager = OrchestratingManager(model="gemini-2.5-flash-preview-05-20")
    print("Manager initialized")
    
    # Register RAG with manager
    manager.register_agent("rag_specialist")
    
    # Wait a bit for registration
    time.sleep(0.5)
    
    # Test the search functionality directly first
    print("\n2. Testing direct RAG search...")
    test_message = AgentMessage(
        sender="test",
        recipient="rag_specialist",
        message_type=MessageType.REQUEST,
        payload={
            "action": "hybrid_search",
            "query": "understanding the codebase",
            "max_results": 5
        }
    )
    
    start = time.time()
    response = broker.send_request(test_message, timeout=10.0)
    elapsed = time.time() - start
    
    print(f"Direct RAG test completed in {elapsed:.2f}s")
    if response:
        print(f"Response status: {response.payload.get('status')}")
    else:
        print("No response received")
    
    # Now test through manager
    print("\n3. Testing through manager...")
    start = time.time()
    
    # Create a thread to call manager.chat
    result = [None]
    error = [None]
    
    def manager_chat():
        try:
            result[0] = manager._handle_search_codebase({
                "type": "search_codebase",
                "description": "understanding the codebase architecture"
            })
        except Exception as e:
            error[0] = e
            import traceback
            traceback.print_exc()
    
    thread = threading.Thread(target=manager_chat)
    thread.start()
    
    # Monitor the thread
    timeout = 15
    thread.join(timeout)
    
    elapsed = time.time() - start
    
    if thread.is_alive():
        print(f"Manager call timed out after {elapsed:.2f}s")
        print("Thread is still running...")
    else:
        print(f"Manager call completed in {elapsed:.2f}s")
        if error[0]:
            print(f"Error: {error[0]}")
        elif result[0]:
            print(f"Result: {result[0][:200]}...")
        else:
            print("No result")
    
    # Print broker stats
    print("\n4. Broker Stats:")
    stats = broker.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Print monitor summary
    print("\n5. Monitor Summary:")
    monitor.print_summary()

if __name__ == "__main__":
    test_orchestration_timeout()