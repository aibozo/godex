# coding-agent/agent/retrieval/chunker.py

import re
from pathlib import Path
from typing import List, Dict, Any

from agent.config import get_settings
from agent.memory.utils import estimate_tokens

# --------------------------------------------------------------------------------
# Regular expressions for detecting function/class boundaries.
# For simplicity, we cover common languages: Python, JavaScript, TypeScript.
# --------------------------------------------------------------------------------

PY_FUNC_RE = re.compile(r"^\s*def\s+\w+\s*\(")
PY_CLASS_RE = re.compile(r"^\s*class\s+\w+\s*(\(|:)")
JS_FUNC_RE = re.compile(r"^\s*(export\s+)?function\s+\w+\s*\(")
JS_ARROW_RE = re.compile(r"^\s*(const|let|var)\s+\w+\s*=\s*\(.*\)\s*=>")
JS_CLASS_RE = re.compile(r"^\s*(export\s+)?class\s+\w+\s*{")

# Combine all patterns
BOUNDARY_PATTERNS = [PY_FUNC_RE, PY_CLASS_RE, JS_FUNC_RE, JS_ARROW_RE, JS_CLASS_RE]


def is_boundary(line: str) -> bool:
    """
    Return True if `line` matches any known function/class definition pattern.
    """
    for pat in BOUNDARY_PATTERNS:
        if pat.match(line):
            return True
    return False


def chunk_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Chunk the file at `file_path` into ≤ max_tokens chunks with overlap.
    Returns a list of dicts: {
      "file_path": str (relative),
      "start_line": int,
      "end_line": int,
      "text": str
    }
    """
    settings = get_settings()
    max_toks = settings.retrieval["chunker"]["max_tokens"]
    overlap = settings.retrieval["chunker"]["overlap_tokens"]

    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    chunks: List[Dict[str, Any]] = []
    n = len(lines)
    idx = 0  # current line index (0-based)

    while idx < n:
        start_line = idx
        tok_count = 0
        chunk_lines = []

        # Expand chunk until near max_toks or EOF
        while idx < n:
            line = lines[idx]
            line_toks = estimate_tokens(line)
            if tok_count + line_toks > max_toks:
                break
            chunk_lines.append(line)
            tok_count += line_toks
            idx += 1

            # If many lines and we found a boundary recently, we could cut earlier.
            # For simplicity, we cut exactly when tokens exceed—or at EOF.

        # If token limit exceeded immediately (single line > max_toks), force include single line
        if not chunk_lines or tok_count > max_toks:
            # Take at least one line
            chunk_lines = [lines[start_line]]
            tok_count = estimate_tokens(lines[start_line])
            idx = start_line + 1

        end_line = idx  # exclusive index
        # Now adjust for overlap: next chunk should start at max(start_line + len(chunk_lines) - overlap_lines, end_line)
        # We need to count how many lines approximate to `overlap` tokens, scanning backward
        overlap_count = 0
        tok_acc = 0
        j = len(chunk_lines) - 1
        while j >= 0 and tok_acc < overlap:
            tok_acc += estimate_tokens(chunk_lines[j])
            overlap_count += 1
            j -= 1

        next_start = max(start_line + len(chunk_lines) - overlap_count, end_line - overlap_count)
        if next_start < idx:
            next_start = idx - overlap_count
        # But ensure next_start > start_line
        next_start = max(next_start, start_line + len(chunk_lines))

        # Save the chunk
        chunk_text = "".join(chunk_lines)
        try:
            rel_path = str(file_path.relative_to(Path(get_settings().agent_home)))
        except ValueError:
            # If file is not under agent_home, use absolute path
            rel_path = str(file_path)
        chunks.append({
            "file_path": rel_path,
            "start_line": start_line + 1,  # convert to 1-based
            "end_line": end_line,          # exclusive → inclusive = end_line
            "text": chunk_text
        })

        # Move idx back by overlap_count to create overlap
        idx = max(end_line - overlap_count, start_line + 1)
        
        # Ensure we always make progress
        if idx <= start_line:
            idx = start_line + 1

    return chunks