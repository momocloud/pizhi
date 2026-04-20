from subprocess import run
import sys


from pizhi.cli import main
from pizhi.services.archive_service import ArchiveResult
from pizhi.services.maintenance import MaintenanceFinding
from pizhi.services.maintenance import MaintenanceResult


CHAPTER_THREE_RESPONSE = """---
chapter_title: "第三章 暗巷回声"
word_count_estimated: 3100
characters_involved:
  - 沈轩
  - 顾临
worldview_changed: false
synopsis_changed: false
timeline_events:
  - at: "1986-03-15 夜"
    event: "沈轩在暗巷与顾临短暂交锋"
    is_flashback: false
    is_major_turning_point: true
foreshadowing:
  introduced: []
  referenced: []
  resolved:
    - id: F001
---

顾临终于在暗巷拦住了沈轩，问他血衣究竟从哪里来。

---

## characters_snapshot

# 第三章角色状态

## 沈轩
- **位置**：香港，旧城暗巷
- **状态**：试图隐瞒血衣来源，但已经动摇

## 顾临
- **位置**：香港，旧城暗巷
- **状态**：怀疑加深，决定独自追查

## relationships_snapshot

# 第三章人物关系

## 当前关系状态

| 从 | 到 | 关系 | 信任度 | 备注 |
|----|----|------|--------|------|
| 沈轩 | 顾临 | 对抗 + 利用 | 低 | 各自隐瞒关键信息 |

## 本章变化

| 关系 | 变化前 | 变化后 | 触发原因 |
|------|--------|--------|---------|
| 沈轩 → 顾临 | 试探 | 对抗 + 利用 | 顾临逼问血衣来源 |
"""


def test_continue_command_writes_checkpoint_summary_every_three_chapters(initialized_project, fixture_text):
    outline_response = initialized_project / "outline_expand_response.md"
    outline_response.write_text(
        fixture_text("outline_expand_response.md")
        + "\n## ch003 | 暗巷回声\n- 沈轩在暗巷被顾临截住。\n- 血衣线索首次闭环。\n",
        encoding="utf-8",
    )

    responses_dir = initialized_project / "chapter_responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    (responses_dir / "ch001_response.md").write_text(fixture_text("ch001_response.md"), encoding="utf-8")
    (responses_dir / "ch002_response.md").write_text(fixture_text("ch002_response.md"), encoding="utf-8")
    (responses_dir / "ch003_response.md").write_text(CHAPTER_THREE_RESPONSE, encoding="utf-8")

    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "continue",
            "--count",
            "3",
            "--outline-response-file",
            str(outline_response),
            "--chapter-responses-dir",
            str(responses_dir),
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    checkpoint_files = sorted((initialized_project / ".pizhi" / "cache").glob("checkpoint-*.md"))
    assert checkpoint_files

    checkpoint_text = checkpoint_files[0].read_text(encoding="utf-8")
    assert "雨夜访客" in checkpoint_text
    assert "暗巷回声" in checkpoint_text
    assert "F001" in checkpoint_text


def test_continue_command_checkpoint_includes_maintenance_summary(initialized_project, fixture_text):
    outline_response = initialized_project / "outline_expand_response.md"
    outline_response.write_text(
        fixture_text("outline_expand_response.md")
        + "\n## ch003 | 暗巷回声\n- 沈轩在暗巷被顾临截住。\n- 血衣线索首次闭环。\n",
        encoding="utf-8",
    )

    responses_dir = initialized_project / "chapter_responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    (responses_dir / "ch001_response.md").write_text(
        fixture_text("ch001_response_synopsis_invalid.md"),
        encoding="utf-8",
    )
    (responses_dir / "ch002_response.md").write_text(fixture_text("ch002_response.md"), encoding="utf-8")
    (responses_dir / "ch003_response.md").write_text(CHAPTER_THREE_RESPONSE, encoding="utf-8")

    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "continue",
            "--count",
            "3",
            "--outline-response-file",
            str(outline_response),
            "--chapter-responses-dir",
            str(responses_dir),
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    checkpoint_files = sorted((initialized_project / ".pizhi" / "cache").glob("checkpoint-*.md"))
    assert checkpoint_files

    checkpoint_text = checkpoint_files[0].read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "Maintenance" in checkpoint_text
    assert "Synopsis review" in checkpoint_text


