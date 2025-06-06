from __future__ import annotations
import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, FilePath
import yaml

class Settings(BaseSettings):
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    cost_cap_daily: float = 20.0
    memory_summarise_threshold: int = 4000  # tokens
    model_router_default: str = "gpt-4o-mini"
    agent_home: Path = Field(Path.cwd(), env="AGENT_HOME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def _load_yaml(path: Path | None):
    if path and path.exists():
        with open(path, "r") as fh:
            return yaml.safe_load(fh) or {}
    return {}

@lru_cache
def get_settings(config_path: Path | None = None) -> Settings:
    file_vals = _load_yaml(config_path or Path(".cokeydex.yml"))
    return Settings(**file_vals)