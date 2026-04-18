from subprocess import run
import sys

from pizhi.services.chapter_writer import apply_chapter_response


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
