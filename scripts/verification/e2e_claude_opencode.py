from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from string import Template


@dataclass(frozen=True, slots=True)
class StageConfig:
    slug: str
    target_chapters: int
    report_path: Path


_STAGE_CONFIGS = {
    "stage1": {
        "target_chapters": 3,
        "report_stem": "e2e-stage-1-smoke.md",
    },
    "stage2": {
        "target_chapters": 10,
        "report_stem": "e2e-stage-2-endurance.md",
    },
    "stage3": {
        "target_chapters": 30,
        "report_stem": "e2e-stage-3-full-run.md",
    },
}

_CLAUDE_STAGE_PROMPT_TEMPLATE_PATH = Path(__file__).with_name("templates") / "claude_stage_prompt.md"


def build_validation_root_name(timestamp: str) -> str:
    sanitized_timestamp = re.sub(r"[^0-9A-Za-z]+", "-", timestamp).strip("-")
    return f"pizhi-e2e-claude-opencode-{sanitized_timestamp}"


def build_validation_root_path(timestamp: str, base_dir: Path | None = None) -> Path:
    root_dir = Path("tmp") if base_dir is None else Path(base_dir)
    return root_dir / build_validation_root_name(timestamp)


def build_stage_report_path(
    stage_slug: str,
    report_date: str,
    docs_dir: Path | None = None,
) -> Path:
    docs_root = Path("docs") / "verification" if docs_dir is None else Path(docs_dir)
    return docs_root / f"{report_date}-{_stage_config(stage_slug)['report_stem']}"


def build_stage_config(
    stage_slug: str,
    report_date: str,
    docs_dir: Path | None = None,
) -> StageConfig:
    stage = _stage_config(stage_slug)
    return StageConfig(
        slug=stage_slug,
        target_chapters=stage["target_chapters"],
        report_path=build_stage_report_path(
            stage_slug,
            report_date=report_date,
            docs_dir=docs_dir,
        ),
    )


def render_claude_stage_prompt(
    *,
    stage_slug: str,
    project_root: str | Path,
    repo_root: str | Path,
    target_chapters: int,
    genre: str,
) -> str:
    template = Template(_load_claude_stage_prompt_template())
    return template.substitute(
        stage_slug=stage_slug,
        project_root=Path(project_root).as_posix(),
        repo_root=Path(repo_root).as_posix(),
        target_chapters=target_chapters,
        genre=genre,
    )


def collect_stage_artifacts(project_root: str | Path) -> dict[str, list[str]]:
    root = Path(project_root).resolve()
    cache_root = root / ".pizhi" / "cache"
    return {
        "runs": _collect_artifact_entries(cache_root / "runs"),
        "sessions": _collect_artifact_entries(cache_root / "continue_sessions"),
        "checkpoints": _collect_artifact_entries(cache_root / "checkpoints"),
        "reports": _collect_artifact_entries(cache_root, filename="review_full.md"),
        "manuscript": _collect_artifact_entries(root / "manuscript"),
    }


def _load_claude_stage_prompt_template() -> str:
    try:
        return _CLAUDE_STAGE_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"unable to load Claude stage prompt template at {_CLAUDE_STAGE_PROMPT_TEMPLATE_PATH}"
        ) from exc


def _collect_artifact_entries(directory: Path, filename: str | None = None) -> list[str]:
    if filename is not None:
        path = directory / filename
        return [path.resolve().as_posix()] if path.exists() else []
    if not directory.exists():
        return []
    entries: list[str] = []
    for path in sorted(directory.iterdir(), key=lambda candidate: candidate.name):
        entries.append(path.resolve().as_posix())
    return entries


def _stage_config(stage_slug: str) -> dict[str, object]:
    try:
        return _STAGE_CONFIGS[stage_slug]
    except KeyError as exc:
        raise ValueError(f"unknown stage slug: {stage_slug}") from exc
