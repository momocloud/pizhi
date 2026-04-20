import pytest

from pizhi.domain.agent_extensions import AgentSpec
from pizhi.services.agent_registry import AgentRegistry


def test_agent_registry_filters_enabled_agents_by_kind_and_scope():
    registry = AgentRegistry(
        [
            AgentSpec(
                agent_id="critique.chapter",
                kind="review",
                description="chapter critique agent",
                enabled=True,
                target_scope="chapter",
                prompt_template="Review the chapter for pacing drift.",
            ),
            AgentSpec(
                agent_id="critique.disabled",
                kind="review",
                description="disabled chapter critique agent",
                enabled=False,
                target_scope="chapter",
                prompt_template="Review the chapter for pacing drift.",
            ),
            AgentSpec(
                agent_id="archive.audit",
                kind="maintenance",
                description="archive audit agent",
                enabled=True,
                target_scope="project",
                prompt_template="Audit the maintenance summary for missed archive work.",
            ),
        ]
    )

    chapter_review_agents = registry.iter_enabled(kind="review", target_scope="chapter")

    assert [agent.agent_id for agent in chapter_review_agents] == ["critique.chapter"]


def test_agent_spec_rejects_invalid_kind_and_target_scope():
    with pytest.raises(ValueError, match="unknown agent kind"):
        AgentSpec(
            agent_id="bad.kind",
            kind="unknown",  # type: ignore[arg-type]
            description="invalid",
            enabled=True,
            target_scope="chapter",
            prompt_template="noop",
        )

    with pytest.raises(ValueError, match="unknown agent target scope"):
        AgentSpec(
            agent_id="bad.scope",
            kind="review",
            description="invalid",
            enabled=True,
            target_scope="anywhere",  # type: ignore[arg-type]
            prompt_template="noop",
        )
