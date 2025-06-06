# Integration test using real Gemini API
import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agent.planner import Planner
from agent.tasks.manager import PlanManager
from agent.llm import LLMClient

@pytest.fixture
def gemini_setup(tmp_path, monkeypatch):
    """Setup for Gemini integration test"""
    os.chdir(tmp_path)
    
    # Create a minimal config with Gemini
    config_text = f"""
gemini_api_key: "{os.environ.get('GEMINI_API_KEY', '')}"
model_router_default: "gemini-1.5-flash"
"""
    (tmp_path / ".cokeydex.yml").write_text(config_text)
    
    # Create required directories
    (tmp_path / "memory" / "plans").mkdir(parents=True)
    (tmp_path / "memory" / "scratch").mkdir(parents=True)
    
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return tmp_path

@pytest.mark.skipif(not os.environ.get('GEMINI_API_KEY'), reason="GEMINI_API_KEY not set")
def test_planner_with_gemini(gemini_setup):
    """Test that planner works with Gemini API"""
    planner = Planner()
    
    # Simple request
    plan = planner.generate_plan("Create a hello world Python script")
    
    # Verify plan was created
    assert plan is not None
    assert len(plan.tasks) > 0
    
    # Check first task
    task = plan.tasks[0]
    assert task.id.startswith("T-")
    assert task.description
    assert len(task.accept_tests) > 0
    assert task.budget.tokens or task.budget.dollars
    
    # Verify files were saved
    pm = PlanManager()
    saved_plan = pm.load_latest_plan()
    assert saved_plan is not None
    assert len(saved_plan.tasks) == len(plan.tasks)
    
    print(f"Generated {len(plan.tasks)} tasks:")
    for task in plan.tasks:
        print(f"  {task.id}: {task.description}")

@pytest.mark.skipif(not os.environ.get('GEMINI_API_KEY'), reason="GEMINI_API_KEY not set")
def test_llm_client_gemini():
    """Test LLM client with Gemini directly"""
    # Skip if no API key
    if not os.environ.get('GEMINI_API_KEY'):
        pytest.skip("GEMINI_API_KEY not set")
    
    client = LLMClient("gemini-1.5-flash")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello Gemini!' and nothing else."}
    ]
    
    response = client.chat_completion(messages)
    assert response
    assert "Gemini" in response or "gemini" in response
    print(f"Gemini response: {response}")