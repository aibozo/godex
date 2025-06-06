from __future__ import annotations
import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, FilePath
from typing import List, Dict, Any
import yaml

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Allow extra fields from config files
    )
    
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")
    cost_cap_daily: float = 20.0
    memory_summarise_threshold: int = 4000  # tokens
    model_router_default: str = "gpt-4o-mini"
    executor_model: str = Field(default="")  # Specific model for executor
    planner_model: str = Field(default="")  # Specific model for planner
    reflexion_model: str = Field(default="")  # Specific model for reflexion
    gemini_thinking_mode: bool = Field(default=False)  # Enable thinking mode for Gemini
    agent_home: Path = Field(default_factory=Path.cwd)
    tools_allowed: List[str] = Field(default_factory=lambda: [
        "read_file", "write_diff", "run_tests", "static_analyze", "grep", "vector_search"
    ])
    
    # Retrieval configuration
    retrieval: Dict[str, Any] = Field(default_factory=lambda: {
        "bm25": {
            "index_dir": "bm25_index",
            "ngram_range": [1, 1],
            "max_features": 50000
        },
        "chunker": {
            "max_tokens": 400,
            "overlap_tokens": 50
        },
        "embeddings": {
            "collection_name": "codebase",
            "model": "text-embedding-3-small"
        }
    })
    
    # Executor-specific settings
    max_tool_calls_per_task: int = Field(
        30, description="Hard limit of tool calls (Thought-Tool-Observation) per task"
    )
    max_reflexion_retries: int = Field(
        3, description="Number of reflexion+retry loops before marking task as failed"
    )
    consecutive_failure_threshold: int = Field(
        5, description="Number of consecutive failing diffs (or test failures) to trigger rollback"
    )
    test_command: str = Field(
        "pytest -q", description="Default command to run project tests"
    )
    lint_command: str = Field(
        "ruff .", description="Default command to run static analysis"
    )

def _load_yaml(path: Path | None):
    if path and path.exists():
        with open(path, "r") as fh:
            return yaml.safe_load(fh) or {}
    return {}

@lru_cache
def get_settings(config_path: Path | None = None) -> Settings:
    file_vals = _load_yaml(config_path or Path(".cokeydex.yml"))
    return Settings(**file_vals)