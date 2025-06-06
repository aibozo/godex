# coding-agent/agent/tools/core.py

import subprocess
import sys
import json
import threading
import shlex
import os
import time
import traceback
from pathlib import Path
from typing import Any, Dict

from .schema import ToolRequest
from .permissions import ACL

# Global ACL instance (lazy loaded)
_acl: ACL | None = None

def get_acl() -> ACL:
    global _acl
    if _acl is None:
        _acl = ACL()
    return _acl

def _find_firejail() -> bool:
    import shutil
    return shutil.which("firejail") is not None

def _run_with_firejail(command: str, timeout: int) -> Dict[str, Any]:
    """
    Run `command` under Firejail. Returns a dict {exit_code, stdout, stderr}.
    """
    firejail_path = "firejail"
    # --quiet: suppress Firejail banner
    full_cmd = f"{firejail_path} --quiet {command}"
    return _run_subprocess(full_cmd, timeout)

def _run_with_docker(command: str, timeout: int) -> Dict[str, Any]:
    """
    Run `command` inside the `cokeydex-runner:latest` Docker container.
    We assume the current working directory is mounted at /workspace.
    """
    # Mount the host's current directory as /workspace, working dir inside container.
    cwd = os.getcwd()
    docker_cmd = (
        f"docker run --rm -v {shlex.quote(cwd)}:/workspace -w /workspace "
        "cokeydex-runner:latest /bin/bash -lc "
        f"{shlex.quote(command)}"
    )
    return _run_subprocess(docker_cmd, timeout)

def _run_subprocess(raw_command: str, timeout: int) -> Dict[str, Any]:
    """
    Execute `raw_command` via shell, enforce timeout, capture stdout/stderr.
    """
    # Start subprocess
    proc = subprocess.Popen(
        raw_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    # Timer thread to kill if needed
    timer = threading.Timer(timeout, proc.kill)
    try:
        timer.start()
        stdout, stderr = proc.communicate()
    finally:
        timer.cancel()

    return {
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }

def invoke_tool(request_json: str) -> str:
    """
    Entrypoint for calling a tool. Takes a JSON string, returns a JSON string:
    { "exit_code": int, "stdout": "...", "stderr": "..." }
    Steps:
      1. Parse & validate JSON → ToolRequest
      2. ACL check
      3. Find wrapper script
      4. Build command line
      5. Run under sandbox (if secure) or direct
      6. Return JSON response
    """
    try:
        # 1. Parse & validate
        payload = json.loads(request_json)
        tool_req = ToolRequest.model_validate(payload)
    except Exception as e:
        err = {"exit_code": -1, "stdout": "", "stderr": f"Invalid request: {e}"}
        return json.dumps(err)

    # 2. ACL check
    acl = get_acl()
    if not acl.is_allowed(tool_req.name):
        resp = {
            "exit_code": 1,
            "stdout": "",
            "stderr": f"Permission denied for tool '{tool_req.name}'",
        }
        return json.dumps(resp)

    # 3. Look for wrapper script under tools/
    wrapper_path = Path(__file__).parent.parent.parent / "tools" / f"{tool_req.name}.py"
    if not wrapper_path.exists():
        resp = {
            "exit_code": 1,
            "stdout": "",
            "stderr": f"Tool wrapper not found: '{tool_req.name}'",
        }
        return json.dumps(resp)

    # 4. Build the command line: we execute wrapper under python, passing args as JSON via stdin
    #    Example: python tools/read_file.py '{"path": "...", "start": 0, "end": 100}'
    args_json = json.dumps(tool_req.args)
    py_executable = sys.executable  # e.g., /usr/bin/python3.11
    cmd = f"{shlex.quote(py_executable)} {shlex.quote(str(wrapper_path))} {shlex.quote(args_json)}"

    # 5. Decide sandboxing
    result: Dict[str, Any]
    if tool_req.secure:
        if _find_firejail():
            result = _run_with_firejail(cmd, tool_req.timeout_seconds)
        else:
            result = _run_with_docker(cmd, tool_req.timeout_seconds)
    else:
        result = _run_subprocess(cmd, tool_req.timeout_seconds)

    # 6. Return JSON
    return json.dumps(result)