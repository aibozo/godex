# coding-agent/agent/memory/summarizer.py

import datetime
from typing import Tuple, Optional
from pathlib import Path
import openai
from agent.config import get_settings
from agent.memory.utils import read_file, atomic_write

# --------------------------------------------------------------------------------
# PROMPT TEMPLATE: instruct GPT-4 nano to summarize a Markdown scratchpad.
# We use a "system + user" style for clarity, though a single‐message prompt also works.
# --------------------------------------------------------------------------------

_SUMMARY_PREFIX = """You are an expert agent responsible for compressing a project's scratchpad notes into a concise summary.
You must:
- Keep any lines beginning with '- [ ]' (unchecked task) or '*TODO*:' exactly as is (do not rephrase).
- Summarize the rest of the Markdown in a way that captures all key facts, decisions, and context, in no more than 400 tokens.
- Output must be valid Markdown: use headings, bullet points, and paragraphs as needed, but preserve unchecked tasks verbatim.
Example of preserving tasks:
  - [ ] Refactor payment module
  *TODO*: Update README with new instructions

Begin summarizing below. Do not output any extra commentary—only the summary Markdown.
---
"""

# --------------------------------------------------------------------------------
# SELECT MODEL: GPT-4 nano (lowest‐cost, 8k window). Using OpenAI API.
# Alternatives: Claude‐4‐nano if anthropic_api_key provided.
# --------------------------------------------------------------------------------

def _choose_model() -> str:
    settings = get_settings()
    # If Anthropic key exists and we prefer Claude, switch here. Default: GPT-4‐nano.
    if settings.anthropic_api_key:
        return "claude-3-haiku-20240307"  # Using actual Claude model name
    return "gpt-4o-mini"  # OpenAI's small/fast model

# --------------------------------------------------------------------------------
# Public function to summarize a scratchpad.
# Input: path to MD file under memory/scratch/
# Output: tuple(new_summary_text, archive_filename)
# --------------------------------------------------------------------------------

def summarize_scratchpad(scratch_path: Path) -> Tuple[str, Optional[Path]]:
    """
    Summarize the given scratchpad Markdown file, write the summary to archive, and return:
      (summary_markdown, archive_path)
    The caller is responsible for truncating the original scratchpad.
    """
    settings = get_settings()
    text = read_file(scratch_path)
    if not text.strip():
        # Nothing to summarize
        return "", None

    model = _choose_model()
    prompt = _SUMMARY_PREFIX + text

    # Call OpenAI (or Anthropic) API
    try:
        if settings.anthropic_api_key and model.startswith("claude"):
            # Example stub: replace with actual Anthropic API call
            summary = _call_anthropic(model, prompt, settings.anthropic_api_key)
        else:
            # Using new OpenAI client interface
            client = openai.OpenAI(api_key=settings.openai_api_key)
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,  # Allow reasonable summary length
                temperature=0.2,
            )
            summary = completion.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Summarization failed: {e}")

    # Write summary to archive
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    archive_fn = scratch_path.stem + f"_summary_{timestamp}.md"
    archive_path = scratch_path.parent.parent / "archive" / archive_fn
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(archive_path, summary)

    return summary, archive_path

# --------------------------------------------------------------------------------
# Helper for Anthropic (stub implementation)
# --------------------------------------------------------------------------------

def _call_anthropic(model: str, prompt: str, api_key: str) -> str:
    """
    Example function showing how you might call Anthropic's API.
    Replace with actual Claude API client usage.
    """
    # from anthropic import Anthropic
    # client = Anthropic(api_key=api_key)
    # response = client.messages.create(
    #     model=model,
    #     messages=[{"role": "user", "content": prompt}],
    #     max_tokens=400,
    #     temperature=0.2,
    # )
    # return response.content[0].text
    raise NotImplementedError("Anthropic summarization not wired.")