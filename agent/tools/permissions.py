# coding-agent/agent/tools/permissions.py

from pathlib import Path
import yaml
from typing import Set
from agent.config import get_settings, Settings

class ACL:
    """
    Loads the 'tools_allowed' list from .cokeydex.yml (via Settings).
    Offers a method to check if a given tool name is allowed.
    """
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._allowed: Set[str] = set()
        self._load_acl()

    def _load_acl(self):
        # Read tools_allowed from the same source as Settings
        config_path = Path(self.settings.agent_home) / ".cokeydex.yml"
        try:
            raw = yaml.safe_load(config_path.read_text())
        except Exception:
            raw = {}
        allowed_list = raw.get("tools_allowed", [])
        if not isinstance(allowed_list, list):
            raise ValueError("`tools_allowed` in .cokeydex.yml must be a list of strings")
        self._allowed = set(str(x) for x in allowed_list)

    def is_allowed(self, tool_name: str) -> bool:
        return tool_name in self._allowed

    def reload(self):
        self._load_acl()