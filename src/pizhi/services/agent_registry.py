from __future__ import annotations

from collections.abc import Iterable

from pizhi.domain.agent_extensions import AgentKind
from pizhi.domain.agent_extensions import AgentSpec
from pizhi.domain.agent_extensions import AgentTargetScope


class AgentRegistry:
    def __init__(self, specs: Iterable[AgentSpec]):
        self._specs = list(specs)

    def iter_enabled(
        self,
        *,
        kind: AgentKind,
        target_scope: AgentTargetScope,
    ) -> list[AgentSpec]:
        return [
            spec
            for spec in self._specs
            if spec.enabled and spec.kind == kind and spec.target_scope == target_scope
        ]
