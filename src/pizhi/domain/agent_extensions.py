from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class AgentSpec:
    agent_id: str
    kind: Literal["review", "maintenance"]
    description: str
    enabled: bool
    target_scope: Literal["chapter", "project"]
    prompt_template: str
