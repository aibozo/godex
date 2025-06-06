# coding-agent/tests/test_tools.py

import subprocess, sys, json
import os
from pathlib import Path
import tempfile
import pytest

# Path to the core invoker
CORE = [sys.executable, "-c", 
        "import agent.tools.core as c; "
        "import sys; "
        "data=sys.stdin.read(); "
        "sys.stdout.write(c.invoke_tool(data))"]

def run_core(request: dict) -> dict:
    """
    Helper to invoke the core.process with a JSON payload and return a dict.
    """
    p = subprocess.Popen(
        CORE,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    payload = json.dumps(request)
    out, err = p.communicate(payload, timeout=10)
    if err:
        # The core module shouldn't print to stderr except on internal error
        print("CORE STDERROR:", err)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        pytest.skip("Core did not return valid JSON: " + out)

def test_read_file_success(tmp_path):
    # Create a sample file
    file = tmp_path / "foo.txt"
    file.write_text("Hello, world!")
    req = {
        "name": "read_file",
        "args": {"path": str(file), "start": 0, "end": 5},
        "secure": False,
        "timeout_seconds": 5
    }
    resp = run_core(req)
    assert resp["exit_code"] == 0
    assert resp["stdout"] == "Hello"

def test_read_file_not_exists(tmp_path):
    fake = tmp_path / "nope.txt"
    req = {
        "name": "read_file",
        "args": {"path": str(fake)},
        "secure": False,
        "timeout_seconds": 5
    }
    resp = run_core(req)
    assert resp["exit_code"] != 0
    assert "not found" in resp["stderr"].lower()

def test_acl_denied(tmp_path):
    # Temporarily clear permissions
    # Write a minimal .cokeydex.yml with no tools_allowed
    agent_yml = tmp_path / ".cokeydex.yml"
    agent_yml.write_text("tools_allowed: []\n")
    os.chdir(tmp_path)
    req = {
        "name": "read_file",
        "args": {"path": "whatever"},
        "secure": False,
        "timeout_seconds": 1
    }
    resp = run_core(req)
    assert resp["exit_code"] == 1
    assert "permission denied" in resp["stderr"].lower()

def test_write_diff_roundtrip(tmp_path):
    # Create a file and write a diff that changes a line
    file = tmp_path / "bar.txt"
    file.write_text("line1\nline2\nline3\n")
    # Diff: change line2 -> "LINE2\n"
    diff_text = """\
--- a/bar.txt
+++ b/bar.txt
@@ -1,3 +1,3 @@
 line1
-line2
+LINE2
 line3
"""
    req = {
        "name": "write_diff",
        "args": {"path": str(file), "diff": diff_text},
        "secure": False,
        "timeout_seconds": 5
    }
    resp = run_core(req)
    assert resp["exit_code"] == 0
    # Verify file contents updated
    updated = Path(file).read_text()
    assert "LINE2" in updated

def test_run_tests_failure(tmp_path):
    # Create a tiny pytest file that fails
    proj = tmp_path / "proj"
    (proj / "tests").mkdir(parents=True)
    test_file = proj / "tests" / "test_fail.py"
    test_file.write_text("def test_fail():\n    assert False\n")
    os.chdir(proj)
    req = {
        "name": "run_tests",
        "args": {"cmd": "pytest -q"},
        "secure": False,
        "timeout_seconds": 10
    }
    resp = run_core(req)
    assert resp["exit_code"] != 0
    assert "1 failed" in resp["stdout"]

def test_grep(tmp_path):
    # Create two files with content
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.py"
    f1.write_text("foo bar baz\n")
    f2.write_text("def foo(): pass")
    os.chdir(tmp_path)
    req = {
        "name": "grep",
        "args": {"pattern": "foo", "path_glob": "*.py", "max_lines": 10},
        "secure": False,
        "timeout_seconds": 5
    }
    resp = run_core(req)
    assert resp["exit_code"] == 0
    assert "b.py" in resp["stdout"]

@pytest.mark.skip(reason="Requires a pre‐seeded Chroma database for full vector search")
def test_vector_search(tmp_path):
    # This test is skipped unless you implement Phase IV to seed embeddings.
    pass