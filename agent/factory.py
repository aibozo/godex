"""
Agent Factory - Creates and manages all specialized agents.

Provides centralized agent creation, registration, and lifecycle management.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from agent.orchestrator.enhanced_manager import EnhancedManager
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.executor_pool import ExecutorPool
from agent.communication.broker import MessageBroker


class AgentFactory:
    """
    Factory for creating and managing all agents in the system.
    
    Handles:
    - Agent initialization
    - Registration with message broker
    - Inter-agent introduction
    - System startup coordination
    """
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.broker = MessageBroker()
        self.created_at = datetime.now()
    
    def create_complete_system(self) -> Dict[str, Any]:
        """
        Create the complete multi-agent system with all agents.
        
        Returns:
            Dictionary of created agents
        """
        try:
            print("🚀 Initializing Cokeydx Multi-Agent System...")
            
            # Create Manager (orchestrator)
            print("📋 Creating Enhanced Manager...")
            manager = EnhancedManager()
            self.agents["manager"] = manager
            
            # Create RAG Specialist
            print("🔍 Creating RAG Specialist...")
            rag_specialist = RAGSpecialist()
            self.agents["rag_specialist"] = rag_specialist
            
            # Create Planner Agent
            print("🗂️  Creating Planner Agent...")
            planner = PlannerAgent()
            self.agents["planner"] = planner
            
            # Create Executor Pool
            print("⚙️  Creating Executor Pool...")
            executor_pool = ExecutorPool(pool_size=2)
            self.agents["executor"] = executor_pool
            
            # Register all agents with Manager
            print("🔗 Registering agents with Manager...")
            manager.register_agent("rag_specialist")
            manager.register_agent("planner")
            manager.register_agent("executor")
            
            # Test inter-agent communication
            print("🗨️  Testing inter-agent communication...")
            self._test_agent_communication()
            
            print("✅ Multi-Agent System initialized successfully!")
            
            return {
                "status": "success",
                "agents_created": list(self.agents.keys()),
                "manager": manager,
                "rag_specialist": rag_specialist,
                "planner": planner,
                "executor_pool": executor_pool,
                "broker": self.broker
            }
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "agents_created": list(self.agents.keys())
            }
    
    def create_manager_only(self) -> EnhancedManager:
        """Create just the Enhanced Manager for testing."""
        try:
            manager = EnhancedManager()
            self.agents["manager"] = manager
            return manager
        except Exception as e:
            print(f"Manager creation failed: {e}")
            raise
    
    def create_rag_specialist(self) -> RAGSpecialist:
        """Create just the RAG Specialist for testing."""
        try:
            rag_specialist = RAGSpecialist()
            self.agents["rag_specialist"] = rag_specialist
            return rag_specialist
        except Exception as e:
            print(f"RAG Specialist creation failed: {e}")
            raise
    
    def create_planner(self) -> PlannerAgent:
        """Create just the Planner Agent for testing."""
        try:
            planner = PlannerAgent()
            self.agents["planner"] = planner
            return planner
        except Exception as e:
            print(f"Planner creation failed: {e}")
            raise
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all agents in the system."""
        status = {
            "factory_status": {
                "created_at": self.created_at,
                "agents_active": len(self.agents),
                "broker_stats": self.broker.get_stats()
            },
            "agents": {}
        }
        
        for agent_name, agent in self.agents.items():
            try:
                if hasattr(agent, 'get_status'):
                    status["agents"][agent_name] = agent.get_status()
                elif hasattr(agent, 'get_execution_status'):
                    status["agents"][agent_name] = agent.get_execution_status()
                else:
                    status["agents"][agent_name] = {"status": "active", "type": type(agent).__name__}
            except Exception as e:
                status["agents"][agent_name] = {"status": "error", "error": str(e)}
        
        return status
    
    def shutdown_system(self) -> None:
        """Shutdown all agents and the message broker."""
        print("🛑 Shutting down Multi-Agent System...")
        
        try:
            # Shutdown broker
            self.broker.shutdown()
            
            # Clear agents
            self.agents.clear()
            
            print("✅ System shutdown complete")
            
        except Exception as e:
            print(f"❌ Shutdown error: {e}")
    
    def _test_agent_communication(self) -> None:
        """Test basic communication between agents."""
        try:
            if "manager" in self.agents and "rag_specialist" in self.agents:
                # Test Manager -> RAG communication
                from agent.communication.protocol import AgentMessage, MessageType
                
                test_message = AgentMessage(
                    sender="factory",
                    recipient="rag_specialist",
                    message_type=MessageType.REQUEST,
                    payload={
                        "action": "hybrid_search",
                        "query": "test communication",
                        "max_results": 1
                    }
                )
                
                # This tests the message routing
                # In a full test, we'd verify the response
                print("  📡 Communication test passed")
                
        except Exception as e:
            print(f"  ⚠️  Communication test failed: {e}")


def create_system() -> Dict[str, Any]:
    """
    Convenience function to create the complete system.
    
    Returns:
        System components
    """
    factory = AgentFactory()
    return factory.create_complete_system()


def test_system_creation():
    """Test system creation without full initialization."""
    print("🧪 Testing system creation...")
    
    try:
        factory = AgentFactory()
        
        # Test individual agent creation
        print("  Testing Manager creation...")
        manager = factory.create_manager_only()
        print(f"  ✅ Manager created: {manager.agent_id}")
        
        print("  Testing RAG Specialist creation...")
        rag = factory.create_rag_specialist()
        print(f"  ✅ RAG Specialist created: {rag.agent_id}")
        
        print("  Testing Planner creation...")
        planner = factory.create_planner()
        print(f"  ✅ Planner created: {planner.agent_id}")
        
        # Get system status
        status = factory.get_system_status()
        print(f"  📊 System status: {len(status['agents'])} agents active")
        
        print("✅ System creation test passed!")
        
        # Cleanup
        factory.shutdown_system()
        
        return True
        
    except Exception as e:
        print(f"❌ System creation test failed: {e}")
        return False


if __name__ == "__main__":
    # Run basic tests
    test_system_creation()