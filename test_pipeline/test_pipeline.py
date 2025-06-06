#!/usr/bin/env python3
"""
Test the full multi-agent pipeline with real prompts.

This script:
1. Creates the multi-agent system
2. Sends prompts to the Manager
3. Monitors the execution flow
4. Reports any breaks in the pipeline
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Change to the parent directory so .cokeydex.yml is found
os.chdir(Path(__file__).parent.parent)

from agent.factory import AgentFactory
from agent.communication.protocol import AgentMessage, MessageType


class PipelineTester:
    """Test the complete pipeline from prompt to execution."""
    
    def __init__(self):
        self.factory = AgentFactory()
        self.system = None
        self.manager = None
        self.test_results = []
        
    def setup_system(self):
        """Initialize the multi-agent system."""
        print("🚀 Setting up multi-agent system...")
        self.system = self.factory.create_complete_system()
        
        if self.system["status"] != "success":
            raise RuntimeError(f"Failed to create system: {self.system}")
            
        self.manager = self.system["manager"]
        print("✅ System ready\n")
        
    def test_simple_calculator(self):
        """Test creating a simple calculator project."""
        print("\n" + "="*60)
        print("TEST 1: Simple Calculator Project")
        print("="*60)
        
        prompt = "I need a simple Python calculator that can add, subtract, multiply, and divide two numbers. It should have a clean CLI interface."
        
        print(f"📝 Sending prompt to Manager: {prompt[:50]}...")
        
        try:
            # Send prompt to manager
            response = self.manager.chat(prompt)
            print(f"\n🤖 Manager response: {response}")
            
            # Check if Manager understands the request
            if "Enhanced Manager received" in response:
                print("✅ Manager received the request")
                
                # Now we need to trigger the actual planning
                # In a real implementation, the Manager would delegate automatically
                # For now, let's manually trigger the delegation
                
                # Create a planning request
                plan_message = AgentMessage(
                    sender="manager",
                    recipient="planner",
                    message_type=MessageType.REQUEST,
                    payload={
                        "action": "create_plan",
                        "objective": prompt
                    }
                )
                
                # Get the planner and send request
                planner = self.system["planner"]
                plan_response = planner.handle_request(plan_message)
                
                print(f"\n📋 Planner response: {plan_response}")
                
                if plan_response["status"] == "success":
                    print("✅ Plan created successfully")
                    
                    # Now trigger execution
                    # In real implementation, Manager would coordinate this
                    executor = self.system["executor_pool"]
                    
                    exec_message = AgentMessage(
                        sender="manager",
                        recipient="executor",
                        message_type=MessageType.REQUEST,
                        payload={
                            "action": "execute_task",
                            "task_id": "T-001",
                            "task_description": "Create calculator.py with basic operations"
                        }
                    )
                    
                    exec_response = executor.handle_request(exec_message)
                    print(f"\n⚙️ Executor response: {exec_response}")
                    
                    if exec_response["status"] == "success":
                        print("✅ Task executed successfully")
                        self.test_results.append(("Simple Calculator", "PASSED"))
                    else:
                        print("❌ Task execution failed")
                        self.test_results.append(("Simple Calculator", "FAILED"))
                else:
                    print("❌ Planning failed")
                    self.test_results.append(("Simple Calculator", "FAILED"))
            else:
                print("❌ Manager did not understand the request")
                self.test_results.append(("Simple Calculator", "FAILED"))
                
        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append(("Simple Calculator", f"ERROR: {e}"))
    
    def test_manager_tools(self):
        """Test Manager using its tools directly."""
        print("\n" + "="*60)
        print("TEST 2: Manager Tool Usage")
        print("="*60)
        
        try:
            # Test if Manager can use create_project tool
            print("📝 Testing Manager's create_project tool...")
            
            result = self.manager.execute_tool("create_project", {
                "project_name": "test_calculator",
                "project_type": "python",
                "project_path": "./test_pipeline/test_project"
            })
            
            print(f"\n🔧 Tool result: {result}")
            
            if result.get("exit_code") == 0:
                print("✅ Manager can execute tools")
                self.test_results.append(("Manager Tools", "PASSED"))
            else:
                print(f"❌ Tool execution failed: {result.get('stderr', 'Unknown error')}")
                self.test_results.append(("Manager Tools", "FAILED"))
                
        except Exception as e:
            print(f"❌ Tool test error: {e}")
            self.test_results.append(("Manager Tools", f"ERROR: {e}"))
    
    def test_agent_communication(self):
        """Test inter-agent communication flow."""
        print("\n" + "="*60)
        print("TEST 3: Inter-Agent Communication")
        print("="*60)
        
        try:
            # Test Manager -> RAG communication
            print("📝 Testing Manager -> RAG communication...")
            
            rag = self.system["rag_specialist"]
            
            # Manager asks RAG for context
            search_message = AgentMessage(
                sender="manager",
                recipient="rag_specialist",
                message_type=MessageType.REQUEST,
                payload={
                    "action": "hybrid_search",
                    "query": "calculator implementation python",
                    "max_results": 3
                }
            )
            
            response = rag.handle_request(search_message)
            print(f"\n🔍 RAG response: {response}")
            
            if response["status"] == "success":
                print("✅ Inter-agent communication working")
                self.test_results.append(("Agent Communication", "PASSED"))
            else:
                print("❌ Communication failed")
                self.test_results.append(("Agent Communication", "FAILED"))
                
        except Exception as e:
            print(f"❌ Communication test error: {e}")
            self.test_results.append(("Agent Communication", f"ERROR: {e}"))
    
    def run_all_tests(self):
        """Run all pipeline tests."""
        print("\n" + "="*60)
        print("COKEYDEX PIPELINE INTEGRATION TEST")
        print("="*60)
        
        # Setup system
        self.setup_system()
        
        # Run tests
        tests = [
            self.test_manager_tools,
            self.test_agent_communication,
            self.test_simple_calculator
        ]
        
        for test_func in tests:
            try:
                test_func()
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"\n❌ Test crashed: {e}")
                import traceback
                traceback.print_exc()
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, status in self.test_results if status == "PASSED")
        total = len(self.test_results)
        
        for test_name, status in self.test_results:
            icon = "✅" if status == "PASSED" else "❌"
            print(f"{icon} {test_name}: {status}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        self.factory.shutdown_system()


def main():
    """Run the pipeline test."""
    tester = PipelineTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()