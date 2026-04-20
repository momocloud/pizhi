from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AgentKind = Literal["review", "maintenance"]
AgentTargetScope = Literal["chapter", "project"]
_VALID_AGENT_KINDS = {"review", "maintenance"}
_VALID_TARGET_SCOPES = {"chapter", "project"}


@dataclass(slots=True)
class AgentSpec:
    agent_id: str
    kind: AgentKind
    description: str
    enabled: bool
    target_scope: AgentTargetScope
    prompt_template: str

    def __post_init__(self) -> None:
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        if not isinstance(self.kind, str):
            raise ValueError("kind must be a string")
        if self.kind not in _VALID_AGENT_KINDS:
            raise ValueError(f"unknown agent kind: {self.kind!r}")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("description must be a non-empty string")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        if not isinstance(self.target_scope, str):
            raise ValueError("target_scope must be a string")
        if self.target_scope not in _VALID_TARGET_SCOPES:
            raise ValueError(f"unknown agent target scope: {self.target_scope!r}")
        if not isinstance(self.prompt_template, str) or not self.prompt_template.strip():
            raise ValueError("prompt_template must be a non-empty string")
