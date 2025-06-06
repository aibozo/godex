# coding-agent/agent/tools/schema.py

from typing import Literal, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, StrictStr, StrictBool, StrictInt

class ToolRequest(BaseModel):
    """
    Represents a fully‐validated request to invoke a tool.
    """
    name: StrictStr = Field(..., description="Tool name, must match registered tool.")
    args: Dict[StrictStr, Any] = Field(
        default_factory=dict, description="Arguments to the tool (key: value)."
    )
    secure: StrictBool = Field(
        True, description="Whether to run this tool inside the sandbox."
    )
    timeout_seconds: StrictInt = Field(
        30,
        ge=1,
        le=300,
        description="Wall‐clock timeout in seconds for this tool call.",
    )

    @field_validator("name")
    def name_must_be_safe(cls, v: str) -> str:
        # Only allow [a-zA-Z0-9_-]
        import re
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", v):
            raise ValueError("Tool name contains invalid characters")
        return v

    @field_validator("args")
    def args_must_be_json_serializable(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        # We'll rely on natural JSON types; deep validation is in each wrapper
        return v