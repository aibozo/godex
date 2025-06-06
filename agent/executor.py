# coding-agent/agent/executor.py

import os
import sys
import json
import shutil
import subprocess
import time
import traceback
from pathlib import Path
from typing import Tuple, Optional

import yaml

from agent.config import get_settings
from agent.tasks.manager import PlanManager
from agent.tasks.schema import Task, Plan
from agent.memory.manager import MemoryManager
from agent.tools.core import invoke_tool
from agent.retrieval.orchestrator import HybridRetriever
from agent.llm import LLMClient


class Executor:
    def __init__(self):
        self.settings = get_settings()
        self.home = Path(self.settings.agent_home)
        self.pm = PlanManager()
        self.mm = MemoryManager()
        self.retriever = HybridRetriever()
        # Use executor-specific model if configured, otherwise default
        model = self.settings.executor_model or self.settings.model_router_default
        self.llm = LLMClient(model, component="executor")

    # ------------------------------------------------------------
    # Public method: run a single task by ID
    # ------------------------------------------------------------
    def run_task(self, task_id: str) -> None:
        """
        Execute the task with id=task_id according to the ReAct loop.
        """
        # 1. Load the latest plan and find Task
        plan = self.pm.load_latest_plan()
        if not plan:
            print(f"[Executor] No plan found; aborting.")
            return
        task = next((t for t in plan.tasks if t.id == task_id), None)
        if not task:
            print(f"[Executor] Task {task_id} not found in plan.")
            return
        if task.status == "done":
            print(f"[Executor] Task {task_id} is already done; skipping.")
            return
        if task.status == "in_progress":
            print(f"[Executor] Task {task_id} is already in progress; skipping.")
            return

        # 2. Create and checkout new branch
        branch_name = f"agent/{task.id}"
        self._create_and_checkout_branch(branch_name)

        # 3. Mark in-progress in plan
        self._update_task_status(task, "in_progress")

        # 4. Begin ReAct loop
        success = self._react_loop(task)

        if success:
            # 5a. Commit final changes
            commit_msg = f"[Agent] Complete {task.id}: {task.description}"
            self._git_commit_all(commit_msg)

            # 5b. Update status to done
            self._update_task_status(task, "done")
            self.mm.append_scratch(task.id, f"**Task {task.id} completed successfully on branch {branch_name}.**")
            print(f"[Executor] Task {task.id} done; branch {branch_name} contains changes.")
        else:
            # 6. Rollback branch
            self._rollback_branch(branch_name)
            self._update_task_status(task, "failed")
            self.mm.append_scratch(task.id, f"**Task {task.id} failed after retries; rolled back.**")
            print(f"[Executor] Task {task.id} failed and was rolled back.")

        # 7. Checkout main branch
        self._git_checkout("main")

    # ------------------------------------------------------------
    # Public method: run all pending tasks in order
    # ------------------------------------------------------------
    def run_all(self) -> None:
        """
        Execute all tasks in the latest plan whose status != done.
        """
        plan = self.pm.load_latest_plan()
        if not plan:
            print("[Executor] No plan found; nothing to run.")
            return
        for task in plan.tasks:
            if task.status != "done":
                print(f"[Executor] Running task {task.id}: {task.description}")
                self.run_task(task.id)
            else:
                print(f"[Executor] Skipping {task.id}; already done.")

    # ------------------------------------------------------------
    # Core ReAct Loop
    # ------------------------------------------------------------
    def _react_loop(self, task: Task) -> bool:
        """
        Returns True if task completes successfully; False if failed after retries/rollback.
        """
        tool_calls = 0
        reflexion_retries = 0
        consecutive_failures = 0
        test_failures: str = ""  # preserve last test stderr for context

        while tool_calls < self.settings.max_tool_calls_per_task:
            # 1. Prepare prompt for LLM
            prompt_payload = self._build_diff_prompt(task, test_failures)
            # Call LLM for diff
            try:
                diff_text = self.llm.chat_completion(
                    messages=prompt_payload["messages"],
                    temperature=0.2,
                    # max_tokens will use model default
                )
            except Exception as e:
                self.mm.append_scratch(task.id, f"LLM call failed: {e}")
                return False

            self.mm.append_scratch(task.id, f"**Thought:** Generated diff:\n```diff\n{diff_text}\n```")

            if not diff_text:
                # No changes needed; run tests to verify
                test_ok, test_out, test_err = self._run_tests_and_lint()
                if test_ok:
                    return True
                else:
                    test_failures = test_out + "\n" + test_err
                    self.mm.append_scratch(task.id, f"**Observation:** Tests failing with no diff:\n```\n{test_failures}\n```")
                    # Reflexion
                    if self._should_reflect(reflexion_retries, consecutive_failures):
                        self._do_reflexion(task, test_failures)
                        reflexion_retries += 1
                        consecutive_failures += 1
                        continue
                    else:
                        return False

            # 2. Call write_diff tool
            tool_calls += 1
            write_req = {
                "name": "write_diff",
                "args": {"path": "./", "diff": diff_text},
                "secure": True,
                "timeout_seconds": 60
            }
            write_resp = json.loads(invoke_tool(json.dumps(write_req)))
            if write_resp["exit_code"] != 0:
                err = write_resp["stderr"]
                self.mm.append_scratch(task.id, f"**Observation:** write_diff failed: {err}")
                # Treat as failure → Reflexion
                test_failures = err
                if self._should_reflect(reflexion_retries, consecutive_failures):
                    self._do_reflexion(task, test_failures)
                    reflexion_retries += 1
                    consecutive_failures += 1
                    continue
                else:
                    return False
            else:
                self.mm.append_scratch(task.id, f"**Observation:** Diff applied successfully.")

            # 3. Run tests
            test_ok, test_out, test_err = self._run_tests_and_lint()
            if test_ok:
                return True
            else:
                test_failures = test_out + "\n" + test_err
                self.mm.append_scratch(task.id, f"**Observation:** Tests failing:\n```\n{test_failures}\n```")
                # Reflexion
                if self._should_reflect(reflexion_retries, consecutive_failures):
                    self._do_reflexion(task, test_failures)
                    reflexion_retries += 1
                    consecutive_failures += 1
                    continue
                else:
                    return False

        # Exceeded max tool calls
        self.mm.append_scratch(task.id, f"**Executor:** Reached max tool calls without success.")
        return False

    # ------------------------------------------------------------
    # Helper: Build diff prompt for LLM
    # ------------------------------------------------------------
    def _build_diff_prompt(self, task: Task, test_failures: str) -> dict:
        """
        Constructs the messages list for LLM to generate a diff.
        """
        # 1. System message
        system_msg = (
            "You are a coding agent. Given the current task, generate a unified diff to complete the task. "
            "Output only valid unified diff format. If no changes are needed, output an empty response."
        )

        # 2. Gather code context via Retrieval
        code_chunks = self.retriever.fetch_context(task.description, top_n=5)
        # Format code_context as YAML list
        code_context = []
        for chunk in code_chunks:
            code_context.append({
                "file_path": chunk["file_path"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "text": chunk["text"]
            })
        # 3. Gather memory (scratchpad)
        memory_text = self.mm.read_scratch(task.id)

        # 4. Compose user message as YAML
        user_dict = {
            "task_id": task.id,
            "description": task.description,
            "code_context": code_context,
            "test_failures": test_failures or "",
            "memory": memory_text or ""
        }
        user_msg = yaml.safe_dump(user_dict, sort_keys=False)

        return {
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ]
        }

    # ------------------------------------------------------------
    # Helper: Run tests and lint via tools
    # ------------------------------------------------------------
    def _run_tests_and_lint(self) -> Tuple[bool, str, str]:
        """
        Returns (tests_and_lint_passed, stdout, stderr).
        """
        # 1. run_tests
        run_req = {
            "name": "run_tests",
            "args": {"cmd": self.settings.test_command},
            "secure": True,
            "timeout_seconds": 120
        }
        run_resp = json.loads(invoke_tool(json.dumps(run_req)))
        tests_ok = (run_resp["exit_code"] == 0)
        out = run_resp["stdout"]
        err = run_resp["stderr"]

        # 2. static_analyze
        lint_req = {
            "name": "static_analyze",
            "args": {"cmd": self.settings.lint_command},
            "secure": True,
            "timeout_seconds": 60
        }
        lint_resp = json.loads(invoke_tool(json.dumps(lint_req)))
        lint_ok = (lint_resp["exit_code"] == 0)
        out += "\n" + lint_resp["stdout"]
        err += "\n" + lint_resp["stderr"]

        return (tests_ok and lint_ok, out, err)

    # ------------------------------------------------------------
    # Helper: Decide if we should reflex and retry
    # ------------------------------------------------------------
    def _should_reflect(self, reflexion_retries: int, consecutive_failures: int) -> bool:
        if reflexion_retries < self.settings.max_reflexion_retries and consecutive_failures < self.settings.consecutive_failure_threshold:
            return True
        return False

    # ------------------------------------------------------------
    # Helper: Perform a Reflexion step
    # ------------------------------------------------------------
    def _do_reflexion(self, task: Task, test_failures: str) -> None:
        """
        Ask LLM to self‐critique last failure and append to memory.
        """
        prompt = (
            f"Task {task.id} failed tests/lint. Here are failure logs:\n\n```\n{test_failures}\n```\n"
            f"Explain in 3 bullet points why the failure occurred and suggest what to change next time."
        )
        try:
            critique = self.llm.chat_completion(
                messages=[{"role": "system", "content": "You are a reflective coding agent."},
                          {"role": "user", "content": prompt}],
                temperature=0.2,
                # max_tokens will use model default
            )
        except Exception as e:
            critique = f"(Reflexion failed: {e})"

        self.mm.append_scratch(task.id, f"**Reflexion:**\n{critique}")

    # ------------------------------------------------------------
    # Helper: Update task status in plan YAML
    # ------------------------------------------------------------
    def _update_task_status(self, task: Task, new_status: str) -> None:
        """
        Load latest plan, set task.status=new_status, merge & save.
        """
        plan = self.pm.load_latest_plan()
        for t in plan.tasks:
            if t.id == task.id:
                t.status = new_status
        self.pm.merge_and_save(plan)

    # ------------------------------------------------------------
    # Helper: Git operations
    # ------------------------------------------------------------
    def _git(self, cmd: str) -> Tuple[bool, str]:
        """
        Run a git command in the repo root; return (success, output).
        """
        proc = subprocess.Popen(
            cmd, shell=True, cwd=self.home,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        out, _ = proc.communicate()
        return (proc.returncode == 0, out)

    def _create_and_checkout_branch(self, branch: str) -> None:
        """
        Create a new branch from main and checkout.
        """
        # Ensure main is up-to-date
        self._git("git checkout main")
        # Create branch (force if exists)
        self._git(f"git branch -D {branch}")
        success, out = self._git(f"git checkout -b {branch}")
        if not success:
            raise RuntimeError(f"Failed to create branch {branch}: {out}")

    def _git_commit_all(self, message: str) -> None:
        """
        Stage all changes and commit.
        """
        self._git("git add .")
        success, out = self._git(f"git commit -m {json.dumps(message)}")
        if not success:
            raise RuntimeError(f"Git commit failed: {out}")

    def _git_checkout(self, branch: str) -> None:
        """
        Checkout existing branch (e.g., 'main').
        """
        self._git(f"git checkout {branch}")

    def _rollback_branch(self, branch: str) -> None:
        """
        Delete the branch and reset to main.
        """
        # Checkout main
        self._git("git checkout main")
        # Delete branch
        self._git(f"git branch -D {branch}")
        # Discard any changes (in case diffs applied but commit failed)
        self._git("git reset --hard")