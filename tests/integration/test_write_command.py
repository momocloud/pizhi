from subprocess import run
import sys

from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.maintenance import run_full_maintenance
from pizhi.services.write_service import WriteService


def _seed_drafted_block(initialized_project, start_chapter: int = 1, end_chapter: int = 50) -> None:
    paths = project_paths(initialized_project)
    store = ChapterIndexStore(paths.chapter_index_file)
    for chapter_number in range(start_chapter, end_chapter + 1):
        store.upsert(
            {
                "n": chapter_number,
                "title": f"第{chapter_number:03d}章",
                "vol": 1,
                "status": "drafted",
                "summary": "",
                "updated": "2026-04-18",
            }
        )


def _prepare_archived_write_context(initialized_project, fixture_text) -> None:
    _seed_drafted_block(initialized_project)
    apply_chapter_response(initialized_project, 50, fixture_text("ch001_response.md"))
    run_full_maintenance(initialized_project)

    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch051"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第051章 封档之后\n\n- 新章节需要承接已封档的关键转折。\n",
        encoding="utf-8",
    )


def _archived_synopsis_response() -> str:
    return """---
chapter_title: "第五十一章 封档之后"
word_count_estimated: 1800
characters_involved:
  - 沈轩
worldview_changed: false
synopsis_changed: true
timeline_events: []
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---

封档后的章节继续推进沈轩对血衣来源的追查。

## characters_snapshot

# 第五十一章角色状态

## 沈轩
- **位置**：香港，旺角
- **状态**：仍在追查封档前遗留的血衣线索

## relationships_snapshot

# 第五十一章人物关系

## 当前关系状态

| 从 | 到 | 关系 | 信任度 | 备注 |
|----|----|------|--------|------|
| 沈轩 | 阿坤 | 怀疑 | 低 | 沈轩仍记得封档前的关键发现 |

## 本章变化

| 关系 | 变化前 | 变化后 | 触发原因 |
|------|--------|--------|---------|
| 沈轩 → 阿坤 | 怀疑 | 怀疑 | 封档后仍未消除对血衣来源的疑虑 |

## synopsis_new

# Synopsis

封档后的概要继续承接沈轩发现血衣这一重大转折，并说明他仍在追查这条旧线索。

## coverage_markers
foreshadowing_ids:
 - F001
major_turning_points:
- T050-02
"""


