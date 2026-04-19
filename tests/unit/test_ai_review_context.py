from __future__ import annotations

import json
from pathlib import Path

from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.ai_review_context import build_chapter_ai_review_context
from pizhi.services.ai_review_context import build_full_ai_review_context
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.consistency.structural import run_structural_review
from pizhi.services.consistency.structural import StructuralIssue
from pizhi.services.consistency.structural import StructuralReport
from pizhi.services.maintenance import MaintenanceFinding
from pizhi.services.maintenance import MaintenanceResult
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


def _write_alias_character_meta(initialized_project) -> None:
    paths = project_paths(initialized_project)
    meta_path = paths.chapter_dir(2) / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["characters_involved"] = ["轩哥"]
    meta["foreshadowing"] = {"introduced": [], "referenced": [], "resolved": []}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_canonical_character_meta(initialized_project) -> None:
    paths = project_paths(initialized_project)
    meta_path = paths.chapter_dir(2) / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["characters_involved"] = ["沈轩"]
    meta["foreshadowing"] = {"introduced": [], "referenced": [], "resolved": []}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_alias_character_index(initialized_project) -> None:
    paths = project_paths(initialized_project)
    paths.global_dir.joinpath("characters_index.md").write_text(
        """# Characters Index

## 沈轩
- **别名**：轩哥
- **定位**：主角
- **状态**：调查码头血衣

## 阿坤
- **别名**：坤哥
- **定位**：线人
- **状态**：对血衣来历含糊其辞
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


def test_build_chapter_ai_review_context_resolves_character_aliases(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    _write_alias_character_index(initialized_project)
    _write_alias_character_meta(initialized_project)
    paths = project_paths(initialized_project)
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 码头血衣的来源
- **Planned Payoff**: ch005
- **Related Characters**: 沈轩

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )

    report = run_structural_review(initialized_project, chapter_number=2)
    context = build_chapter_ai_review_context(initialized_project, 2, report.chapter_issues[2])

    assert "## 沈轩" in context.prompt_context
    assert "别名" in context.prompt_context
    assert "轩哥" in context.prompt_context
    assert "F001" in context.prompt_context
    assert "码头血衣的来源" in context.prompt_context


def test_build_chapter_ai_review_context_resolves_tracker_aliases(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))
    _write_canonical_character_meta(initialized_project)
    paths = project_paths(initialized_project)
    paths.global_dir.joinpath("characters_index.md").write_text(
        """# Characters Index

## 沈轩
- **别名**：轩哥
- **定位**：主角
- **状态**：调查码头血衣
""",
        encoding="utf-8",
    )
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 码头血衣的来源
- **Planned Payoff**: ch005
- **Related Characters**: 轩哥

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )

    report = run_structural_review(initialized_project, chapter_number=2)
    context = build_chapter_ai_review_context(initialized_project, 2, report.chapter_issues[2])

    assert "F001" in context.prompt_context
    assert "码头血衣的来源" in context.prompt_context


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


def test_build_chapter_ai_review_context_bounds_large_inputs_and_sorts_metadata(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    paths = project_paths(initialized_project)
    chapter_two_dir = paths.chapter_dir(2)
    chapter_one_dir = paths.chapter_dir(1)

    (chapter_two_dir / "text.md").write_text(
        "CURRENT-HEAD\n" + ("current detail " * 1600) + "\nCURRENT-TAIL-SHOULD-NOT-APPEAR\n",
        encoding="utf-8",
    )
    (chapter_one_dir / "text.md").write_text(
        "PREVIOUS-HEAD\n" + ("previous detail " * 1600) + "\nPREVIOUS-TAIL-SHOULD-NOT-APPEAR\n",
        encoding="utf-8",
    )
    paths.worldview_file.write_text(
        "WORLDVIEW-HEAD\n" + ("world detail " * 1600) + "\nWORLDVIEW-TAIL-SHOULD-NOT-APPEAR\n",
        encoding="utf-8",
    )
    paths.global_dir.joinpath("characters_index.md").write_text(
        """# Characters Index

## Alpha
- **别名**：A 哥
- **状态**：""" + ("alpha detail " * 800) + """
ALPHA-TAIL-SHOULD-NOT-APPEAR

## Beta
- **定位**：配角

## Zeta
- **定位**：配角

## Omega
- **定位**：无关角色
""",
        encoding="utf-8",
    )

    chapter_two_meta_path = chapter_two_dir / "meta.json"
    chapter_two_meta = json.loads(chapter_two_meta_path.read_text(encoding="utf-8"))
    chapter_two_meta["characters_involved"] = ["Zeta", "Alpha"]
    chapter_two_meta_path.write_text(
        json.dumps(chapter_two_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    chapter_one_meta_path = chapter_one_dir / "meta.json"
    chapter_one_meta = json.loads(chapter_one_meta_path.read_text(encoding="utf-8"))
    chapter_one_meta["characters_involved"] = ["Beta"]
    chapter_one_meta_path.write_text(
        json.dumps(chapter_one_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    context = build_chapter_ai_review_context(initialized_project, 2, [])

    assert "CURRENT-HEAD" in context.prompt_context
    assert "PREVIOUS-HEAD" in context.prompt_context
    assert "WORLDVIEW-HEAD" in context.prompt_context
    assert "CURRENT-TAIL-SHOULD-NOT-APPEAR" not in context.prompt_context
    assert "PREVIOUS-TAIL-SHOULD-NOT-APPEAR" not in context.prompt_context
    assert "WORLDVIEW-TAIL-SHOULD-NOT-APPEAR" not in context.prompt_context
    assert "ALPHA-TAIL-SHOULD-NOT-APPEAR" not in context.prompt_context
    assert "... [truncated" in context.prompt_context
    assert len(context.prompt_context) < 20000
    assert context.metadata["relevant_character_names"] == ["Alpha", "Beta", "Zeta"]


def test_build_chapter_ai_review_context_bounds_large_meta_summary(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    paths = project_paths(initialized_project)
    meta_path = paths.chapter_dir(2) / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["chapter_title"] = "META-TITLE-HEAD " + ("title detail " * 500) + " META-TITLE-TAIL-SHOULD-NOT-APPEAR"
    meta["characters_involved"] = [f"MetaChar{index:03d}" for index in range(1, 31)]
    meta["characters_involved"].append("META-CHAR-TAIL-SHOULD-NOT-APPEAR")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    context = build_chapter_ai_review_context(initialized_project, 2, [])

    assert "META-TITLE-HEAD" in context.prompt_context
    assert "META-TITLE-TAIL-SHOULD-NOT-APPEAR" not in context.prompt_context
    assert "MetaChar001" in context.prompt_context
    assert "META-CHAR-TAIL-SHOULD-NOT-APPEAR" not in context.prompt_context
    assert "... [truncated" in context.prompt_context
    assert "characters_involved_count" in context.metadata
    assert context.metadata["characters_involved_count"] == 31
    assert context.metadata["characters_involved"][-1] == "... [23 more]"


def test_build_full_ai_review_context_bounds_large_project_context_and_metadata(initialized_project):
    paths = project_paths(initialized_project)
    store = ChapterIndexStore(paths.chapter_index_file)

    for chapter_number in range(1, 41):
        store.upsert(
            {
                "n": chapter_number,
                "title": f"第{chapter_number:03d}章",
                "vol": 1,
                "status": "drafted",
                "summary": f"SIG-{chapter_number:03d}-HEAD " + ("signal detail " * 120) + f" SIG-{chapter_number:03d}-TAIL",
                "updated": "2026-04-18",
            }
        )

    report = StructuralReport(
        chapter_issues={
            chapter_number: [
                StructuralIssue(
                    category="时间线合理性",
                    severity="中",
                    description=f"章节 {chapter_number} 的问题摘要。",
                    evidence="示例证据",
                    suggestion="示例建议",
                )
            ]
            for chapter_number in range(1, 41)
        },
        global_issues=[
            StructuralIssue(
                category="伏笔超期",
                severity="高",
                description="存在超期伏笔。",
                evidence="F999",
                suggestion="尽快回收。",
            )
        ],
    )
    maintenance_result = MaintenanceResult(
        synopsis_review=None,
        archive_result=None,
        findings=[
            MaintenanceFinding(category="Archive", detail=f"archive finding {index}")
            for index in range(1, 4)
        ],
    )

    context = build_full_ai_review_context(initialized_project, report, maintenance_result)

    assert "SIG-040-HEAD" in context.prompt_context
    assert "SIG-001-HEAD" not in context.prompt_context
    assert "SIG-001-TAIL" not in context.prompt_context
    assert len(context.prompt_context) < 18000
    assert "recent_chapters" not in context.metadata
    assert context.metadata["recent_chapter_count"] == 40
    assert context.metadata["recent_chapter_targets"] == ["ch040", "ch039", "ch038", "ch037", "ch036"]
