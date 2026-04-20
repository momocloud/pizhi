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
        if self.kind not in _VALID_AGENT_KINDS:
            raise ValueError(f"unknown agent kind: {self.kind!r}")
        if self.target_scope not in _VALID_TARGET_SCOPES:
            raise ValueError(f"unknown agent target scope: {self.target_scope!r}")
