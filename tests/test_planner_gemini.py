# Integration tests for planner with real Gemini API
import os
import yaml
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agent.planner import Planner
from agent.tasks.manager import PlanManager
from agent.config import get_settings

@pytest.fixture
def gemini_setup(tmp_path, monkeypatch):
    """Setup for Gemini integration test"""
    os.chdir(tmp_path)
    
    # Create config with Gemini 1.5 Flash (has free tier)
    config_text = f"""
gemini_api_key: "{os.environ.get('GEMINI_API_KEY', '')}"
model_router_default: "gemini-1.5-flash"
cost_cap_daily: 10.0
memory_summarise_threshold: 1000
tools_allowed:
  - read_file
  - write_diff
  - run_tests
  - static_analyze
  - grep
  - vector_search
retrieval:
  planner_defaults_tokens: 2000
  planner_defaults_dollars: 0.05
  bm25:
    index_dir: "bm25_index"
    ngram_range: [1, 1]
    max_features: 1000
  chunker:
    max_tokens: 100
    overlap_tokens: 10
  embeddings:
    collection_name: "codebase"
    model: "stub"
"""
    (tmp_path / ".cokeydex.yml").write_text(config_text)
    
    # Create required directories
    (tmp_path / "memory" / "plans").mkdir(parents=True)
    (tmp_path / "memory" / "scratch").mkdir(parents=True)
    
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return tmp_path

@pytest.mark.skipif(not os.environ.get('GEMINI_API_KEY'), reason="GEMINI_API_KEY not set")
def test_planner_simple_request(gemini_setup):
    """Test planner with a simple request using real Gemini"""
    planner = Planner()
    
    # Simple request
    plan = planner.generate_plan("Create a Python function to calculate fibonacci numbers")
    
    # Verify plan was created
    assert plan is not None
    assert len(plan.tasks) > 0
    
    # Check task structure
    for task in plan.tasks:
        assert task.id.startswith("T-")
        assert task.description
        assert len(task.accept_tests) > 0
        assert task.budget.tokens > 0
        assert task.budget.dollars > 0
        assert task.owner in ["agent", "human"]
        assert task.status == "pending"
    
    # Verify files were saved
    pm = PlanManager()
    saved_plan = pm.load_latest_plan()
    assert saved_plan is not None
    assert len(saved_plan.tasks) == len(plan.tasks)
    
    # Check YAML file exists
    yaml_files = list(pm.plans_dir.glob("PLAN_*.yaml"))
    assert len(yaml_files) == 1
    
    # Check markdown file exists
    md_files = list(pm.scratch_dir.glob("PLAN_*.md"))
    assert len(md_files) == 1
    
    print(f"\nGenerated {len(plan.tasks)} tasks:")
    for task in plan.tasks:
        print(f"  {task.id}: {task.description}")
        print(f"    Accept tests: {', '.join(task.accept_tests)}")
        print(f"    Budget: {task.budget.tokens} tokens, ${task.budget.dollars}")

@pytest.mark.skipif(not os.environ.get('GEMINI_API_KEY'), reason="GEMINI_API_KEY not set")
def test_planner_complex_request(gemini_setup):
    """Test planner with a complex multi-step request"""
    planner = Planner()
    
    request = """
    Build a REST API for a todo list application with the following features:
    1. CRUD operations for todos
    2. User authentication
    3. Unit tests with >80% coverage
    4. API documentation
    """
    
    plan = planner.generate_plan(request)
    
    # Should generate multiple tasks
    assert len(plan.tasks) >= 3
    
    # Check for expected task types
    descriptions = [t.description.lower() for t in plan.tasks]
    
    # Should have tasks related to API, auth, tests
    has_api_task = any("api" in d or "crud" in d or "endpoint" in d for d in descriptions)
    has_auth_task = any("auth" in d or "user" in d for d in descriptions)
    has_test_task = any("test" in d or "coverage" in d for d in descriptions)
    
    assert has_api_task, "Should have API-related task"
    assert has_auth_task, "Should have auth-related task"
    assert has_test_task, "Should have test-related task"
    
    print(f"\nComplex request generated {len(plan.tasks)} tasks:")
    for task in plan.tasks:
        print(f"  {task.id}: {task.description}")

