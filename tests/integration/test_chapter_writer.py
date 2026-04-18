import json

from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.consistency.structural import run_structural_review


def test_apply_chapter_response_writes_chapter_and_updates_index(initialized_project, fixture_text):
    result = apply_chapter_response(
        initialized_project,
        chapter_number=1,
        raw_response=fixture_text("ch001_response.md"),
    )

    assert result.chapter_dir.joinpath("text.md").exists()
    assert result.chapter_dir.joinpath("characters.md").exists()
    assert result.chapter_dir.joinpath("relationships.md").exists()
    assert result.chapter_dir.joinpath("worldview_patch.md").exists()

    index_text = initialized_project.joinpath(".pizhi", "chapters", "index.jsonl").read_text(encoding="utf-8")
    timeline_text = initialized_project.joinpath(".pizhi", "global", "timeline.md").read_text(encoding="utf-8")
    foreshadowing_text = initialized_project.joinpath(".pizhi", "global", "foreshadowing.md").read_text(encoding="utf-8")

    assert '"status": "drafted"' in index_text
    assert "第一章 雨夜访客" in index_text
    assert "T001-01" in timeline_text
    assert "F001" in foreshadowing_text


def test_apply_chapter_response_keeps_archived_non_flashback_context_for_review(initialized_project):
    paths = project_paths(initialized_project)
    paths.archive_dir.mkdir(parents=True, exist_ok=True)
    (paths.archive_dir / "timeline_ch001-050.md").write_text(
        """# Timeline Archive: ch001-ch050

## T050-01
- **时间**: 1986-03-20 夜
- **事件**: 归档前最后一条主线推进
- **闪回**: 否
- **重大转折**: 否
""",
        encoding="utf-8",
    )

    apply_chapter_response(
        initialized_project,
        chapter_number=51,
        raw_response=_chapter_response(
            chapter_title="第五十一章 旧案回声",
            body="沈轩翻出旧案卷宗，只在回忆里补全缺口。",
            timeline_events=[
                {
                    "at": "1986-03-18 夜",
                    "event": "沈轩回想两天前听到的旧证词",
                    "is_flashback": True,
                    "is_major_turning_point": False,
                }
            ],
        ),
    )

    apply_chapter_response(
        initialized_project,
        chapter_number=52,
        raw_response=_chapter_response(
            chapter_title="第五十二章 错位脚印",
            body="沈轩在仓库外确认一串更早出现的脚印。",
            timeline_events=[
                {
                    "at": "1986-03-19 夜",
                    "event": "沈轩在仓库外确认脚印",
                    "is_flashback": False,
                    "is_major_turning_point": False,
                }
            ],
        ),
    )

    meta = json.loads((paths.chapter_dir(52) / "meta.json").read_text(encoding="utf-8"))

    assert meta["review_context"]["previous_last_non_flashback"] == "1986-03-20 夜"

    report = run_structural_review(initialized_project, chapter_number=52)

    assert any(issue.category == "时间线单调性" for issue in report.chapter_issues[52])


def _chapter_response(*, chapter_title: str, body: str, timeline_events: list[dict]) -> str:
    payload = {
        "chapter_title": chapter_title,
        "word_count_estimated": 1800,
        "characters_involved": ["沈轩"],
        "worldview_changed": False,
        "synopsis_changed": False,
        "timeline_events": timeline_events,
        "foreshadowing": {
            "introduced": [],
            "referenced": [],
            "resolved": [],
        },
    }
    return (
        "---\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n---\n\n"
        + body
        + "\n\n---\n\n## characters_snapshot\n\n# 角色状态\n\n## 沈轩\n- **位置**：香港\n- **状态**：调查中\n\n"
        + "## relationships_snapshot\n\n# 人物关系\n\n## 当前关系状态\n\n| 从 | 到 | 关系 | 信任度 | 备注 |\n"
        + "|----|----|------|--------|------|\n| 沈轩 | 自己 | 调查 | 中 | 持续推进 |\n\n## 本章变化\n\n"
        + "| 关系 | 变化前 | 变化后 | 触发原因 |\n|------|--------|--------|---------|\n"
        + "| 沈轩 → 自己 | 调查 | 调查 | 继续追查 |\n"
    )
