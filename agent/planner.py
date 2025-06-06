# coding-agent/agent/planner.py

import yaml
import re
import os
from pathlib import Path
from typing import Optional

from agent.config import get_settings
from agent.tasks.schema import Plan, Task, Budget
from agent.tasks.manager import PlanManager
from agent.llm import LLMClient

class Planner:
    def __init__(self):
        self.settings = get_settings()
        self.home = Path(self.settings.agent_home)
        self.manager = PlanManager()
        # Choose model for planning
        self.model = getattr(self.settings, 'planner_model', None) or self.settings.model_router_default
        self.llm = LLMClient(self.model, component="planner")

    def _get_existing_tasks(self) -> Optional[Plan]:
        return self.manager.load_latest_plan()

    def _next_task_id(self, existing_plan: Optional[Plan]) -> int:
        if not existing_plan or not existing_plan.tasks:
            return 1
        nums = [int(re.match(r"T-(\d+)", t.id).group(1)) for t in existing_plan.tasks]
        return max(nums) + 1

    def _build_prompt(self, request: str, existing_plan: Optional[Plan]) -> dict:
        """
        Returns a dict of messages for ChatCompletion: {'model':..., 'messages': [...]}
        """
        # Prepare existing_tasks YAML
        if existing_plan:
            existing_tasks_data = {"tasks": [t.model_dump(exclude_none=True) for t in existing_plan.tasks]}
        else:
            existing_tasks_data = {}

        system_msg = (
            "You are a task planner AI. Given a high‐level engineering request, decompose it into discrete tasks, each with:\n"
            "  - A unique Task ID of the form T-<sequential integer> (continuing from existing tasks).\n"
            "  - A brief description (under 100 characters).\n"
            "  - A list of acceptance tests (shell or pytest commands) that verify completion.\n"
            "  - A budget specifying tokens and dollars (e.g., 2000 tokens, $0.05).\n"
            "  - An owner ('agent' or 'human').\n"
            "Output must be valid YAML following this schema:\n"
            "```yaml\n"
            "tasks:\n"
            "  - id: T-<number>\n"
            "    description: \"<text>\"\n"
            "    accept_tests:\n"
            "      - \"<cmd1>\"\n"
            "      - \"<cmd2>\"\n"
            "    budget:\n"
            "      tokens: <int>\n"
            "      dollars: <float>\n"
            "    owner: agent\n"
            "```\n"
            "Do NOT output any other keys. Ensure the YAML is parseable by a strict parser.\n"
            "Existing tasks (if any) will be provided as context in YAML under 'existing_tasks:'. "
            "Continue numbering from the maximum existing ID + 1."
        )

        user_msg = {
            "existing_tasks": existing_tasks_data,
            "request": request,
            "defaults": {
                "tokens": self.settings.retrieval.get("planner_defaults_tokens", 2000),
                "dollars": self.settings.retrieval.get("planner_defaults_dollars", 0.05),
                "owner": "agent"
            }
        }

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": yaml.safe_dump(user_msg, sort_keys=False)}
        ]

        return {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 2000
        }

    def generate_plan(self, request: str) -> Plan:
        """
        Create or update a plan based on `request`. Returns the Plan object.
        """
        existing = self._get_existing_tasks()
        prompt = self._build_prompt(request, existing)

        # Call LLM
        try:
            thinking_mode = getattr(self.settings, 'gemini_thinking_mode', False)
            reply = self.llm.chat_completion(
                messages=prompt["messages"],
                temperature=prompt.get("temperature", 0.2),
                max_tokens=prompt.get("max_tokens", 1000),
                thinking_mode=thinking_mode
            )
        except Exception as e:
            raise RuntimeError(f"Planner LLM call failed: {e}")

        # Parse YAML from `reply`
        try:
            # Handle case where LLM wraps YAML in markdown code blocks
            yaml_text = reply.strip()
            if yaml_text.startswith("```yaml"):
                yaml_text = yaml_text[7:]  # Remove ```yaml
            elif yaml_text.startswith("```"):
                yaml_text = yaml_text[3:]  # Remove ```
            if yaml_text.endswith("```"):
                yaml_text = yaml_text[:-3]  # Remove trailing ```
            yaml_text = yaml_text.strip()
            
            data = yaml.safe_load(yaml_text)
            new_plan = Plan.model_validate(data)
        except Exception as e:
            raise ValueError(f"Failed to parse plan YAML: {e}\nYAML was:\n{reply}")

        # Merge with existing plan, preserving status
        merged_plan = self.manager.merge_and_save(new_plan)
        return merged_plan