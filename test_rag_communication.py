#!/usr/bin/env python3
"""Test RAG agent communication specifically."""

import sys
sys.path.insert(0, '.')

from agent.communication.broker import MessageBroker
from agent.communication.protocol import AgentMessage, MessageType
from agent.specialists.rag_agent import RAGSpecialist
import time

def test_rag_direct():
    """Test direct message to RAG agent."""
    print("=== Testing RAG Communication ===\n")
    
    # Create RAG agent (it will register itself)
    rag = RAGSpecialist(model="gemini-2.5-flash-preview-05-20")
    print("✓ RAG Specialist created\n")
    
    # Get broker and check registration
    broker = MessageBroker()
    stats = broker.get_stats()
    print(f"Registered agents: {stats['registered_agents']}\n")
    
    # Send a test message
    message = AgentMessage(
        sender="test",
        recipient="rag_specialist",
        message_type=MessageType.REQUEST,
        payload={
            "action": "hybrid_search",
            "query": "calculator functions",
            "max_results": 3
        }
    )
    
    print(f"Sending message to RAG...")
    print(f"  Message ID: {message.message_id}")
    print(f"  Recipient: {message.recipient}")
    print(f"  Action: {message.payload['action']}")
    
    start = time.time()
    response = broker.send_request(message, timeout=10.0)
    elapsed = time.time() - start
    
    if response:
        print(f"\nResponse received in {elapsed:.2f}s:")
        print(f"  Type: {type(response)}")
        print(f"  Status: {response.payload.get('status')}")
        print(f"  Results count: {len(response.payload.get('results', []))}")
        print(f"  Total searches: {response.payload.get('total_searches', 0)}")
    else:
        print(f"\n❌ No response after {elapsed:.2f}s")
    
    # Final broker stats
    final_stats = broker.get_stats()
    print(f"\nFinal Broker Stats:")
    print(f"  Messages sent: {final_stats['messages_sent']}")
    print(f"  Messages delivered: {final_stats['messages_delivered']}")
    print(f"  Messages failed: {final_stats['messages_failed']}")

if __name__ == "__main__":
    test_rag_direct()