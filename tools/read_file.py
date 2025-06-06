#!/usr/bin/env python3
# coding-agent/tools/read_file.py

import sys
import json
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        err = {"exit_code": 1, "stdout": "", "stderr": "Expected exactly one JSON arg"}
        print(json.dumps(err))
        sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
        path = args.get("path")
        start = int(args.get("start", 0))
        end = int(args.get("end", -1))
        if not path:
            raise ValueError("Missing 'path'")
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        data = p.read_text(encoding="utf-8")
        # Clip to [start:end]
        content = data[start:end] if end != -1 else data[start:]
        resp = {"exit_code": 0, "stdout": content, "stderr": ""}
    except Exception as e:
        resp = {"exit_code": 1, "stdout": "", "stderr": str(e)}

    print(json.dumps(resp))
    sys.exit(resp["exit_code"])

if __name__ == "__main__":
    main()