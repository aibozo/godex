# coding-agent/tests/test_planner.py

import os
import sys
import yaml
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from agent.planner import Planner
from agent.tasks.schema import Plan, Task, Budget
from agent.tasks.manager import PlanManager

# --------------------------------------------------------------------------------
# Helper: stub OpenAI ChatCompletion response
# --------------------------------------------------------------------------------

class DummyChoice:
    def __init__(self, content):
        self.message = MagicMock(content=content)

class DummyResponse:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]

# --------------------------------------------------------------------------------
# Sample YAML reply from LLM
# --------------------------------------------------------------------------------

SAMPLE_YAML = """
tasks:
  - id: T-1
    description: "Initialize project repository"
    accept_tests:
      - "ls"
    budget:
      tokens: 1000
      dollars: 0.01
    owner: agent
  - id: T-2
    description: "Set up CI pipeline"
    accept_tests:
      - "pytest -q"
    budget:
      tokens: 1500
      dollars: 0.02
    owner: agent
"""

# --------------------------------------------------------------------------------
# Test cases
# --------------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def in_temp_dir(tmp_path, monkeypatch):
    """
    Run tests in a temp directory with a minimal .agent.yml
    """
    os.chdir(tmp_path)
    agent_yml = tmp_path / ".agent.yml"
    agent_yml.write_text("""
openai_api_key: "test"
anthropic_api_key: ""
cost_cap_daily: 20.0
memory_summarise_threshold: 1000
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
    # Ensure memory/plans and memory/scratch exist
    (tmp_path / "memory" / "plans").mkdir(parents=True)
    (tmp_path / "memory" / "scratch").mkdir(parents=True)
    yield

@patch("openai.ChatCompletion.create")
def test_generate_plan_creates_files(mock_create):
    # Stub LLM to return SAMPLE_YAML
    mock_create.return_value = DummyResponse(SAMPLE_YAML)

    planner = Planner()
    plan_obj = planner.generate_plan("Initialize project and CI")

    # Check that plan_obj matches SAMPLE_YAML
    assert isinstance(plan_obj, Plan)
    assert len(plan_obj.tasks) == 2
    assert plan_obj.tasks[0].id == "T-1"
    assert plan_obj.tasks[1].description == "Set up CI pipeline"

    # Verify YAML file was written
    pm = planner.manager
    yaml_files = list((Path(pm.plans_dir)).glob("PLAN_*.yaml"))
    assert len(yaml_files) == 1
    yaml_contents = yaml.safe_load(yaml_files[0].read_text())
    assert "tasks" in yaml_contents

    # Verify Markdown file was written
    md_file = Path(pm.scratch_dir) / f"{yaml_files[0].stem}.md"
    assert md_file.exists()
    md_text = md_file.read_text()
    assert "- [ ] T-1: Initialize project repository" in md_text
    assert "Acceptance: `ls`" in md_text

@patch("openai.ChatCompletion.create")
def test_merge_preserves_status(mock_create):
    # First, create an existing plan with T-1 marked as done
    manager = PlanManager()
    existing_plan = Plan(tasks=[
        Task(
            id="T-1",
            description="Old desc",
            accept_tests=["ls"],
            budget=Budget(tokens=500, dollars=0.005),
            owner="agent",
            status="done"
        )
    ])
    manager.save_plan(existing_plan)
    time.sleep(1)  # ensure timestamp difference

    # New YAML returned by LLM for the same T-1 (with updated desc)
    NEW_YAML = """
tasks:
  - id: T-1
    description: "Updated description"
    accept_tests:
      - "ls"
    budget:
      tokens: 800
      dollars: 0.01
    owner: agent
  - id: T-2
    description: "New Task"
    accept_tests:
      - "echo hi"
    budget:
      tokens: 600
      dollars: 0.005
    owner: agent
"""
    mock_create.return_value = DummyResponse(NEW_YAML)

    planner = Planner()
    new_plan = planner.generate_plan("Redefine existing and add new task")

    # T-1 should preserve status="done"
    t1 = next(t for t in new_plan.tasks if t.id == "T-1")
    assert t1.status == "done"
    assert t1.description == "Updated description"  # updated field

    # T-2 is new, status defaults to "pending"
    t2 = next(t for t in new_plan.tasks if t.id == "T-2")
    assert t2.status == "pending"

    # Confirm two plan files exist (original + merged)
    yaml_files = list((Path(planner.manager.plans_dir)).glob("PLAN_*.yaml"))
    assert len(yaml_files) == 2

def test_load_latest_plan_returns_none_when_empty():
    pm = PlanManager()
    # Ensure no plans exist by deleting any that might be there
    for f in pm.plans_dir.glob("PLAN_*.yaml"):
        f.unlink()
    assert pm.load_latest_plan() is None

def test_invalid_yaml_from_llm_raises(monkeypatch):
    # Stub LLM to return invalid YAML
    with patch("openai.ChatCompletion.create") as mock_create:
        mock_create.return_value = DummyResponse("not: valid: yaml: -")
        planner = Planner()
        with pytest.raises(ValueError):
            planner.generate_plan("Test invalid YAML")