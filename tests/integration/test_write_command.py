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


def _stale_candidate_response() -> str:
    return """---
chapter_title: "第一章 雨夜访客"
word_count_estimated: 3200
characters_involved:
  - 沈轩
  - 阿坤
worldview_changed: false
synopsis_changed: true
timeline_events:
  - at: "1986-03-14 夜"
    event: "沈轩抵达码头三号仓"
    is_flashback: false
    is_major_turning_point: false
  - at: "1986-03-15 凌晨"
    event: "沈轩发现血衣"
    is_flashback: false
    is_major_turning_point: true
foreshadowing:
  introduced:
    - id: F001
      desc: "码头血衣的来源"
      planned_payoff: "ch005"
      priority: high
      related_characters:
        - 沈轩
  referenced: []
  resolved: []
---

沈轩在雨夜里来到码头三号仓，先一步意识到血衣不是巧合。

---

## characters_snapshot

# 第一章角色状态

## 沈轩
- **位置**：香港，葵涌码头
- **状态**：刚察觉血衣可能牵出更深的旧案

## 阿坤
- **位置**：香港，葵涌码头
- **状态**：故作镇定，仍在观察沈轩的反应

## relationships_snapshot

# 第一章人物关系

## 当前关系状态

| 从 | 到 | 关系 | 信任度 | 备注 |
|----|----|------|--------|------|
| 沈轩 | 阿坤 | 合作 | 中 | 暂时同行，但彼此保留 |

## 本章变化

| 关系 | 变化前 | 变化后 | 触发原因 |
|------|--------|--------|---------|
| 沈轩 → 阿坤 | 无 | 合作 | 一同进入码头查仓 |

## synopsis_new

# Synopsis

沈轩卷入码头血衣谜团，这份遗留概要还提前写入了下一章才会补齐的维护标记。

## coverage_markers
foreshadowing_ids:
- F001
- F002
major_turning_points:
- T001-02
- T002-01
"""


def _second_chapter_without_synopsis_update() -> str:
    return """---
chapter_title: "第二章 血衣余波"
word_count_estimated: 3300
characters_involved:
  - 沈轩
  - 阿坤
worldview_changed: false
synopsis_changed: false
timeline_events:
  - at: "1986-03-15 上午"
    event: "沈轩确认血衣还牵出新的目击者"
    is_flashback: false
    is_major_turning_point: true
foreshadowing:
  introduced:
    - id: F002
      desc: "血衣目击者留下的第二条线索"
      planned_payoff: "ch006"
      priority: high
      related_characters:
        - 沈轩
  referenced:
    - id: F001
  resolved: []
---

沈轩和阿坤离开码头后，确认血衣背后还有新的目击者。

---

## characters_snapshot

# 第二章角色状态

## 沈轩
- **位置**：香港，旺角
- **状态**：意识到血衣线索开始外溢

## 阿坤
- **位置**：香港，旺角
- **状态**：继续回避关键问题

## relationships_snapshot

# 第二章人物关系

## 当前关系状态

| 从 | 到 | 关系 | 信任度 | 备注 |
|----|----|------|--------|------|
| 沈轩 | 阿坤 | 合作 + 怀疑 | 低 | 彼此都知道仍有隐瞒 |

## 本章变化

| 关系 | 变化前 | 变化后 | 触发原因 |
|------|--------|--------|---------|
| 沈轩 → 阿坤 | 合作 | 合作 + 怀疑 | 新目击者线索让沈轩更不信任阿坤 |
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


def test_write_and_full_review_do_not_promote_stale_synopsis_candidate(initialized_project):
    chapter_one_dir = initialized_project / ".pizhi" / "chapters" / "ch001"
    chapter_one_dir.mkdir(parents=True, exist_ok=True)
    (chapter_one_dir / "outline.md").write_text(
        "# 第001章 雨夜访客\n\n- 沈轩在码头发现血衣。\n",
        encoding="utf-8",
    )
    chapter_two_dir = initialized_project / ".pizhi" / "chapters" / "ch002"
    chapter_two_dir.mkdir(parents=True, exist_ok=True)
    (chapter_two_dir / "outline.md").write_text(
        "# 第002章 血衣余波\n\n- 沈轩确认血衣牵出新的目击者。\n",
        encoding="utf-8",
    )

    ch1_response = initialized_project / "ch001_response_stale_candidate.md"
    ch1_response.write_text(_stale_candidate_response(), encoding="utf-8")
    ch2_response = initialized_project / "ch002_response_no_synopsis.md"
    ch2_response.write_text(_second_chapter_without_synopsis_update(), encoding="utf-8")

    first_result = run(
        [sys.executable, "-m", "pizhi", "write", "--chapter", "1", "--response-file", str(ch1_response)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    paths = project_paths(initialized_project)
    stale_review_text = (paths.cache_dir / "synopsis_review.md").read_text(encoding="utf-8")

    assert first_result.returncode == 0, first_result.stderr
    assert paths.synopsis_candidate_file.exists()
    assert "status: rejected" in stale_review_text
    assert "unexpected foreshadowing ids: F002" in stale_review_text
    assert "unexpected major turning points: T002-01" in stale_review_text

    second_result = run(
        [sys.executable, "-m", "pizhi", "write", "--chapter", "2", "--response-file", str(ch2_response)],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    synopsis_text_after_write = paths.synopsis_file.read_text(encoding="utf-8")
    review_text_after_write = (paths.cache_dir / "synopsis_review.md").read_text(encoding="utf-8")

    assert second_result.returncode == 0, second_result.stderr
    assert paths.synopsis_candidate_file.exists()
    assert "沈轩卷入码头血衣谜团，这份遗留概要还提前写入了下一章才会补齐的维护标记。" not in synopsis_text_after_write
    assert review_text_after_write == stale_review_text

    full_review_result = run(
        [sys.executable, "-m", "pizhi", "review", "--full"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    full_report = (paths.cache_dir / "review_full.md").read_text(encoding="utf-8")
    review_text_after_full = (paths.cache_dir / "synopsis_review.md").read_text(encoding="utf-8")

    assert full_review_result.returncode == 0, full_review_result.stderr
    assert paths.synopsis_candidate_file.exists()
    assert review_text_after_full == stale_review_text
    assert "- Synopsis review: not run." in full_report


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
