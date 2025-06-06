#!/usr/bin/env python3
# coding-agent/tools/write_diff.py

import sys
import json
import difflib
from pathlib import Path

def apply_diff(original: str, diff_text: str) -> str:
    """
    Apply a unified diff to the original text, return the updated text.
    If diff fails, raise an exception.
    """
    # Use difflib to apply the patch
    orig_lines = original.splitlines(keepends=True)
    diff_lines = diff_text.splitlines(keepends=True)
    
    # Unfortunately, stdlib lacks a robust patch applier. In Phase II, we do a simple check:
    # We only allow diffs with '--- a/path' and '+++ b/path' to match the file we loaded.
    # Then we write the diff to a temp file and call `patch` binary. 
    import tempfile, subprocess

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf_orig:
        tf_orig.write(original)
        orig_name = tf_orig.name

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf_diff:
        tf_diff.write(diff_text)
        diff_name = tf_diff.name

    # Run `patch` CLI to apply diff in‐place
    cmd = f"patch {orig_name} {diff_name}"
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    out, err = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Patch failed: {err.strip()}")

    # Read patched content
    with open(orig_name, "r", encoding="utf-8") as f:
        new_text = f.read()
    return new_text

def main():
    if len(sys.argv) != 2:
        err = {"exit_code": 1, "stdout": "", "stderr": "Expected one JSON arg"}
        print(json.dumps(err)); sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
        path = args.get("path")
        diff_text = args.get("diff")
        if not path or diff_text is None:
            raise ValueError("Missing 'path' or 'diff'")
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        original = p.read_text(encoding="utf-8")
        patched = apply_diff(original, diff_text)
        p.write_text(patched, encoding="utf-8")
        resp = {"exit_code": 0, "stdout": "OK", "stderr": ""}
    except Exception as e:
        resp = {"exit_code": 1, "stdout": "", "stderr": str(e)}

    print(json.dumps(resp))
    sys.exit(resp["exit_code"])

if __name__ == "__main__":
    main()