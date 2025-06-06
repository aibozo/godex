#!/usr/bin/env python3
# coding-agent/tools/run_tests.py

import sys
import json
import subprocess

def main():
    if len(sys.argv) != 2:
        msg = {"exit_code": 1, "stdout": "", "stderr": "Expected JSON arg"}
        print(json.dumps(msg)); sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
        cmd = args.get("cmd", "pytest -q")
        if not isinstance(cmd, str):
            raise ValueError("'cmd' must be a string")
        # Run tests
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        out, err = proc.communicate()
        resp = {
            "exit_code": proc.returncode,
            "stdout": out,
            "stderr": err,
        }
    except Exception as e:
        resp = {"exit_code": 1, "stdout": "", "stderr": str(e)}

    print(json.dumps(resp))
    sys.exit(resp["exit_code"])

if __name__ == "__main__":
    main()