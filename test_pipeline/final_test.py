#!/usr/bin/env python3
"""
Final comprehensive test of the multi-agent pipeline.

This demonstrates:
1. User gives a simple prompt to Manager
2. Manager orchestrates all agents
3. A working project is created
"""

import sys
import os
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from agent.orchestrator.orchestrating_manager import OrchestratingManager
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.executor_pool import ExecutorPool


def cleanup_workspace():
    """Clean up any previous test projects."""
    workspace = Path("./workspace")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(exist_ok=True)


def main():
    """Run the final pipeline test."""
    
    print("🚀 COKEYDEX FINAL PIPELINE TEST")
    print("="*60)
    print("This test demonstrates the full multi-agent pipeline")
    print("from a simple user prompt to project creation.")
    print("="*60)
    
    # Clean workspace
    cleanup_workspace()
    
    # Create the multi-agent system
    print("\n📋 Setting up multi-agent system...")
    
    manager = OrchestratingManager()
    rag = RAGSpecialist()
    planner = PlannerAgent()
    executor = ExecutorPool()
    
    # Register agents
    manager.register_agent("rag_specialist")
    manager.register_agent("planner")
    manager.register_agent("executor")
    
    print("✅ System ready")
    
    # Test prompts
    prompts = [
        {
            "prompt": "I need a Python calculator that can add, subtract, multiply, and divide two numbers.",
            "expected": "calculator project"
        },
        {
            "prompt": "What files were created?",
            "expected": "status update"
        }
    ]
    
    # Run tests
    for i, test in enumerate(prompts, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {test['expected']}")
        print('='*60)
        print(f"\n👤 User: {test['prompt']}")
        
        response = manager.chat(test['prompt'])
        
        print(f"\n🤖 Manager:\n{response}")
    
    # Show created files
    print(f"\n{'='*60}")
    print("CREATED FILES")
    print('='*60)
    
    workspace = Path("./workspace")
    if workspace.exists():
        for project_dir in workspace.iterdir():
            if project_dir.is_dir():
                print(f"\n📁 {project_dir.name}/")
                for file in project_dir.rglob("*"):
                    if file.is_file():
                        relative = file.relative_to(project_dir)
                        print(f"   - {relative}")
    
    # Show system stats
    status = manager.get_system_status()
    print(f"\n{'='*60}")
    print("SYSTEM STATISTICS")
    print('='*60)
    print(f"Total requests processed: {status['manager_status']['total_requests']}")
    print(f"Agents involved: {len(status['manager_status']['registered_agents'])}")
    print(f"Tasks completed: {len([t for t in manager.task_progress.values() if t['status'] == 'completed'])}")
    
    print("\n✅ Pipeline test complete!")
    print("\n💡 Next steps:")
    print("   1. Implement actual code generation in Executor")
    print("   2. Add real LLM calls for intelligent responses")
    print("   3. Improve task breakdown in Planner")
    print("   4. Add more sophisticated RAG retrieval")


if __name__ == "__main__":
    main()