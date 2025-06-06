#!/usr/bin/env python3
# tools/get_task_status.py

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


def main():
    if len(sys.argv) != 2:
        err = {"exit_code": 1, "stdout": "", "stderr": "Expected exactly one JSON arg"}
        print(json.dumps(err))
        sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
        task_id = args.get("task_id")
        
        if not task_id:
            # Return status of all tasks
            result = get_all_task_status()
        else:
            # Return status of specific task
            result = get_task_status(task_id)
        
        resp = {"exit_code": 0, "stdout": json.dumps(result), "stderr": ""}
        
    except Exception as e:
        resp = {"exit_code": 1, "stdout": "", "stderr": str(e)}

    print(json.dumps(resp))
    sys.exit(resp["exit_code"])


def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a specific task."""
    
    # Look for the task in latest plan
    plan_data = load_latest_plan()
    if not plan_data:
        return {
            "task_id": task_id,
            "status": "not_found",
            "message": "No plans found"
        }
    
    # Find the task
    for task in plan_data.get("tasks", []):
        if task.get("id") == task_id:
            return {
                "task_id": task_id,
                "status": task.get("status", "unknown"),
                "description": task.get("description", ""),
                "owner": task.get("owner", ""),
                "accept_tests": task.get("accept_tests", []),
                "budget": task.get("budget", {}),
                "found": True
            }
    
    return {
        "task_id": task_id,
        "status": "not_found",
        "message": f"Task {task_id} not found in current plan"
    }


def get_all_task_status() -> Dict[str, Any]:
    """Get status of all tasks in the current plan."""
    
    plan_data = load_latest_plan()
    if not plan_data:
        return {
            "total_tasks": 0,
            "tasks": [],
            "message": "No plans found"
        }
    
    tasks = plan_data.get("tasks", [])
    
    # Count tasks by status
    status_counts = {}
    task_list = []
    
    for task in tasks:
        status = task.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        
        task_list.append({
            "id": task.get("id"),
            "status": status,
            "description": task.get("description", ""),
            "owner": task.get("owner", ""),
        })
    
    return {
        "total_tasks": len(tasks),
        "status_counts": status_counts,
        "tasks": task_list,
        "plan_file": str(get_latest_plan_file()) if get_latest_plan_file() else None
    }


def load_latest_plan() -> Optional[Dict[str, Any]]:
    """Load the latest plan YAML file."""
    plan_file = get_latest_plan_file()
    if not plan_file or not plan_file.exists():
        return None
    
    try:
        with open(plan_file, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading plan file {plan_file}: {e}")
        return None


def get_latest_plan_file() -> Optional[Path]:
    """Find the most recent plan file."""
    # Look in memory/plans directory
    plans_dir = Path("memory/plans")
    if not plans_dir.exists():
        return None
    
    plan_files = list(plans_dir.glob("PLAN_*.yaml"))
    if not plan_files:
        return None
    
    # Sort by modification time, most recent first
    plan_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return plan_files[0]


if __name__ == "__main__":
    main()