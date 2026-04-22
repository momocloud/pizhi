from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


REPORT_DATE = "2026-04-22"


@dataclass(frozen=True, slots=True)
class StageConfig:
    slug: str
    target_chapters: int
    report_path: Path


_STAGE_CONFIGS = {
    "stage1": {
        "target_chapters": 3,
        "report_name": f"{REPORT_DATE}-e2e-stage-1-smoke.md",
    },
    "stage2": {
        "target_chapters": 10,
        "report_name": f"{REPORT_DATE}-e2e-stage-2-endurance.md",
    },
    "stage3": {
        "target_chapters": 30,
        "report_name": f"{REPORT_DATE}-e2e-stage-3-full-run.md",
    },
}


def build_validation_root_name(timestamp: str) -> str:
    sanitized_timestamp = re.sub(r"[^0-9A-Za-z]+", "-", timestamp).strip("-")
    return f"pizhi-e2e-claude-opencode-{sanitized_timestamp}"


def build_validation_root_path(timestamp: str, base_dir: Path | None = None) -> Path:
    root_dir = Path("tmp") if base_dir is None else Path(base_dir)
    return root_dir / build_validation_root_name(timestamp)


def build_stage_report_path(stage_slug: str, docs_dir: Path | None = None) -> Path:
    docs_root = Path("docs") / "verification" if docs_dir is None else Path(docs_dir)
    return docs_root / _stage_config(stage_slug)["report_name"]


def build_stage_config(stage_slug: str, docs_dir: Path | None = None) -> StageConfig:
    stage = _stage_config(stage_slug)
    return StageConfig(
        slug=stage_slug,
        target_chapters=stage["target_chapters"],
        report_path=build_stage_report_path(stage_slug, docs_dir=docs_dir),
    )


def _stage_config(stage_slug: str) -> dict[str, object]:
    try:
        return _STAGE_CONFIGS[stage_slug]
    except KeyError as exc:
        raise ValueError(f"unknown stage slug: {stage_slug}") from exc