def test_continue_command_checkpoint_preserves_maintenance_agent_findings(
    initialized_project,
    fixture_text,
    monkeypatch,
):
    outline_response = initialized_project / "outline_expand_response.md"
    outline_response.write_text(
        fixture_text("outline_expand_response.md")
        + "\n## ch003 | 暗巷回声\n- 沈轩在暗巷被顾临截住。\n- 血衣线索首次闭环。\n",
        encoding="utf-8",
    )

    responses_dir = initialized_project / "chapter_responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    (responses_dir / "ch001_response.md").write_text(
        fixture_text("ch001_response_synopsis_invalid.md"),
        encoding="utf-8",
    )
    (responses_dir / "ch002_response.md").write_text(fixture_text("ch002_response.md"), encoding="utf-8")
    (responses_dir / "ch003_response.md").write_text(CHAPTER_THREE_RESPONSE, encoding="utf-8")

    maintenance_result = MaintenanceResult(
        synopsis_review=None,
        archive_result=ArchiveResult(findings=[]),
        findings=[
            MaintenanceFinding(
                category="Maintenance agent",
                detail="archive.audit: synopsis-extension finding",
            )
        ],
    )
    monkeypatch.chdir(initialized_project)
    monkeypatch.setattr(
        "pizhi.services.write_service.run_after_write",
        lambda *_args, **_kwargs: maintenance_result,
    )

    result = main(
        [
            "continue",
            "--count",
            "3",
            "--outline-response-file",
            str(outline_response),
            "--chapter-responses-dir",
            str(responses_dir),
        ]
    )

    checkpoint_files = sorted((initialized_project / ".pizhi" / "cache").glob("checkpoint-*.md"))
    assert checkpoint_files

    checkpoint_text = checkpoint_files[0].read_text(encoding="utf-8")

    assert result == 0
    assert "Maintenance agent" in checkpoint_text
    assert "archive.audit: synopsis-extension finding" in checkpoint_text


def test_continue_command_checkpoint_preserves_mixed_maintenance_outcomes(initialized_project, fixture_text):
    outline_response = initialized_project / "outline_expand_response.md"
    outline_response.write_text(
        fixture_text("outline_expand_response.md")
        + "\n## ch003 | 暗巷回声\n- 沈轩在暗巷被顾临截住。\n- 血衣线索首次闭环。\n",
        encoding="utf-8",
    )

    responses_dir = initialized_project / "chapter_responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    (responses_dir / "ch001_response.md").write_text(
        fixture_text("ch001_response_synopsis_invalid.md"),
        encoding="utf-8",
    )
    valid_chapter_two = fixture_text("ch001_response_synopsis_valid.md").replace(
        "- T001-02",
        "- T001-02\n- T002-02",
    )
    (responses_dir / "ch002_response.md").write_text(
        valid_chapter_two,
        encoding="utf-8",
    )
    (responses_dir / "ch003_response.md").write_text(CHAPTER_THREE_RESPONSE, encoding="utf-8")

    result = run(
        [
            sys.executable,
            "-m",
            "pizhi",
            "continue",
            "--count",
            "3",
            "--outline-response-file",
            str(outline_response),
            "--chapter-responses-dir",
            str(responses_dir),
        ],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    checkpoint_files = sorted((initialized_project / ".pizhi" / "cache").glob("checkpoint-*.md"))
    assert checkpoint_files

    checkpoint_text = checkpoint_files[0].read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "ch001: Synopsis review rejected" in checkpoint_text
    assert "ch002: Synopsis review promoted" in checkpoint_text
