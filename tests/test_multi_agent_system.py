"""
Comprehensive tests for the multi-agent system.

Tests:
- Agent creation and initialization
- Inter-agent communication
- Summary reporting to Manager
- Tool permissions
- Model assignments
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.factory import AgentFactory
from agent.communication.protocol import AgentMessage, MessageType
from agent.tools.registries import get_agent_tools


class TestMultiAgentSystem:
    """Test the complete multi-agent system."""
    
    def test_individual_agent_creation(self):
        """Test creating each agent individually."""
        factory = AgentFactory()
        
        # Test Manager creation
        manager = factory.create_manager_only()
        assert manager is not None
        assert manager.model == "gemini-2.5-flash-preview-05-20"
        assert manager.component == "manager"
        assert "create_project" in manager.allowed_tools
        
        # Test RAG Specialist creation
        rag = factory.create_rag_specialist()
        assert rag is not None
        assert rag.model == "gemini-2.5-flash-preview-05-20"
        assert rag.component == "rag_specialist"
        assert "hybrid_search" in rag.allowed_tools
        
        # Test Planner creation
        planner = factory.create_planner()
        assert planner is not None
        assert planner.model == "gemini-2.5-flash-preview-05-20"
        assert planner.component == "planner"
        assert "analyze_codebase" in planner.allowed_tools
    
    def test_complete_system_creation(self):
        """Test creating the complete system."""
        factory = AgentFactory()
        result = factory.create_complete_system()
        
        assert result["status"] == "success"
        assert set(result["agents_created"]) == {"manager", "rag_specialist", "planner", "executor"}
        
        # Verify all agents exist
        assert result["manager"] is not None
        assert result["rag_specialist"] is not None
        assert result["planner"] is not None
        assert result["executor_pool"] is not None
    
    def test_agent_registration_with_manager(self):
        """Test that agents register with the manager."""
        factory = AgentFactory()
        result = factory.create_complete_system()
        
        manager = result["manager"]
        assert "rag_specialist" in manager.registered_agents
        assert "planner" in manager.registered_agents
        assert "executor" in manager.registered_agents
    
    def test_inter_agent_communication(self):
        """Test message passing between agents."""
        factory = AgentFactory()
        result = factory.create_complete_system()
        
        broker = result["broker"]
        rag = result["rag_specialist"]
        
        # Create a test message
        test_message = AgentMessage(
            sender="test",
            recipient="rag_specialist",
            message_type=MessageType.REQUEST,
            payload={
                "action": "hybrid_search",
                "query": "test query",
                "max_results": 3
            }
        )
        
        # Test that RAG can handle the message
        response = rag.handle_request(test_message)
        assert response["status"] == "success"
        assert response["query"] == "test query"
        assert "results" in response
    
    def test_summary_reporting_to_manager(self):
        """Test that agents can report summaries to the manager."""
        factory = AgentFactory()
        result = factory.create_complete_system()
        
        manager = result["manager"]
        
        # Create a summary submission
        summary_message = AgentMessage(
            sender="rag_specialist",
            recipient="manager",
            message_type=MessageType.NOTIFICATION,
            payload={
                "action": "submit_summary",
                "summary": {
                    "agent_id": "test-rag-123",
                    "agent_type": "rag_specialist",
                    "timestamp": datetime.now(),
                    "status": "active",
                    "current_tasks": ["search: test query"],
                    "key_findings": ["Found 5 relevant chunks"],
                    "resource_usage": {"searches_performed": 1}
                }
            }
        )
        
        # Test manager handles summary
        response = manager.handle_request(summary_message)
        assert response["status"] == "received"
        assert "test-rag-123" in manager.agent_summaries
    
    def test_tool_permissions(self):
        """Test that each agent has correct tool permissions."""
        # Manager tools
        manager_tools = get_agent_tools("manager")
        assert "create_project" in manager_tools
        assert "get_task_status" in manager_tools
        # Note: read_file is now available to all agents
        
        # RAG tools
        rag_tools = get_agent_tools("rag_specialist")
        assert "hybrid_search" in rag_tools
        assert "rank_chunks" in rag_tools
        assert "write_diff" not in rag_tools  # Executor tool
        
        # Planner tools
        planner_tools = get_agent_tools("planner")
        assert "analyze_codebase" in planner_tools
        assert "query_rag" in planner_tools
        assert "run_tests" not in planner_tools  # Executor tool
        
        # Executor tools
        executor_tools = get_agent_tools("executor")
        assert "read_file" in executor_tools
        assert "write_diff" in executor_tools
        assert "run_tests" in executor_tools
        assert "create_project" not in executor_tools  # Manager tool
    
    def test_system_status(self):
        """Test getting system status."""
        factory = AgentFactory()
        result = factory.create_complete_system()
        
        status = factory.get_system_status()
        assert "factory_status" in status
        assert "agents" in status
        assert len(status["agents"]) == 4
        
        # Check individual agent status
        for agent_name in ["manager", "rag_specialist", "planner"]:
            assert agent_name in status["agents"]
            agent_status = status["agents"][agent_name]
            # BaseAgent agents have these fields
            assert "agent_id" in agent_status
            assert "component" in agent_status
            assert "model" in agent_status
        
        # Executor pool has different structure
        assert "executor" in status["agents"]
        executor_status = status["agents"]["executor"]
        assert "pool_size" in executor_status
        assert "status" in executor_status
    
    def test_manager_conversation(self):
        """Test manager conversation handling."""
        factory = AgentFactory()
        result = factory.create_complete_system()
        
        manager = result["manager"]
        
        # Test chat function
        response = manager.chat("Hello, I need help with a coding task")
        assert "Enhanced Manager received" in response
        assert len(manager.conversation_history) == 2  # Human + manager response
    
    def test_planner_request_handling(self):
        """Test planner handling plan creation requests."""
        factory = AgentFactory()
        result = factory.create_complete_system()
        
        planner = result["planner"]
        
        # Create plan request
        plan_message = AgentMessage(
            sender="manager",
            recipient="planner",
            message_type=MessageType.REQUEST,
            payload={
                "action": "create_plan",
                "objective": "Implement user authentication"
            }
        )
        
        response = planner.handle_request(plan_message)
        assert response["status"] == "success"
        assert response["objective"] == "Implement user authentication"
        assert "plan" in response
        assert len(planner.planning_history) == 1
    
    def test_executor_pool_handling(self):
        """Test executor pool task handling."""
        factory = AgentFactory()
        result = factory.create_complete_system()
        
        executor = result["executor_pool"]
        
        # Create execution request
        exec_message = AgentMessage(
            sender="manager",
            recipient="executor",
            message_type=MessageType.REQUEST,
            payload={
                "action": "execute_task",
                "task_id": "T-001",
                "task_description": "Write unit tests"
            }
        )
        
        response = executor.handle_request(exec_message)
        assert response["status"] == "success"
        assert response["task_id"] == "T-001"
        assert len(executor.execution_history) == 1
    
    def test_system_shutdown(self):
        """Test system shutdown."""
        factory = AgentFactory()
        result = factory.create_complete_system()
        
        # Shutdown should not raise errors
        factory.shutdown_system()
        assert len(factory.agents) == 0


if __name__ == "__main__":
    # Run tests
    test = TestMultiAgentSystem()
    
    print("Running multi-agent system tests...\n")
    
    tests = [
        ("Individual agent creation", test.test_individual_agent_creation),
        ("Complete system creation", test.test_complete_system_creation),
        ("Agent registration", test.test_agent_registration_with_manager),
        ("Inter-agent communication", test.test_inter_agent_communication),
        ("Summary reporting", test.test_summary_reporting_to_manager),
        ("Tool permissions", test.test_tool_permissions),
        ("System status", test.test_system_status),
        ("Manager conversation", test.test_manager_conversation),
        ("Planner requests", test.test_planner_request_handling),
        ("Executor pool", test.test_executor_pool_handling),
        ("System shutdown", test.test_system_shutdown)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            failed += 1
    
    print(f"\nTests: {passed} passed, {failed} failed")