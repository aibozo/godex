#!/usr/bin/env python3
# coding-agent/tools/static_analyze.py

import sys
import json
import subprocess

def main():
    if len(sys.argv) != 2:
        msg = {"exit_code": 1, "stdout": "", "stderr": "Expected JSON arg"}
        print(json.dumps(msg)); sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
        # Default to running ruff on the entire repo
        cmd = args.get("cmd", "ruff .")
        if not isinstance(cmd, str):
            raise ValueError("'cmd' must be a string")
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