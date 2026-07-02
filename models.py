from pydantic import BaseModel
from typing import Literal


class Change(BaseModel):
    old_str: str
    new_str: str
    why: str


class FileChange(BaseModel):
    path: str
    action: Literal["modify", "create"]
    why: str
    changes: list[Change]


class Risk(BaseModel):
    risk: str
    severity: Literal["Low", "Medium", "High"]
    mitigation: str


class Plan(BaseModel):
    summary: str
    execution_order_reasoning: str
    files: list[FileChange]
    risks: list[Risk]
    verification_steps: list[str]