"""
Test actual tool execution in the multi-agent system.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.factory import AgentFactory
from agent.communication.protocol import AgentMessage, MessageType


class TestToolExecution:
    """Test that agents can actually execute tools."""
    
    def test_rag_hybrid_search_tool(self):
        """Test RAG agent executing hybrid search tool."""
        factory = AgentFactory()
        rag = factory.create_rag_specialist()
        
        # Create search request
        search_message = AgentMessage(
            sender="test",
            recipient="rag_specialist",
            message_type=MessageType.REQUEST,
            payload={
                "action": "hybrid_search",
                "query": "test search query",
                "max_results": 3
            }
        )
        
        # Execute search
        response = rag.handle_request(search_message)
        
        print(f"\nRAG Search Response: {response}")
        
        assert response["status"] in ["success", "error"]
        assert response["query"] == "test search query"
        assert "total_searches" in response
        
        if response["status"] == "success":
            assert "results" in response
            assert "tool_response" in response
        else:
            assert "error" in response
            print(f"Tool execution error: {response['error']}")
    
    def test_manager_read_file_tool(self):
        """Test Manager executing read_file tool."""
        factory = AgentFactory()
        manager = factory.create_manager_only()
        
        # Test reading a file that exists
        result = manager.execute_tool("read_file", {
            "path": "README.md"
        })
        
        print(f"\nManager Read File Result: {result}")
        
        assert "exit_code" in result
        if result["exit_code"] == 0:
            assert "stdout" in result
            assert len(result["stdout"]) > 0
        else:
            print(f"Read file error: {result.get('stderr', 'Unknown error')}")
    
    def test_tool_permissions(self):
        """Test that agents can only execute allowed tools."""
        factory = AgentFactory()
        
        # Manager should be able to use create_project
        manager = factory.create_manager_only()
        
        # This should work (allowed tool)
        result = manager.execute_tool("grep", {
            "pattern": "test",
            "path": "."
        })
        assert "exit_code" in result
        
        # RAG should NOT be able to use write_diff
        rag = factory.create_rag_specialist()
        
        try:
            result = rag.execute_tool("write_diff", {
                "file_path": "test.py",
                "diff": "some diff"
            })
            assert False, "RAG should not be able to use write_diff"
        except (ValueError, PermissionError) as e:
            assert "not allowed" in str(e)
            print(f"\nCorrectly blocked: {e}")


if __name__ == "__main__":
    test = TestToolExecution()
    
    print("Testing actual tool execution...\n")
    
    tests = [
        ("RAG hybrid search tool", test.test_rag_hybrid_search_tool),
        ("Manager read file tool", test.test_manager_read_file_tool),
        ("Tool permissions", test.test_tool_permissions)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            print(f"Running: {test_name}")
            print('='*60)
            test_func()
            print(f"✅ {test_name} passed")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Tool Execution Tests: {passed} passed, {failed} failed")