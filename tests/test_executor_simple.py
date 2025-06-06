# Simple test for executor without git/tools complexity

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from agent.executor import Executor
from agent.tasks.schema import Task, Budget, Plan
from agent.tasks.manager import PlanManager

class DummyChoice:
    def __init__(self, content):
        self.message = MagicMock(content=content)

class DummyResponse:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]

@pytest.fixture
def simple_setup(tmp_path, monkeypatch):
    """Minimal setup without git"""
    os.chdir(tmp_path)
    
    # Create config
    (tmp_path / ".cokeydex.yml").write_text("""
openai_api_key: "test"
test_command: "echo 'tests pass'"
lint_command: "echo 'lint pass'"
max_tool_calls_per_task: 3
max_reflexion_retries: 1
consecutive_failure_threshold: 2
""")
    
    # Create directories
    (tmp_path / "memory" / "plans").mkdir(parents=True)
    (tmp_path / "memory" / "scratch").mkdir(parents=True)
    (tmp_path / "bm25_index").mkdir()
    
    # Create a plan
    task = Task(
        id="T-1",
        description="Test task",
        accept_tests=["echo 'test'"],
        budget=Budget(tokens=100, dollars=0.01),
        owner="agent",
        status="pending"
    )
    pm = PlanManager()
    pm.save_plan(Plan(tasks=[task]))
    
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))
    return tmp_path

@patch("agent.executor.Executor._git")
@patch("agent.executor.Executor._git_checkout")
@patch("agent.executor.Executor._create_and_checkout_branch")
@patch("agent.executor.Executor._git_commit_all")
@patch("agent.executor.Executor._rollback_branch")
@patch("agent.tools.core.invoke_tool")
@patch("agent.retrieval.orchestrator.HybridRetriever.fetch_context")
@patch("openai.ChatCompletion.create")
def test_executor_logic(mock_create, mock_fetch, mock_tool, mock_rollback, 
                       mock_commit, mock_checkout_branch, mock_checkout, 
                       mock_git, simple_setup):
    """Test core executor logic without real git/tools"""
    
    # Mock retriever
    mock_fetch.return_value = []
    
    # Mock git operations
    mock_git.return_value = (True, "")
    
    # Mock tool calls
    def tool_effect(request_json):
        req = json.loads(request_json)
        if req["name"] == "write_diff":
            return json.dumps({"exit_code": 0, "stdout": "Applied", "stderr": ""})
        elif req["name"] in ["run_tests", "static_analyze"]:
            return json.dumps({"exit_code": 0, "stdout": "Pass", "stderr": ""})
        return json.dumps({"exit_code": 1, "stdout": "", "stderr": "Unknown"})
    
    mock_tool.side_effect = tool_effect
    
    # Mock LLM to return a diff
    mock_create.return_value = DummyResponse("--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-old\n+new")
    
    executor = Executor()
    executor.run_task("T-1")
    
    # Debug: print memory content
    scratch = executor.mm.read_scratch("T-1")
    if scratch:
        print(f"Scratch content:\n{scratch}")
    
    # Debug: check call counts
    print(f"Tool calls: {mock_tool.call_count}")
    print(f"LLM calls: {mock_create.call_count}")
    
    # Verify git operations were called
    mock_checkout_branch.assert_called_once_with("agent/T-1")
    
    # Check task status
    pm = PlanManager()
    plan = pm.load_latest_plan()
    task = next(t for t in plan.tasks if t.id == "T-1")
    
    if task.status == "done":
        mock_commit.assert_called_once()
        mock_checkout.assert_called_with("main")
        assert task.status == "done"
    else:
        # Task failed, check rollback was called
        mock_rollback.assert_called_once_with("agent/T-1")
        assert task.status == "failed"