def test_write_command_applies_response_file(initialized_project, fixture_text):
    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
        encoding="utf-8",
    )

    response_file = initialized_project / "ch001_response.md"
    response_file.write_text(fixture_text("ch001_response.md"), encoding="utf-8")

    result = run(
        [sys.executable, "-m", "pizhi", "write", "--chapter", "1", "--response-file", str(response_file)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (chapter_dir / "text.md").exists()
    index_text = (initialized_project / ".pizhi" / "chapters" / "index.jsonl").read_text(encoding="utf-8")
    assert '"status": "drafted"' in index_text


def test_write_command_promotes_valid_synopsis_candidate(initialized_project, fixture_text):
    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
        encoding="utf-8",
    )

    response_file = initialized_project / "ch001_response_synopsis_valid.md"
    response_file.write_text(fixture_text("ch001_response_synopsis_valid.md"), encoding="utf-8")

    result = run(
        [sys.executable, "-m", "pizhi", "write", "--chapter", "1", "--response-file", str(response_file)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    synopsis_text = (initialized_project / ".pizhi" / "global" / "synopsis.md").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert synopsis_text.startswith("# Synopsis")
    assert "沈轩卷入码头血衣谜团" in synopsis_text
    assert not (initialized_project / ".pizhi" / "global" / "synopsis_candidate.md").exists()
    assert (initialized_project / ".pizhi" / "cache" / "synopsis_review.md").exists()
    assert "missing coverage_markers section" not in (
        initialized_project / ".pizhi" / "cache" / "synopsis_review.md"
    ).read_text(encoding="utf-8")


def test_write_command_keeps_invalid_synopsis_candidate_and_writes_review_cache(initialized_project, fixture_text):
    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n",
        encoding="utf-8",
    )

    response_file = initialized_project / "ch001_response_synopsis_invalid.md"
    response_file.write_text(fixture_text("ch001_response_synopsis_invalid.md"), encoding="utf-8")

    result = run(
        [sys.executable, "-m", "pizhi", "write", "--chapter", "1", "--response-file", str(response_file)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    candidate_path = initialized_project / ".pizhi" / "global" / "synopsis_candidate.md"
    review_path = initialized_project / ".pizhi" / "cache" / "synopsis_review.md"

    assert result.returncode == 0, result.stderr
    assert candidate_path.exists()
    assert review_path.exists()
    assert "rejected" in review_path.read_text(encoding="utf-8")


def test_write_command_repeated_maintenance_runs_do_not_duplicate_archive_output(initialized_project, fixture_text):
    _seed_drafted_block(initialized_project)
    chapter_one_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
    chapter_one_dir.mkdir(parents=True, exist_ok=True)
    (chapter_one_dir / "outline.md").write_text("# 第001章 雨夜访客\n\n- 沈轩在码头发现异常。\n", encoding="utf-8")
    apply_chapter_response(initialized_project, 50, fixture_text("ch001_response.md"))

    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch051"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第051章 封档之后\n\n- 新章节触发维护钩子。\n",
        encoding="utf-8",
    )

    response_file = initialized_project / "ch051_response.md"
    response_file.write_text(
        fixture_text("ch002_response.md").replace("第二章 码头血衣", "第五十一章 封档之后"),
        encoding="utf-8",
    )

    first_result = run(
        [sys.executable, "-m", "pizhi", "write", "--chapter", "51", "--response-file", str(response_file)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )
    second_result = run(
        [sys.executable, "-m", "pizhi", "review", "--full"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    archive_text = (initialized_project / ".pizhi" / "archive" / "timeline_ch001-050.md").read_text(encoding="utf-8")
    live_timeline_text = (initialized_project / ".pizhi" / "global" / "timeline.md").read_text(encoding="utf-8")

    assert first_result.returncode == 0, first_result.stderr
    assert second_result.returncode == 0, second_result.stderr
    assert archive_text.count("## T050-01") == 1
    assert "## T050-01" not in live_timeline_text


def test_write_prompt_includes_synopsis_coverage_contract_and_archived_turning_points(initialized_project, fixture_text):
    _prepare_archived_write_context(initialized_project, fixture_text)

    prompt_artifact = WriteService(initialized_project).write(chapter_number=51).prompt_artifact
    prompt_text = prompt_artifact.prompt_path.read_text(encoding="utf-8")

    assert "## synopsis_new" in prompt_text
    assert "## coverage_markers" in prompt_text
    assert "foreshadowing_ids:" in prompt_text
    assert "major_turning_points:" in prompt_text
    assert "archived" in prompt_text
    assert "T050-02" in prompt_text


def test_write_prompt_requires_new_synopsis_coverage_ids_for_first_chapter(initialized_project):
    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第001章 雨夜访客\n\n- 沈轩首次发现关键线索。\n",
        encoding="utf-8",
    )

    prompt_artifact = WriteService(initialized_project).write(chapter_number=1).prompt_artifact
    prompt_text = prompt_artifact.prompt_path.read_text(encoding="utf-8")

    assert "If the pre-write lists below show `- (none)`" in prompt_text
    assert "You must still list every foreshadowing ID newly introduced or newly referenced in this chapter" in prompt_text
    assert "For this chapter, timeline event #1 is `T001-01`, event #2 is `T001-02`" in prompt_text
    assert "If you introduce `F001` and the second timeline event is a major turning point" in prompt_text


def test_write_prompt_ignores_overlapping_archive_turning_points(initialized_project, fixture_text):
    _seed_drafted_block(initialized_project)
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    archive_dir = initialized_project / ".pizhi" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "timeline_ch001-050.md").write_text(
        """# Timeline Archive: ch001-ch050

## T050-02
- **时间**: 1986-04-01 夜
- **事件**: 伪造的封档转折
- **闪回**: 否
- **重大转折**: 是
""",
        encoding="utf-8",
    )

    chapter_dir = initialized_project / ".pizhi" / "chapters" / "ch002"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "outline.md").write_text(
        "# 第002章 继续追查\n\n- 沈轩延续第一章的调查。\n",
        encoding="utf-8",
    )

    prompt_artifact = WriteService(initialized_project).write(chapter_number=2).prompt_artifact
    prompt_text = prompt_artifact.prompt_path.read_text(encoding="utf-8")

    assert "T001-02" in prompt_text
    assert "T050-02" not in prompt_text


def test_write_command_promotes_synopsis_candidate_covering_archived_turning_points(initialized_project, fixture_text):
    _prepare_archived_write_context(initialized_project, fixture_text)
    response_file = initialized_project / "ch051_response_synopsis_archived.md"
    response_file.write_text(_archived_synopsis_response(), encoding="utf-8")

    result = run(
        [sys.executable, "-m", "pizhi", "write", "--chapter", "51", "--response-file", str(response_file)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    paths = project_paths(initialized_project)
    synopsis_text = paths.synopsis_file.read_text(encoding="utf-8")
    review_text = (paths.cache_dir / "synopsis_review.md").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "封档后的概要继续承接沈轩发现血衣这一重大转折" in synopsis_text
    assert not paths.synopsis_candidate_file.exists()
    assert "status: promoted" in review_text
    assert "missing major turning points: none" in review_text
