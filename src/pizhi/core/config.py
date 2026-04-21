from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from pizhi.domain.agent_extensions import AgentSpec


@dataclass(slots=True)
class ProjectSection:
    name: str
    genre: str
    pov: str
    created: str
    last_updated: str


@dataclass(slots=True)
class ChaptersSection:
    total_planned: int
    per_volume: int


@dataclass(slots=True)
class ContextWindowSection:
    prev_chapters: int
    max_outline_words: int
    max_chapter_words: int


@dataclass(slots=True)
class StyleSection:
    tone: str
    dialogue_ratio: float


@dataclass(slots=True)
class GenerationSection:
    context_window: ContextWindowSection
    style: StyleSection


@dataclass(slots=True)
class ConsistencySection:
    auto_check: bool
    checkpoint_interval: int


@dataclass(slots=True)
class ForeshadowingSection:
    auto_archive_resolved: bool
    reminder_threshold: int


@dataclass(slots=True)
class ProviderSection:
    provider: str
    model: str
    base_url: str
    api_key_env: str
    brainstorm_model: str | None = None
    outline_model: str | None = None
    write_model: str | None = None
    continue_model: str | None = None
    review_model: str | None = None
    review_base_url: str | None = None
    review_api_key_env: str | None = None

    def resolve_review_config(self) -> ProviderSection:
        return ProviderSection(
            provider=self.provider,
            model=self.review_model or self.model,
            base_url=self.review_base_url or self.base_url,
            api_key_env=self.review_api_key_env or self.api_key_env,
        )

    def resolve_route_config(self, route_name: str) -> ProviderSection:
        if route_name == "review":
            return self.resolve_review_config()

        route_model = {
            "brainstorm": self.brainstorm_model,
            "outline": self.outline_model,
            "write": self.write_model,
            "continue": self.continue_model,
        }.get(route_name)

        return ProviderSection(
            provider=self.provider,
            model=route_model or self.model,
            base_url=self.base_url,
            api_key_env=self.api_key_env,
            brainstorm_model=self.brainstorm_model,
            outline_model=self.outline_model,
            write_model=self.write_model,
            continue_model=self.continue_model,
            review_model=self.review_model,
            review_base_url=self.review_base_url,
            review_api_key_env=self.review_api_key_env,
        )


@dataclass(slots=True)
class AgentBackendSection:
    agent_backend: str
    agent_command: str
    agent_args: list[str]

    def __post_init__(self) -> None:
        self.agent_args = list(self.agent_args)


@dataclass(slots=True)
class ExecutionConfig:
    backend: str = "provider"
    provider: ProviderSection | None = None
    agent: AgentBackendSection | None = None


@dataclass(slots=True)
class ProjectConfig:
    project: ProjectSection
    chapters: ChaptersSection
    generation: GenerationSection
    consistency: ConsistencySection
    foreshadowing: ForeshadowingSection
    execution: ExecutionConfig
    agents: list[AgentSpec] | None = None

    @property
    def provider(self) -> ProviderSection | None:
        return self.execution.provider

    @provider.setter
    def provider(self, value: ProviderSection | None) -> None:
        self.execution.backend = "provider"
        self.execution.provider = value


def default_config(
    name: str,
    genre: str = "",
    total_chapters: int = 0,
    per_volume: int = 20,
    pov: str = "",
    tone: str = "",
    dialogue_ratio: float = 0.35,
) -> ProjectConfig:
    today = date.today().isoformat()
    return ProjectConfig(
        project=ProjectSection(
            name=name,
            genre=genre,
            pov=pov,
            created=today,
            last_updated=today,
        ),
        chapters=ChaptersSection(
            total_planned=total_chapters,
            per_volume=per_volume,
        ),
        generation=GenerationSection(
            context_window=ContextWindowSection(
                prev_chapters=2,
                max_outline_words=500,
                max_chapter_words=5000,
            ),
            style=StyleSection(
                tone=tone,
                dialogue_ratio=dialogue_ratio,
            ),
        ),
        consistency=ConsistencySection(
            auto_check=True,
            checkpoint_interval=3,
        ),
        foreshadowing=ForeshadowingSection(
            auto_archive_resolved=True,
            reminder_threshold=5,
        ),
        execution=ExecutionConfig(),
    )


def save_config(path: Path, config: ProjectConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _validate_unique_agent_ids(config.agents)
    payload = asdict(config)
    execution_payload = payload.get("execution")
    if execution_payload is not None:
        if config.execution.provider is None:
            execution_payload.pop("provider", None)
        if config.execution.agent is None:
            execution_payload.pop("agent", None)
        if not execution_payload.get("provider") and not execution_payload.get("agent"):
            payload.pop("execution", None)
    if config.agents is None:
        payload.pop("agents", None)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)


def load_config(path: Path) -> ProjectConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return _config_from_dict(raw)


def _config_from_dict(data: dict[str, Any]) -> ProjectConfig:
    project = data["project"]
    chapters = data["chapters"]
    generation = data["generation"]
    context_window = generation["context_window"]
    style = generation["style"]
    consistency = data["consistency"]
    foreshadowing = data["foreshadowing"]
    execution = data.get("execution")
    provider = data.get("provider")
    raw_agents = data.get("agents")

    return ProjectConfig(
        project=ProjectSection(**project),
        chapters=ChaptersSection(**chapters),
        generation=GenerationSection(
            context_window=ContextWindowSection(**context_window),
            style=StyleSection(**style),
        ),
        consistency=ConsistencySection(**consistency),
        foreshadowing=ForeshadowingSection(**foreshadowing),
        execution=_execution_config_from_raw(execution, provider),
        agents=_agent_specs_from_raw(raw_agents),
    )


def _execution_config_from_raw(
    raw_execution: Any,
    raw_provider: Any,
) -> ExecutionConfig:
    if raw_execution is not None:
        if not isinstance(raw_execution, dict):
            raise ValueError("execution must be a mapping")
        provider = raw_execution.get("provider")
        agent = raw_execution.get("agent")
        return ExecutionConfig(
            backend=raw_execution.get("backend", "provider"),
            provider=ProviderSection(**provider) if provider else None,
            agent=AgentBackendSection(**agent) if agent else None,
        )

    if raw_provider is not None:
        return ExecutionConfig(
            backend="provider",
            provider=ProviderSection(**raw_provider),
            agent=None,
        )

    return ExecutionConfig()


def _agent_specs_from_raw(raw_agents: Any) -> list[AgentSpec] | None:
    if raw_agents is None:
        return None
    if not isinstance(raw_agents, list):
        raise ValueError("agents must be a list")

    specs: list[AgentSpec] = []
    seen_agent_ids: set[str] = set()
    for raw_spec in raw_agents:
        if not isinstance(raw_spec, dict):
            raise ValueError("agents must contain mappings")
        spec = AgentSpec(**raw_spec)
        if spec.agent_id in seen_agent_ids:
            raise ValueError(f"duplicate agent_id: {spec.agent_id}")
        seen_agent_ids.add(spec.agent_id)
        specs.append(spec)

    return specs


def _validate_unique_agent_ids(specs: list[AgentSpec] | None) -> None:
    if specs is None:
        return

    seen_agent_ids: set[str] = set()
    for spec in specs:
        if spec.agent_id in seen_agent_ids:
            raise ValueError(f"duplicate agent_id: {spec.agent_id}")
        seen_agent_ids.add(spec.agent_id)
