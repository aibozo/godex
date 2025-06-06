# coding-agent/agent/tasks/schema.py

from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re


class Budget(BaseModel):
    tokens: Optional[int] = Field(
        None, description="Maximum number of tokens this task may consume"
    )
    dollars: Optional[float] = Field(
        None, description="Maximum dollars allowed for API calls for this task"
    )
    seconds: Optional[int] = Field(
        None, description="Approximate wall‐clock time estimate in seconds"
    )

    @model_validator(mode='after')
    def at_least_one_specified(self):
        if self.tokens is None and self.dollars is None and self.seconds is None:
            raise ValueError("At least one budget field ('tokens', 'dollars', or 'seconds') must be specified")
        return self


class Task(BaseModel):
    """
    Represents a single task in a plan.
    """
    id: str = Field(..., description="Unique task identifier e.g. 'T-101'")
    description: str = Field(..., description="Short human‐readable description")
    accept_tests: List[str] = Field(
        ..., description="List of shell commands or pytest invocations to verify task completion"
    )
    budget: Budget = Field(..., description="Resource budget for this task")
    owner: Literal["agent", "human"] = Field("agent", description="Who should execute this task")
    status: Optional[Literal["pending", "in_progress", "done", "failed"]] = Field(
        "pending", description="Current status of task"
    )

    @field_validator("id")
    @classmethod
    def id_format(cls, v: str) -> str:
        if not re.fullmatch(r"T-\d+", v):
            raise ValueError("Task id must match pattern 'T-<number>' (e.g., T-101)")
        return v

    @field_validator("accept_tests")
    @classmethod
    def non_empty_test(cls, v: List[str]) -> List[str]:
        for item in v:
            if not item or not isinstance(item, str) or not item.strip():
                raise ValueError("Each 'accept_tests' entry must be a non-empty string")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "T-101",
                "description": "Implement OAuth login flow",
                "accept_tests": ["pytest tests/auth_integration.py"],
                "budget": {"tokens": 2000, "dollars": 0.05},
                "owner": "agent",
                "status": "pending"
            }
        }
    }


class Plan(BaseModel):
    """
    Wraps a list of Task objects.
    """
    tasks: List[Task]

    @model_validator(mode='after')
    def unique_ids(self):
        ids = [t.id for t in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("All task ids must be unique within a plan")
        return self