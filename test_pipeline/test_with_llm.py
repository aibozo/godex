#!/usr/bin/env python3
"""
Test the pipeline with actual LLM capabilities.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from agent.orchestrator.orchestrating_manager import OrchestratingManager
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.executor_pool import ExecutorPool
import shutil


def cleanup_workspace():
    """Clean workspace."""
    workspace = Path("./workspace")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(exist_ok=True)


def main():
    print("🚀 Testing Pipeline with LLM Capabilities")
    print("="*60)
    
    cleanup_workspace()
    
    # Create agents
    print("\n📋 Creating agents with LLM capabilities...")
    manager = OrchestratingManager()
    rag = RAGSpecialist()
    planner = PlannerAgent()
    executor = ExecutorPool()
    
    # Register agents
    manager.register_agent("rag_specialist")
    manager.register_agent("planner")
    manager.register_agent("executor")
    
    print("✅ Agents ready with Gemini 2.5 Flash")
    
    # Test the Planner with actual LLM
    print("\n" + "="*60)
    print("TEST: Planner using LLM")
    print("="*60)
    
    from agent.communication.protocol import AgentMessage, MessageType
    
    plan_message = AgentMessage(
        sender="test",
        recipient="planner",
        message_type=MessageType.REQUEST,
        payload={
            "action": "create_plan",
            "objective": "Create a Python calculator with add, subtract, multiply, divide functions and a CLI interface"
        }
    )
    
    print("\n📝 Sending request to Planner...")
    plan_response = planner.handle_request(plan_message)
    
    print(f"\nPlanner response status: {plan_response['status']}")
    if plan_response['status'] == 'success':
        print("\n📋 Generated Plan:")
        for task in plan_response['plan']['tasks']:
            print(f"   - {task['id']}: {task['description']}")
            print(f"     Complexity: {task.get('estimated_complexity', 'unknown')}")
    else:
        print(f"Error: {plan_response.get('error', 'Unknown error')}")
    
    # Test the complete flow
    print("\n" + "="*60)
    print("TEST: Complete Flow with Manager")
    print("="*60)
    
    response = manager.chat("Create a simple Python calculator that can add, subtract, multiply, and divide numbers")
    print(f"\n🤖 Manager Response:\n{response}")
    
    # Check what was actually created
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    workspace = Path("./workspace")
    if workspace.exists():
        for project_dir in workspace.iterdir():
            if project_dir.is_dir():
                print(f"\n📁 Created: {project_dir.name}/")
                for file in project_dir.rglob("*"):
                    if file.is_file():
                        print(f"   - {file.relative_to(project_dir)}")


if __name__ == "__main__":
    main()