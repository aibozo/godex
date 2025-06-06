# coding-agent/agent/tasks/manager.py

import os
import yaml
import datetime
from pathlib import Path
from typing import Optional

from agent.config import get_settings
from agent.tasks.schema import Plan, Task
from agent.memory.utils import atomic_write


class PlanManager:
    def __init__(self):
        self.settings = get_settings()
        self.home = Path(self.settings.agent_home)
        self.plans_dir = self.home / "memory" / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.scratch_dir = self.home / "memory" / "scratch"
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def _plan_yaml_path(self, timestamp: str) -> Path:
        return self.plans_dir / f"PLAN_{timestamp}.yaml"

    def _plan_md_path(self, timestamp: str) -> Path:
        return self.scratch_dir / f"PLAN_{timestamp}.md"

    def save_plan(self, plan: Plan) -> None:
        """
        Serialize `plan` to YAML and Markdown, then write to files with current UTC timestamp.
        """
        ts = self._timestamp()
        yaml_path = self._plan_yaml_path(ts)
        md_path = self._plan_md_path(ts)

        # 1. Dump YAML
        yaml_text = yaml.safe_dump(
            {"tasks": [t.model_dump(exclude_none=True) for t in plan.tasks]},
            sort_keys=False,
            explicit_start=True,
        )
        atomic_write(yaml_path, yaml_text)

        # 2. Render Markdown checklist
        md_lines = [f"# Plan ({ts})\n"]
        for task in plan.tasks:
            md_lines.append(f"- [ ] {task.id}: {task.description}")
            for cmd in task.accept_tests:
                md_lines.append(f"    - Acceptance: `{cmd}`")
            md_lines.append("")  # blank line between tasks

        md_content = "\n".join(md_lines)
        atomic_write(md_path, md_content)

    def load_latest_plan(self) -> Optional[Plan]:
        """
        Find the most recent PLAN_*.yaml in `plans_dir`, load and return as Plan.
        If none exist, return None.
        """
        files = sorted(self.plans_dir.glob("PLAN_*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return None
        latest = files[0]
        data = yaml.safe_load(latest.read_text())
        return Plan.model_validate(data)

    def merge_and_save(self, new_plan: Plan) -> Plan:
        """
        If an existing plan exists, merge on task IDs:
          - Keep existing tasks' `status` if IDs match.
        Otherwise, just save `new_plan`.
        Finally, write merged plan to disk and return it.
        """
        existing = self.load_latest_plan()
        if existing:
            # Build map from id → Task
            existing_map = {t.id: t for t in existing.tasks}
            merged_tasks = []
            for t in new_plan.tasks:
                if t.id in existing_map:
                    # Preserve status, owner, but update description/accept_tests/budget if changed
                    old = existing_map[t.id]
                    merged = Task(
                        id=t.id,
                        description=t.description,
                        accept_tests=t.accept_tests,
                        budget=t.budget,
                        owner=t.owner,
                        status=old.status or t.status
                    )
                else:
                    merged = t
                merged_tasks.append(merged)
            merged_plan = Plan(tasks=merged_tasks)
        else:
            merged_plan = new_plan

        self.save_plan(merged_plan)
        return merged_plan