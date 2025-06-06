#!/usr/bin/env python3
"""Test RAG agent response times under different conditions."""

import sys
sys.path.insert(0, '.')

import time
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker
from agent.communication.monitor import get_message_monitor
from agent.specialists.rag_agent import RAGSpecialist
from agent.orchestrator.orchestrating_manager import OrchestratingManager

def test_rag_response_times():
    """Test RAG response times in different scenarios."""
    print("Testing RAG agent response times...")
    
    # Initialize monitor
    monitor = get_message_monitor()
    monitor.enable_console_output = False  # Reduce noise
    
    # Initialize broker
    broker = MessageBroker()
    
    # Test 1: Single RAG agent
    print("\n1. Testing single RAG agent response time...")
    rag = RAGSpecialist(model="gemini-2.5-flash-preview-05-20")
    time.sleep(0.5)
    
    response_times = []
    for i in range(3):
        message = AgentMessage(
            sender="test",
            recipient="rag_specialist",
            message_type=MessageType.REQUEST,
            payload={
                "action": "hybrid_search",
                "query": f"test query {i}",
                "max_results": 5
            }
        )
        
        start = time.time()
        response = broker.send_request(message, timeout=30.0)
        elapsed = time.time() - start
        response_times.append(elapsed)
        
        status = "SUCCESS" if response else "TIMEOUT"
        print(f"   Request {i+1}: {elapsed:.2f}s - {status}")
    
    avg_time = sum(response_times) / len(response_times)
    print(f"   Average response time: {avg_time:.2f}s")
    
    # Test 2: With orchestrating manager
    print("\n2. Testing with Orchestrating Manager...")
    manager = OrchestratingManager(model="gemini-2.5-flash-preview-05-20")
    manager.register_agent("rag_specialist")
    time.sleep(0.5)
    
    # Test search through manager
    start = time.time()
    result = manager._handle_search_codebase({
        "type": "search_codebase",
        "description": "understanding the codebase architecture"
    })
    elapsed = time.time() - start
    
    print(f"   Manager search completed in {elapsed:.2f}s")
    if result:
        lines = result.split('\n')
        print(f"   Found {len(lines)} lines in response")
    
    # Test 3: Check timeout behavior
    print("\n3. Testing timeout behavior...")
    
    # Create a message with very short timeout
    message = AgentMessage(
        sender="test",
        recipient="rag_specialist",
        message_type=MessageType.REQUEST,
        payload={
            "action": "hybrid_search",
            "query": "complex query requiring analysis",
            "max_results": 10
        }
    )
    
    start = time.time()
    response = broker.send_request(message, timeout=0.5)  # Very short timeout
    elapsed = time.time() - start
    
    if response:
        print(f"   Response received in {elapsed:.2f}s (unexpected!)")
    else:
        print(f"   Timeout as expected after {elapsed:.2f}s")
    
    # Final stats
    print("\n4. Final Statistics:")
    stats = broker.get_stats()
    print(f"   Total messages sent: {stats['messages_sent']}")
    print(f"   Total messages delivered: {stats['messages_delivered']}")
    print(f"   Total messages failed: {stats['messages_failed']}")
    print(f"   Total responses matched: {stats['responses_matched']}")
    
    # Check for any timeout messages
    failures = monitor.get_recent_failures()
    timeout_count = sum(1 for f in failures if f.get_status().value == "timeout")
    print(f"   Total timeouts: {timeout_count}")

if __name__ == "__main__":
    test_rag_response_times()