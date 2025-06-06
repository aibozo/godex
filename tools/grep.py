#!/usr/bin/env python3
# coding-agent/tools/grep.py

import sys
import json
import subprocess
import shlex

def main():
    if len(sys.argv) != 2:
        msg = {"exit_code": 1, "stdout": "", "stderr": "Expected JSON arg"}
        print(json.dumps(msg)); sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
        pattern = args.get("pattern")
        path_glob = args.get("path_glob", ".")
        max_lines = int(args.get("max_lines", 100))

        if not pattern:
            raise ValueError("Missing 'pattern'")
        # Construct grep command. -R: recursive, -n: show line numbers, -m max matches
        cmd = (
            f"grep -R -n -m {max_lines} --include='{path_glob}' "
            f"{shlex.quote(pattern)} ."
        )
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