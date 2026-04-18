from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.synopsis_review import parse_synopsis_candidate
from pizhi.services.synopsis_review import review_synopsis_candidate


def _write_candidate(initialized_project, content: str) -> None:
    paths = project_paths(initialized_project)
    paths.synopsis_candidate_file.write_text(content, encoding="utf-8")


def _prepare_snapshot_with_active_and_referenced_foreshadowing(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    paths = project_paths(initialized_project)
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 码头血衣的来源
- **Planned Payoff**: ch005
- **Related Characters**: 沈轩

## Referenced
### F002
- **Referenced**: true

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )
    paths.timeline_file.write_text(
        """# Timeline

## T001-01
- **时间**: 1986-03-14 夜
- **事件**: 沈轩抵达码头三号仓
- **闪回**: 否
- **重大转折**: 否

## T001-02
- **时间**: 1986-03-15 凌晨
- **事件**: 沈轩发现血衣
- **闪回**: 否
- **重大转折**: 是

## T002-01
- **时间**: 1986-03-16 早晨
- **事件**: 码头边的证词被重新提起
- **闪回**: 否
- **重大转折**: 是
""",
        encoding="utf-8",
    )


def test_review_synopsis_candidate_promotes_valid_candidate(initialized_project, fixture_text):
    _prepare_snapshot_with_active_and_referenced_foreshadowing(initialized_project, fixture_text)
    paths = project_paths(initialized_project)
    existing_synopsis = "# Synopsis\n\n旧内容\n"
    paths.synopsis_file.write_text(existing_synopsis, encoding="utf-8")

    candidate = (
        "第二章的概要正文。\n\n"
        "## coverage_markers\n"
        "foreshadowing_ids:\n"
        "- F001\n"
        "- F002\n"
        "major_turning_points:\n"
        "- T001-02\n"
        "- T002-01\n"
    )
    _write_candidate(initialized_project, candidate)

    review_result = review_synopsis_candidate(initialized_project)

    assert review_result.promoted is True
    assert not paths.synopsis_candidate_file.exists()
    assert paths.synopsis_file.read_text(encoding="utf-8") == "第二章的概要正文。\n"
    assert "coverage_markers" not in paths.synopsis_file.read_text(encoding="utf-8")
    assert paths.cache_dir.joinpath("synopsis_review.md").exists()


def test_review_synopsis_candidate_accepts_bullet_style_marker_headings(initialized_project, fixture_text):
    _prepare_snapshot_with_active_and_referenced_foreshadowing(initialized_project, fixture_text)
    paths = project_paths(initialized_project)

    candidate = (
        "第二章的概要正文。\n\n"
        "## coverage_markers\n"
        "- foreshadowing_ids:\n"
        "  - F001\n"
        "  - F002\n"
        "- major_turning_points:\n"
        "  - T001-02\n"
        "  - T002-01\n"
    )
    _write_candidate(initialized_project, candidate)

    review_result = review_synopsis_candidate(initialized_project)

    assert review_result.promoted is True
    assert not paths.synopsis_candidate_file.exists()
    assert paths.synopsis_file.read_text(encoding="utf-8") == "第二章的概要正文。\n"


def test_review_synopsis_candidate_allows_empty_marker_sets_when_nothing_is_required(initialized_project):
    paths = project_paths(initialized_project)
    paths.foreshadowing_file.write_text(
        """# Foreshadowing Tracker

## Active

## Referenced

## Resolved

## Abandoned
""",
        encoding="utf-8",
    )
    paths.timeline_file.write_text("# Timeline\n\n", encoding="utf-8")

    candidate = (
        "第二章的概要正文。\n\n"
        "## coverage_markers\n"
        "- foreshadowing_ids:\n"
        "- major_turning_points:\n"
    )
    _write_candidate(initialized_project, candidate)

    review_result = review_synopsis_candidate(initialized_project)

    assert review_result.promoted is True
    assert review_result.missing_foreshadowing_ids == ()
    assert review_result.missing_major_turning_point_ids == ()
    assert not paths.synopsis_candidate_file.exists()
    assert paths.synopsis_file.read_text(encoding="utf-8") == "第二章的概要正文。\n"


def test_review_synopsis_candidate_preserves_invalid_candidate(initialized_project, fixture_text):
    _prepare_snapshot_with_active_and_referenced_foreshadowing(initialized_project, fixture_text)
    paths = project_paths(initialized_project)
    existing_synopsis = "# Synopsis\n\n现有概要\n"
    paths.synopsis_file.write_text(existing_synopsis, encoding="utf-8")

    candidate = (
        "第二章的概要正文。\n\n"
        "## coverage_markers\n"
        "foreshadowing_ids:\n"
        "- F001\n"
        "major_turning_points:\n"
        "- T001-02\n"
    )
    _write_candidate(initialized_project, candidate)

    review_result = review_synopsis_candidate(initialized_project)
    review_text = paths.cache_dir.joinpath("synopsis_review.md").read_text(encoding="utf-8")

    assert review_result.promoted is False
    assert paths.synopsis_candidate_file.exists()
    assert paths.synopsis_file.read_text(encoding="utf-8") == existing_synopsis
    assert "missing foreshadowing ids" in review_text
    assert "F002" in review_text
    assert "T002-01" in review_text


