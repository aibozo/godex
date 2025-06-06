# coding-agent/tests/test_executor.py

import os
import sys
import time
import json
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from agent.executor import Executor
from agent.tasks.schema import Task, Budget, Plan
from agent.tasks.manager import PlanManager

# --------------------------------------------------------------------------------
# Helper: stub ChatCompletion for diff generation and reflexion
# --------------------------------------------------------------------------------

class DummyChoice:
    def __init__(self, content):
        self.message = MagicMock(content=content)

class DummyResponse:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]

# --------------------------------------------------------------------------------
# Create a simple repo for testing:
# - A file 'hello.py' with a failing test
# - A test file 'tests/test_hello.py' that tests for function 'greet'
# --------------------------------------------------------------------------------

@pytest.fixture(scope="function")
def demo_repo(tmp_path, monkeypatch):
    """
    Set up:
      hello.py (empty or stub)
      tests/test_hello.py that expects greet() to return 'hello'
    """
    os.chdir(tmp_path)
    # Initialize git
    subprocess = __import__("subprocess")
    subprocess.run(["git", "init", "-b", "main"], check=True)

    # Create hello.py without greet() to cause initial failure
    hello = tmp_path / "hello.py"
    hello.write_text("")

    # Create tests directory
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_hello.py"
    test_file.write_text(
        "from hello import greet\n"
        "def test_greet():\n"
        "    assert greet() == 'hello'\n"
    )

    # Create a basic .cokeydex.yml
    (tmp_path / ".cokeydex.yml").write_text("""
openai_api_key: "test"
anthropic_api_key: ""
cost_cap_daily: 20.0
memory_summarise_threshold: 1000
max_tool_calls_per_task: 5
max_reflexion_retries: 1
consecutive_failure_threshold: 1
test_command: "pytest -q"
lint_command: "echo 'Linting OK'"
tools_allowed:
  - read_file
  - write_diff
  - run_tests
  - static_analyze
  - grep
  - vector_search
retrieval:
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
""")
    # Create initial plan with one task: Add greet() to hello.py
    task = Task(
        id="T-1",
        description="Implement greet() in hello.py",
        accept_tests=["pytest -q"],
        budget=Budget(tokens=500, dollars=0.01),
        owner="agent",
        status="pending"
    )
    plan = Plan(tasks=[task])
    pm = PlanManager()
    pm.save_plan(plan)

    # Ensure memory folders exist
    (tmp_path / "memory" / "scratch").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "archive").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "plans").mkdir(parents=True, exist_ok=True)

    # Create empty BM25 index directory
    (tmp_path / "bm25_index").mkdir(exist_ok=True)

    # Monkeypatch AGENT_HOME
    monkeypatch.setenv("AGENT_HOME", str(tmp_path))

    # Git add initial files
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

    return tmp_path

# --------------------------------------------------------------------------------
# 1. Happy Path: stub LLM returns diff that adds greet()
# --------------------------------------------------------------------------------

