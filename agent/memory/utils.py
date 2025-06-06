# coding-agent/agent/memory/utils.py

import os
from pathlib import Path
from typing import Tuple

def estimate_tokens(text: str) -> int:
    """
    Roughly estimate tokens in a text by counting characters.
    Assumption: ~4 characters per token on average. 
    """
    num_chars = len(text)
    return (num_chars + 3) // 4  # ceil

def atomic_write(path: Path, content: str) -> None:
    """
    Write content to `path` atomically: write to a temp file, then rename.
    Prevents corruption if interrupted.
    """
    path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.replace(tmp, path)

def read_file(path: Path) -> str:
    """
    Simple read with error handling.
    """
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

def append_file(path: Path, content: str) -> None:
    """
    Append `content` to file at `path`, creating directories as needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(content)