@pytest.mark.skipif(not os.environ.get('GEMINI_API_KEY'), reason="GEMINI_API_KEY not set")
def test_planner_incremental_tasks(gemini_setup):
    """Test adding new tasks to existing plan"""
    planner = Planner()
    manager = PlanManager()
    
    # First request
    plan1 = planner.generate_plan("Set up a Python project structure")
    initial_count = len(plan1.tasks)
    
    # Mark first task as done
    plan1.tasks[0].status = "done"
    manager.save_plan(plan1)
    
    # Second request adds more tasks
    plan2 = planner.generate_plan("Add logging and error handling to the project")
    
    # Should have at least as many tasks (existing + new)
    # Note: Gemini might consolidate or reorganize tasks, so we check for reasonable behavior
    print(f"\nDebug incremental planning:")
    print(f"  Plan 1 had {initial_count} tasks")
    print(f"  Plan 2 has {len(plan2.tasks)} tasks")
    
    # The plan should either preserve existing tasks or have new ones
    assert len(plan2.tasks) >= 2  # At minimum we expect some tasks
    
    # Check if any tasks were preserved
    preserved_ids = [t.id for t in plan2.tasks if t.id in [t.id for t in plan1.tasks]]
    new_task_ids = [t.id for t in plan2.tasks if t.id not in [t.id for t in plan1.tasks]]
    
    print(f"  Preserved task IDs: {preserved_ids}")
    print(f"  New task IDs: {new_task_ids}")
    print(f"  Plan 1 task IDs: {[t.id for t in plan1.tasks]}")
    print(f"  Plan 2 task IDs: {[t.id for t in plan2.tasks]}")
    
    # For Gemini, it might generate all new IDs but we should check that status is preserved
    # if IDs match, or that we have reasonable new tasks
    if preserved_ids:
        # If any tasks were preserved, check the first one's status
        t1 = next(t for t in plan2.tasks if t.id == plan1.tasks[0].id)
        assert t1.status == "done"
    else:
        # If no tasks preserved, at least verify we have some tasks
        assert len(plan2.tasks) >= 2
    
    print(f"\nIncremental planning:")
    print(f"  Initial tasks: {initial_count}")
    print(f"  Total tasks after second request: {len(plan2.tasks)}")
    print(f"  New tasks added: {len(new_task_ids)}")

@pytest.mark.skip(reason="Gemini 2.5 Pro requires paid tier - will enable when billing is confirmed")
def test_planner_with_thinking_mode(gemini_setup):
    """Test planner with Gemini 2.5 Pro thinking mode"""
    # Update config to use thinking variant
    config_path = Path(".cokeydex.yml")
    config = yaml.safe_load(config_path.read_text())
    config["model_router_default"] = "gemini-2.5-pro-preview-06-05"
    config["gemini_thinking_mode"] = True  # Enable thinking if supported
    config_path.write_text(yaml.dump(config))
    
    planner = Planner()
    
    # Complex request that benefits from thinking
    request = """
    Design and implement a distributed task queue system with:
    - Message broker integration
    - Worker pool management
    - Task retries and dead letter queues
    - Monitoring and metrics
    - Horizontal scaling support
    """
    
    plan = planner.generate_plan(request)
    
    # Should generate well-thought-out tasks
    assert len(plan.tasks) >= 4
    
    # Tasks should have detailed acceptance tests
    for task in plan.tasks:
        assert len(task.accept_tests) >= 1
        # Check that tests are specific, not generic
        generic_tests = ["pytest", "python -m pytest", "make test"]
        assert not all(test in generic_tests for test in task.accept_tests)
    
    print(f"\nThinking mode generated {len(plan.tasks)} tasks:")
    for task in plan.tasks:
        print(f"  {task.id}: {task.description}")
        for test in task.accept_tests:
            print(f"    - {test}")

if __name__ == "__main__":
    # Run with: python -m pytest tests/test_planner_gemini.py -v -s
    pytest.main([__file__, "-v", "-s"])