@patch("agent.tools.core.invoke_tool")
@patch("agent.retrieval.orchestrator.HybridRetriever.fetch_context")
@patch("openai.ChatCompletion.create")
def test_executor_happy_path(mock_create, mock_fetch, mock_tool, demo_repo):
    # Mock retriever to return empty context
    mock_fetch.return_value = []
    
    # Mock tool responses
    def tool_side_effect(request_json):
        request = json.loads(request_json)
        if request["name"] == "write_diff":
            # Apply the diff manually
            hello_py = demo_repo / "hello.py"
            hello_py.write_text("def greet():\n    return 'hello'\n")
            return json.dumps({"exit_code": 0, "stdout": "Diff applied", "stderr": ""})
        elif request["name"] == "run_tests":
            # Run actual tests
            subprocess = __import__("subprocess")
            proc = subprocess.run(["pytest", "-q"], cwd=demo_repo, capture_output=True, text=True)
            return json.dumps({"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        elif request["name"] == "static_analyze":
            return json.dumps({"exit_code": 0, "stdout": "Linting OK", "stderr": ""})
        return json.dumps({"exit_code": 1, "stdout": "", "stderr": "Unknown tool"})
    
    mock_tool.side_effect = tool_side_effect
    # Stub LLM to return a diff that adds greet()
    diff_text = (
        "--- a/hello.py\n"
        "+++ b/hello.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+def greet():\n"
        "+    return 'hello'\n"
    )
    mock_create.return_value = DummyResponse(diff_text)

    executor = Executor()
    
    # Debug: check memory content
    mm = executor.mm
    
    executor.run_task("T-1")
    
    # Print scratch content for debugging
    scratch_content = mm.read_scratch("T-1")
    if scratch_content:
        print(f"Scratch content:\n{scratch_content}")

    # Check current branch
    subprocess = __import__("subprocess")
    current_branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=demo_repo).decode().strip()
    print(f"Current branch: {current_branch}")
    
    # Check all branches
    all_branches = subprocess.check_output(["git", "branch", "-a"], cwd=demo_repo).decode()
    print(f"All branches:\n{all_branches}")
    
    # If on main and agent branch exists, checkout the agent branch
    if current_branch == "main" and "agent/T-1" in all_branches:
        subprocess.run(["git", "checkout", "agent/T-1"], cwd=demo_repo, check=True)

    # After execution, hello.py should contain greet()
    content = (demo_repo / "hello.py").read_text()
    assert "def greet()" in content

    # Tests should pass now
    subprocess = __import__("subprocess")
    proc = subprocess.Popen(
        "pytest -q", shell=True, cwd=demo_repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    out, err = proc.communicate(timeout=10)
    assert proc.returncode == 0

    # Check that a branch 'agent/T-1' exists
    branches = subprocess.check_output(["git", "branch"], cwd=demo_repo).decode()
    assert "agent/T-1" in branches

    # Check task status updated to done in latest plan
    pm = PlanManager()
    plan = pm.load_latest_plan()
    t1 = next(t for t in plan.tasks if t.id == "T-1")
    assert t1.status == "done"

# --------------------------------------------------------------------------------
# 2. Test Failure + Reflexion: First diff fails, reflexion produces correct diff
# --------------------------------------------------------------------------------

@patch("agent.tools.core.invoke_tool")
@patch("agent.retrieval.orchestrator.HybridRetriever.fetch_context")
@patch("openai.ChatCompletion.create")
def test_executor_reflexion_success(mock_create, mock_fetch, mock_tool, demo_repo):
    # Mock retriever to return empty context
    mock_fetch.return_value = []
    
    # Track if diff was applied
    diff_applied = [False]
    
    # Mock tool responses
    def tool_side_effect(request_json):
        request = json.loads(request_json)
        if request["name"] == "write_diff":
            # Only apply if second diff (good one)
            if not diff_applied[0] and request["args"]["diff"]:
                hello_py = demo_repo / "hello.py"
                hello_py.write_text("def greet():\n    return 'hello'\n")
                diff_applied[0] = True
            return json.dumps({"exit_code": 0, "stdout": "Diff applied", "stderr": ""})
        elif request["name"] == "run_tests":
            # Run actual tests
            subprocess = __import__("subprocess")
            proc = subprocess.run(["pytest", "-q"], cwd=demo_repo, capture_output=True, text=True)
            return json.dumps({"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        elif request["name"] == "static_analyze":
            return json.dumps({"exit_code": 0, "stdout": "Linting OK", "stderr": ""})
        return json.dumps({"exit_code": 1, "stdout": "", "stderr": "Unknown tool"})
    
    mock_tool.side_effect = tool_side_effect
    """
    - First LLM call returns a diff that does NOT implement greet() properly.
    - Tests still fail → Reflexion triggers.
    - Second LLM call returns correct diff → tests pass.
    """
    # Sequence of responses:
    # 1st call: bad diff (empty or incorrect)
    bad_diff = ""  # no changes
    # 2nd call (Reflexion): LLM provides critique (ignored by Executor)
    # for simplicity, respond with some critique (not used directly)
    critique = "Bullet 1: greet() missing\nBullet 2: ..."
    # 3rd call: correct diff
    good_diff = (
        "--- a/hello.py\n"
        "+++ b/hello.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+def greet():\n"
        "+    return 'hello'\n"
    )

    # Configure mock to return in sequence
    mock_create.side_effect = [
        DummyResponse(bad_diff),     # _build_diff_prompt → no diff
        DummyResponse(critique),     # _do_reflexion → critique
        DummyResponse(good_diff)     # Next diff generation
    ]

    executor = Executor()
    executor.run_task("T-1")

    # After execution, hello.py should now have greet()
    content = (demo_repo / "hello.py").read_text()
    assert "def greet()" in content

    # Task status should be done
    pm = PlanManager()
    plan = pm.load_latest_plan()
    t1 = next(t for t in plan.tasks if t.id == "T-1")
    assert t1.status == "done"

# --------------------------------------------------------------------------------
# 3. Failure After Retries: Always bad diff → roll back branch, status=failed
# --------------------------------------------------------------------------------

@patch("agent.tools.core.invoke_tool")
@patch("agent.retrieval.orchestrator.HybridRetriever.fetch_context")
@patch("openai.ChatCompletion.create")
def test_executor_failure_and_rollback(mock_create, mock_fetch, mock_tool, demo_repo):
    # Mock retriever to return empty context
    mock_fetch.return_value = []
    
    # Mock tool responses - tests always fail
    def tool_side_effect(request_json):
        request = json.loads(request_json)
        if request["name"] == "write_diff":
            return json.dumps({"exit_code": 0, "stdout": "Diff applied", "stderr": ""})
        elif request["name"] == "run_tests":
            # Tests fail because greet() is missing
            return json.dumps({"exit_code": 1, "stdout": "", "stderr": "ImportError: cannot import name 'greet' from 'hello'"})
        elif request["name"] == "static_analyze":
            return json.dumps({"exit_code": 0, "stdout": "Linting OK", "stderr": ""})
        return json.dumps({"exit_code": 1, "stdout": "", "stderr": "Unknown tool"})
    
    mock_tool.side_effect = tool_side_effect
    # LLM always returns bad diff (empty)
    mock_create.return_value = DummyResponse("")

    executor = Executor()
    executor.run_task("T-1")

    # Branch 'agent/T-1' should NOT exist (rolled back)
    subprocess = __import__("subprocess")
    branches = subprocess.check_output(["git", "branch"], cwd=demo_repo).decode()
    assert "agent/T-1" not in branches

    # hello.py should still be empty
    content = (demo_repo / "hello.py").read_text()
    assert content.strip() == ""

    # Task status should be 'failed'
    pm = PlanManager()
    plan = pm.load_latest_plan()
    t1 = next(t for t in plan.tasks if t.id == "T-1")
    assert t1.status == "failed"