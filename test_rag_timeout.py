#!/usr/bin/env python3
"""Test RAG agent timeout issue."""

import sys
sys.path.insert(0, '.')

import time
from agent.communication.protocol import AgentMessage, MessageType
from agent.communication.broker import MessageBroker
from agent.communication.monitor import get_message_monitor
from agent.specialists.rag_agent import RAGSpecialist

def test_rag_timeout():
    """Test the RAG agent timeout scenario."""
    print("Testing RAG agent timeout scenario...")
    
    # Initialize monitor
    monitor = get_message_monitor()
    monitor.enable_console_output = True
    
    # Initialize broker
    broker = MessageBroker()
    
    # Initialize RAG specialist
    print("\n1. Initializing RAG specialist...")
    rag = RAGSpecialist()
    
    # Wait a bit for registration
    time.sleep(0.5)
    
    # Create a test message
    print("\n2. Creating test message...")
    message = AgentMessage(
        sender="manager",
        recipient="rag_specialist",
        message_type=MessageType.REQUEST,
        payload={
            "action": "hybrid_search",
            "query": "test query",
            "max_results": 5
        }
    )
    
    print(f"\n3. Sending request (message_id: {message.message_id[:8]}...)...")
    start_time = time.time()
    
    # Send request with timeout
    response = broker.send_request(message, timeout=10.0)
    
    elapsed = time.time() - start_time
    print(f"\n4. Request completed in {elapsed:.2f}s")
    
    if response:
        print(f"Response received: {response}")
        if hasattr(response, 'payload'):
            print(f"Response payload: {response.payload}")
    else:
        print("Response: None (timeout)")
    
    # Print monitor summary
    print("\n5. Monitor Summary:")
    monitor.print_summary()
    
    # Get the trace for our message
    trace = monitor.get_trace(message.message_id)
    if trace:
        print(f"\nDetailed trace for message {message.message_id[:8]}...:")
        for event in trace.events:
            print(f"  [{event.timestamp.strftime('%H:%M:%S.%f')[:-3]}] {event.status.value}: {event.details}")
            if event.error:
                print(f"    Error: {event.error}")

if __name__ == "__main__":
    test_rag_timeout()