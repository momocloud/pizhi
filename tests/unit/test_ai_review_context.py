from __future__ import annotations

from pathlib import Path

from pizhi.core.paths import project_paths
from pizhi.services.ai_review_context import build_chapter_ai_review_context
from pizhi.services.ai_review_context import build_full_ai_review_context
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.consistency.structural import run_structural_review
from pizhi.services.consistency.structural import StructuralIssue
from pizhi.services.maintenance import run_full_maintenance


def _write_characters_index(initialized_project) -> None:
    paths = project_paths(initialized_project)
    paths.global_dir.joinpath("characters_index.md").write_text(
        """# Characters Index

## 沈轩
- **定位**：主角
- **状态**：调查码头血衣

## 阿坤
- **定位**：线人
- **状态**：对血衣来历含糊其辞

## 雷老板
- **定位**：码头势力
- **状态**：只在边缘现身
""",
        encoding="utf-8",
    )


def _write_overdue_foreshadowing(initialized_project) -> None:
    paths = project_paths(initialized_project)
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 码头血衣的来源
- **Planned Payoff**: ch005
- **Related Characters**: 沈轩

### F999 | Priority: medium
- **Description**: 超期伏笔示例
- **Planned Payoff**: ch001
- **Related Characters**: 沈轩

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )


def test_build_chapter_ai_review_context_includes_target_previous_and_globals(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    _write_characters_index(initialized_project)

    issues = [
        StructuralIssue(
            category="人物一致性",
            severity="中",
            description="中严重度 A 类问题也必须出现在 packet 中。",
            evidence="示例证据",
            suggestion="示例建议",
        ),
        StructuralIssue(
            category="时间线单调性",
            severity="高",
            description="高严重度问题示例。",
            evidence="示例证据",
            suggestion="示例建议",
        ),
    ]
    context = build_chapter_ai_review_context(initialized_project, 2, issues)

    assert "当前章节正文" in context.prompt_context
    assert "天亮后，沈轩把那件血衣卷进塑料布" in context.prompt_context
    assert "当前角色快照" in context.prompt_context
    assert "第二章角色状态" in context.prompt_context
    assert "当前关系快照" in context.prompt_context
    assert "合作 + 怀疑" in context.prompt_context
    assert "关键 meta 摘要" in context.prompt_context
    assert "chapter_title" in context.prompt_context
    assert "上一章正文" in context.prompt_context
    assert "沈轩在雨夜里来到码头三号仓" in context.prompt_context
    assert "上一章角色快照" in context.prompt_context
    assert "第一章角色状态" in context.prompt_context
    assert "上一章关系快照" in context.prompt_context
    assert "码头三号仓" in context.prompt_context
    assert "世界观" in context.prompt_context
    assert "相关伏笔" in context.prompt_context
    assert "F001" in context.prompt_context
    assert "角色索引" in context.prompt_context
    assert "调查码头血衣" in context.prompt_context
    assert "A 类结构问题" in context.prompt_context
    assert "中严重度 A 类问题也必须出现在 packet 中。" in context.prompt_context
    assert "高严重度问题示例。" in context.prompt_context
    assert str(Path(".pizhi/chapters/ch002/text.md")) in context.referenced_files
    assert str(Path(".pizhi/global/characters_index.md")) in context.referenced_files


def test_build_full_ai_review_context_compresses_project_snapshot(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))
    _write_overdue_foreshadowing(initialized_project)

    report = run_structural_review(initialized_project, full=True)
    maintenance_result = run_full_maintenance(initialized_project)
    context = build_full_ai_review_context(initialized_project, report, maintenance_result)

    assert "章节问题摘要" in context.prompt_context
    assert "ch002" in context.prompt_context
    assert "时间线单调性" in context.prompt_context
    assert "活跃伏笔" in context.prompt_context
    assert "F001" in context.prompt_context
    assert "超期伏笔" in context.prompt_context
    assert "F999" in context.prompt_context
    assert "重大转折" in context.prompt_context
    assert "最近章节状态" in context.prompt_context
    assert "ch001" in context.prompt_context
    assert "drafted" in context.prompt_context
    assert "章节信号" in context.prompt_context
    assert "雨夜里来到码头三号仓" in context.prompt_context
    assert "比上一章更早的事情" in context.prompt_context
    assert "A 类全书问题" in context.prompt_context
    assert "伏笔超期" in context.prompt_context
    assert "Maintenance" in context.prompt_context