def test_review_synopsis_candidate_rejects_unknown_marker_ids(initialized_project, fixture_text):
    _prepare_snapshot_with_active_and_referenced_foreshadowing(initialized_project, fixture_text)
    paths = project_paths(initialized_project)
    existing_synopsis = "# Synopsis\n\n现有概要\n"
    paths.synopsis_file.write_text(existing_synopsis, encoding="utf-8")

    candidate = (
        "第二章的概要正文。\n\n"
        "## coverage_markers\n"
        "foreshadowing_ids:\n"
        "- F001\n"
        "- F002\n"
        "- F999\n"
        "major_turning_points:\n"
        "- T001-02\n"
        "- T002-01\n"
        "- T999-99\n"
    )
    _write_candidate(initialized_project, candidate)

    review_result = review_synopsis_candidate(initialized_project)
    review_text = paths.cache_dir.joinpath("synopsis_review.md").read_text(encoding="utf-8")

    assert review_result.promoted is False
    assert review_result.unexpected_foreshadowing_ids == ("F999",)
    assert review_result.unexpected_major_turning_point_ids == ("T999-99",)
    assert paths.synopsis_candidate_file.exists()
    assert paths.synopsis_file.read_text(encoding="utf-8") == existing_synopsis
    assert "unexpected foreshadowing ids" in review_text
    assert "F999" in review_text
    assert "unexpected major turning points" in review_text
    assert "T999-99" in review_text


def test_review_synopsis_candidate_rejects_malformed_or_empty_candidates(initialized_project):
    paths = project_paths(initialized_project)
    existing_synopsis = "# Synopsis\n\n现有概要\n"
    paths.synopsis_file.write_text(existing_synopsis, encoding="utf-8")

    cases = [
        (
            "概要正文。\n\n"
            "## coverage_markers\n"
            "foreshadowing_ids:\n"
            "- F001\n",
            "missing marker sections: major_turning_points",
        ),
        (
            "## coverage_markers\n"
            "foreshadowing_ids:\n"
            "- F001\n"
            "major_turning_points:\n"
            "- T001-02\n",
            "synopsis candidate body cannot be empty",
        ),
    ]

    for index, (candidate, expected_error) in enumerate(cases, start=1):
        paths.synopsis_candidate_file.write_text(candidate, encoding="utf-8")

        review_result = review_synopsis_candidate(initialized_project)
        review_text = paths.cache_dir.joinpath("synopsis_review.md").read_text(encoding="utf-8")

        assert review_result.promoted is False
        assert review_result.review_text == review_text
        assert paths.synopsis_candidate_file.exists()
        assert paths.synopsis_file.read_text(encoding="utf-8") == existing_synopsis
        assert f"error: {expected_error}" in review_text, index


def test_parse_synopsis_candidate_rejects_malformed_markers():
    raw = (
        "概要正文。\n\n"
        "## coverage_markers\n"
        "foreshadowing_ids:\n"
        "- F001\n"
    )

    try:
        parse_synopsis_candidate(raw)
    except ValueError as exc:
        assert "major_turning_points" in str(exc)
    else:
        raise AssertionError("expected parse_synopsis_candidate() to reject malformed markers")


def test_parse_synopsis_candidate_rejects_empty_body():
    raw = (
        "## coverage_markers\n"
        "foreshadowing_ids:\n"
        "- F001\n"
        "major_turning_points:\n"
        "- T001-02\n"
    )

    try:
        parse_synopsis_candidate(raw)
    except ValueError as exc:
        assert "body" in str(exc)
    else:
        raise AssertionError("expected parse_synopsis_candidate() to reject empty body")


def test_apply_chapter_response_does_not_write_placeholder_notes(initialized_project):
    raw_response = """---
chapter_title: "第三章 新概要"
word_count_estimated: 1200
characters_involved: []
worldview_changed: false
synopsis_changed: true
timeline_events: []
foreshadowing:
  introduced: []
  referenced: []
  resolved: []
---

正文。

## characters_snapshot

# 第三章角色状态

## relationships_snapshot

# 第三章人物关系

## synopsis_new

# 新概要
"""

    apply_chapter_response(initialized_project, 3, raw_response)

    paths = project_paths(initialized_project)
    chapter_notes = paths.chapter_dir(3) / "notes.md"

    assert paths.synopsis_candidate_file.exists()
    assert not chapter_notes.exists()
