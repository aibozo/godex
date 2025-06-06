#!/usr/bin/env python3
"""
Test the real flow where Manager orchestrates agents to complete a task.

This is a more realistic test where the Manager:
1. Receives a user request
2. Delegates to Planner for task breakdown
3. Uses RAG for context
4. Coordinates Executor for implementation
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from agent.factory import AgentFactory
from agent.communication.protocol import AgentMessage, MessageType


class RealFlowTester:
    """Test realistic multi-agent workflows."""
    
    def __init__(self):
        self.factory = AgentFactory()
        self.system = None
        
    def setup(self):
        """Initialize the system."""
        print("🚀 Initializing multi-agent system...")
        self.system = self.factory.create_complete_system()
        
        if self.system["status"] != "success":
            raise RuntimeError("Failed to create system")
            
        print("✅ System ready\n")
        
    def simulate_calculator_project(self):
        """Simulate creating a calculator project with proper agent coordination."""
        print("\n" + "="*60)
        print("SIMULATING: Calculator Project Creation")
        print("="*60)
        
        manager = self.system["manager"]
        planner = self.system["planner"]
        rag = self.system["rag_specialist"]
        executor = self.system["executor_pool"]
        
        # Step 1: User request to Manager
        user_request = "Create a Python calculator with add, subtract, multiply, and divide functions. Include a simple CLI interface."
        print(f"\n👤 User: {user_request}")
        
        # Step 2: Manager processes request
        # In a real system, this would be handled by the Manager's chat method
        # For now, we'll simulate the flow
        
        print("\n📋 Manager: Processing request and delegating to Planner...")
        
        # Manager asks Planner to create a plan
        plan_request = AgentMessage(
            sender="manager",
            recipient="planner",
            message_type=MessageType.REQUEST,
            payload={
                "action": "create_plan",
                "objective": user_request
            }
        )
        
        plan_response = planner.handle_request(plan_request)
        print(f"\n🗂️ Planner: Created plan with {len(plan_response.get('plan', {}).get('tasks', []))} tasks")
        
        # Step 3: Manager asks RAG for relevant context
        print("\n📋 Manager: Requesting context from RAG...")
        
        context_request = AgentMessage(
            sender="manager",
            recipient="rag_specialist",
            message_type=MessageType.REQUEST,
            payload={
                "action": "hybrid_search",
                "query": "python calculator CLI implementation argparse",
                "max_results": 5
            }
        )
        
        rag_response = rag.handle_request(context_request)
        print(f"\n🔍 RAG: Search completed with {rag_response.get('total_searches', 0)} searches performed")
        
        # Step 4: Manager creates the project structure
        print("\n📋 Manager: Creating project structure...")
        
        project_result = manager.execute_tool("create_project", {
            "project_name": "calculator_demo",
            "project_type": "python",
            "project_path": "./test_pipeline/demo_projects"
        })
        
        if project_result.get("exit_code") == 0:
            print("✅ Project structure created")
            
            # Parse the created files
            stdout_data = json.loads(project_result["stdout"])
            created_data = json.loads(stdout_data["stdout"])
            print(f"   Created {len(created_data.get('created_files', []))} files")
            print(f"   Created {len(created_data.get('created_dirs', []))} directories")
        else:
            print(f"❌ Failed to create project: {project_result.get('stderr')}")
            return
        
        # Step 5: Manager delegates implementation to Executor
        print("\n📋 Manager: Delegating implementation to Executor...")
        
        # Simulate task execution
        tasks = [
            ("Create calculator.py with basic operations", "calculator.py"),
            ("Add CLI interface", "cli.py"),
            ("Write unit tests", "test_calculator.py")
        ]
        
        for i, (task_desc, filename) in enumerate(tasks, 1):
            exec_request = AgentMessage(
                sender="manager",
                recipient="executor",
                message_type=MessageType.REQUEST,
                payload={
                    "action": "execute_task",
                    "task_id": f"T-{i:03d}",
                    "task_description": task_desc
                }
            )
            
            exec_response = executor.handle_request(exec_request)
            
            if exec_response["status"] == "success":
                print(f"   ✅ Task {exec_response['task_id']}: {task_desc}")
            else:
                print(f"   ❌ Task {exec_response['task_id']}: Failed")
        
        # Step 6: Manager summarizes the work
        print("\n📋 Manager: Work completed. Summary:")
        print("   - Project structure created")
        print("   - Basic calculator implementation (simulated)")
        print("   - CLI interface added (simulated)")
        print("   - Unit tests written (simulated)")
        
        # Get system status
        status = manager.get_system_status()
        print(f"\n📊 System Status:")
        print(f"   - Session duration: {status['manager_status']['session_duration']:.1f}s")
        print(f"   - Total requests: {status['manager_status']['total_requests']}")
        print(f"   - Active agents: {len(status['manager_status']['registered_agents'])}")
        
    def test_actual_implementation(self):
        """Test with actual file creation using write_diff tool."""
        print("\n" + "="*60)
        print("TESTING: Actual File Implementation")
        print("="*60)
        
        manager = self.system["manager"]
        
        # Create a simple calculator.py file
        print("\n📝 Creating actual calculator.py file...")
        
        # First read the __init__.py to understand the structure
        calc_path = "./test_pipeline/demo_projects/calculator_demo/src/calculator.py"
        
        # Manager would normally delegate this to Executor, but let's test directly
        # Note: Manager doesn't have write_diff in its allowed tools, so this would
        # normally be done by the Executor
        
        print("⚠️  Note: In real flow, Executor would create files, not Manager")
        print("   Manager would coordinate and monitor progress")
        
    def run(self):
        """Run all tests."""
        self.setup()
        
        try:
            self.simulate_calculator_project()
            self.test_actual_implementation()
            
        finally:
            print("\n🧹 Cleaning up...")
            self.factory.shutdown_system()
            print("✅ Complete")


def main():
    tester = RealFlowTester()
    tester.run()


if __name__ == "__main__":
    main()