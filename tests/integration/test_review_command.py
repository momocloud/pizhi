from dataclasses import dataclass
from subprocess import run
import sys

from pizhi.adapters.provider_base import ProviderResponse
from pizhi.cli import main
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.services.chapter_writer import apply_chapter_response


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


@dataclass
class StaticReviewAdapter:
    content_text: str

    def execute(self, provider_request):
        return ProviderResponse(
            raw_payload={"id": "resp_test"},
            content_text=self.content_text,
        )


@dataclass
class FailingReviewAdapter:
    error_message: str

    def execute(self, provider_request):
        raise RuntimeError(self.error_message)


def _configure_review_provider(initialized_project) -> None:
    config_path = initialized_project / ".pizhi" / "config.yaml"
    config = load_config(config_path)
    config.provider = ProviderSection(
        provider="openai_compatible",
        model="gpt-5.4",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        review_model="gpt-5.4-mini",
        review_base_url="https://api.openai.com/v1/review",
        review_api_key_env="OPENAI_REVIEW_API_KEY",
    )
    save_config(config_path, config)


def test_review_command_writes_notes_file(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "review", "--chapter", "2"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    notes_path = initialized_project / ".pizhi" / "chapters" / "ch002" / "notes.md"

    assert result.returncode == 0
    assert notes_path.exists()
    assert "时间线单调性" in notes_path.read_text(encoding="utf-8")


def test_review_command_chapter_execute_writes_ai_review_and_run_id(
    initialized_project, monkeypatch, capsys, fixture_text
):
    monkeypatch.chdir(initialized_project)
    _configure_review_provider(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StaticReviewAdapter(
            """\
### 问题 1
- **类别**：人物一致性
- **严重度**：高
- **描述**：沈轩前后动机冲突。
- **证据**：示例证据。
- **建议修法**：补充动机铺垫。
""",
        ),
    )

    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    exit_code = main(["review", "--chapter", "2", "--execute"])
    output = capsys.readouterr().out
    notes_path = initialized_project / ".pizhi" / "chapters" / "ch002" / "notes.md"

    assert exit_code == 0
    assert "Run ID:" in output
    assert notes_path.exists()
    notes_text = notes_path.read_text(encoding="utf-8")
    assert "## A 类结构检查" in notes_text
    assert "## B 类 AI 审查" in notes_text


def test_review_command_full_execute_writes_ai_review_and_cache_report(
    initialized_project, monkeypatch, capsys, fixture_text
):
    monkeypatch.chdir(initialized_project)
    _configure_review_provider(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: StaticReviewAdapter(
            """\
### 问题 1
- **类别**：时间线合理性
- **严重度**：中
- **描述**：章节时间线略显跳跃。
- **证据**：示例证据。
- **建议修法**：补充过渡段落。
""",
        ),
    )

    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 6, fixture_text("ch001_response.md"))

    exit_code = main(["review", "--full", "--execute"])
    output = capsys.readouterr().out
    report_path = initialized_project / ".pizhi" / "cache" / "review_full.md"

    assert exit_code == 0
    assert "Run ID:" in output
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "## Maintenance" in report_text
    assert "## B 类 AI 审查" in report_text


def test_review_command_execute_failure_keeps_a_class_output(
    initialized_project, monkeypatch, capsys, fixture_text
):
    monkeypatch.chdir(initialized_project)
    _configure_review_provider(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")
    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: FailingReviewAdapter("provider request failed"),
    )

    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    exit_code = main(["review", "--chapter", "2", "--execute"])
    output = capsys.readouterr().out
    notes_path = initialized_project / ".pizhi" / "chapters" / "ch002" / "notes.md"

    assert exit_code != 0
    assert "Run ID:" in output
    assert notes_path.exists()
    notes_text = notes_path.read_text(encoding="utf-8")
    assert "## A 类结构检查" in notes_text
    assert "## B 类 AI 审查" in notes_text
    assert "AI 审查执行失败" in notes_text


def test_review_command_full_writes_cache_report(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 6, fixture_text("ch001_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "review", "--full"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    report_path = initialized_project / ".pizhi" / "cache" / "review_full.md"

    assert result.returncode == 0
    assert report_path.exists()
    assert "Global issues:" in result.stdout


def test_review_command_full_backfills_archive_and_reports_maintenance(initialized_project, fixture_text):
    _seed_drafted_block(initialized_project)
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 50, fixture_text("ch001_response.md"))

    result = run(
        [sys.executable, "-m", "pizhi", "review", "--full"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    timeline_archive = initialized_project / ".pizhi" / "archive" / "timeline_ch001-050.md"
    report_path = initialized_project / ".pizhi" / "cache" / "review_full.md"

    assert result.returncode == 0, result.stderr
    assert "Maintenance findings:" in result.stdout
    assert timeline_archive.exists()
    assert "## Maintenance" in report_path.read_text(encoding="utf-8")
    assert "Archive findings" in report_path.read_text(encoding="utf-8")
