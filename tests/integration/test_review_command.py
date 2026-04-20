from dataclasses import dataclass
import re
from subprocess import run
import sys

from pizhi.adapters.provider_base import ProviderResponse
from pizhi.cli import main
from pizhi.core.config import ProviderSection
from pizhi.core.config import load_config
from pizhi.core.config import save_config
from pizhi.core.jsonl_store import ChapterIndexStore
from pizhi.core.paths import project_paths
from pizhi.domain.agent_extensions import AgentSpec
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


def _configure_review_agent(initialized_project, *, agent_id: str = "critique.chapter", target_scope: str = "chapter") -> None:
    config_path = initialized_project / ".pizhi" / "config.yaml"
    config = load_config(config_path)
    config.agents = [
        AgentSpec(
            agent_id=agent_id,
            kind="review",
            description="Extension review agent.",
            enabled=True,
            target_scope=target_scope,
            prompt_template="Check the target for issues.",
        )
    ]
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
    assert "人物一致性" in notes_text
    assert "补充动机铺垫" in notes_text


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
    assert "# Review Full" in report_text
    assert "## Summary" in report_text
    assert "## A 类结构检查" in report_text
    assert "## Maintenance" in report_text
    assert "## B 类 AI 审查" in report_text
    assert "时间线合理性" in report_text
    assert "补充过渡段落" in report_text


def test_review_command_full_execute_ignores_missing_chapter_argument(
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

    exit_code = main(["review", "--full", "--execute", "--chapter", "7"])
    output = capsys.readouterr().out
    report_path = initialized_project / ".pizhi" / "cache" / "review_full.md"

    assert exit_code == 0
    assert "Run ID:" in output
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "# Review Full" in report_text
    assert "## Summary" in report_text
    assert "## A 类结构检查" in report_text
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


def test_review_command_execute_records_extension_failure_without_losing_builtin_sections(
    initialized_project, monkeypatch, capsys, fixture_text
):
    monkeypatch.chdir(initialized_project)
    _configure_review_provider(initialized_project)
    _configure_review_agent(initialized_project)
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

    def fake_execute_agent_spec(*_args, **_kwargs):
        from pizhi.services.agent_extensions import AgentExecutionResult

        return AgentExecutionResult(
            agent_id="critique.chapter",
            kind="review",
            status="failed",
            summary="Execution failed",
            issues=[],
            suggestions=[],
            failure_reason="extension failed",
            run_id="run_ext",
        )

    monkeypatch.setattr("pizhi.commands.review_cmd.execute_agent_spec", fake_execute_agent_spec)

    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    exit_code = main(["review", "--chapter", "2", "--execute"])
    output = capsys.readouterr().out
    notes_path = initialized_project / ".pizhi" / "chapters" / "ch002" / "notes.md"

    assert exit_code == 0
    assert "Run ID:" in output
    notes_text = notes_path.read_text(encoding="utf-8")
    assert "## A 类结构检查" in notes_text
    assert "## B 类 AI 审查" in notes_text
    assert "## Review Agent critique.chapter" in notes_text
    assert "failed" in notes_text.lower()


def test_review_command_execute_records_registry_load_failure_without_losing_builtin_sections(
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
    monkeypatch.setattr(
        "pizhi.commands.review_cmd.load_agent_registry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid agent config")),
    )

    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    exit_code = main(["review", "--chapter", "2", "--execute"])
    output = capsys.readouterr().out
    notes_path = initialized_project / ".pizhi" / "chapters" / "ch002" / "notes.md"

    assert exit_code == 0
    assert "Run ID:" in output
    notes_text = notes_path.read_text(encoding="utf-8")
    assert "## A 类结构检查" in notes_text
    assert "## B 类 AI 审查" in notes_text
    assert "## Review Agent extension.setup" in notes_text
    assert "invalid agent config" in notes_text


def test_review_command_execute_without_scope_returns_readable_error_and_does_not_mutate_notes(
    initialized_project, fixture_text
):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch001_response_invalid_timeline.md"))

    first_review = run(
        [sys.executable, "-m", "pizhi", "review", "--chapter", "2"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )
    assert first_review.returncode == 0

    notes_path = initialized_project / ".pizhi" / "chapters" / "ch002" / "notes.md"
    notes_before = notes_path.read_text(encoding="utf-8")

    result = run(
        [sys.executable, "-m", "pizhi", "review", "--execute"],
        cwd=initialized_project,
        capture_output=True,
        text=True,
    )

    notes_after = notes_path.read_text(encoding="utf-8")

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "error:" in result.stderr.lower()
    assert "chapter" in result.stderr.lower() or "full" in result.stderr.lower()
    assert notes_after == notes_before


def test_review_command_execute_rejects_missing_chapter_without_mutation(
    initialized_project, monkeypatch, capsys, fixture_text
):
    monkeypatch.chdir(initialized_project)
    _configure_review_provider(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")

    provider_calls = []

    class RecordingReviewAdapter:
        def execute(self, provider_request):
            provider_calls.append(provider_request)
            return ProviderResponse(
                raw_payload={"id": "resp_test"},
                content_text="### 问题 1\n- **类别**：人物一致性\n- **严重度**：高\n- **描述**：示例。\n- **证据**：示例。\n- **建议修法**：示例。\n",
            )

    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RecordingReviewAdapter(),
    )

    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    notes_path = initialized_project / ".pizhi" / "chapters" / "ch007" / "notes.md"
    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"

    exit_code = main(["review", "--chapter", "7", "--execute"])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "Traceback" not in captured.err
    assert "chapter 7" in captured.err.lower()
    assert provider_calls == []
    assert not notes_path.exists()
    assert not runs_dir.exists()


def test_review_command_execute_rejects_indexed_missing_chapter_target_without_mutation(
    initialized_project, monkeypatch, capsys
):
    monkeypatch.chdir(initialized_project)
    _configure_review_provider(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")

    provider_calls = []

    class RecordingReviewAdapter:
        def execute(self, provider_request):
            provider_calls.append(provider_request)
            return ProviderResponse(
                raw_payload={"id": "resp_test"},
                content_text="### 问题 1\n- **类别**：人物一致性\n- **严重度**：高\n- **描述**：示例。\n- **证据**：示例。\n- **建议修法**：示例。\n",
            )

    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RecordingReviewAdapter(),
    )

    paths = project_paths(initialized_project)
    store = ChapterIndexStore(paths.chapter_index_file)
    store.upsert(
        {
            "n": 7,
            "title": "第007章",
            "vol": 1,
            "status": "drafted",
            "summary": "",
            "updated": "2026-04-18",
        }
    )

    notes_path = initialized_project / ".pizhi" / "chapters" / "ch007" / "notes.md"
    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"

    exit_code = main(["review", "--chapter", "7", "--execute"])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "Traceback" not in captured.err
    assert "chapter 7" in captured.err.lower()
    assert provider_calls == []
    assert not notes_path.exists()
    assert not runs_dir.exists()


def test_review_command_execute_rejects_existing_chapter_directory_with_missing_artifacts_without_mutation(
    initialized_project, monkeypatch, capsys
):
    monkeypatch.chdir(initialized_project)
    _configure_review_provider(initialized_project)
    monkeypatch.setenv("OPENAI_REVIEW_API_KEY", "review-secret")

    provider_calls = []

    class RecordingReviewAdapter:
        def execute(self, provider_request):
            provider_calls.append(provider_request)
            return ProviderResponse(
                raw_payload={"id": "resp_test"},
                content_text="### 问题 1\n- **类别**：人物一致性\n- **严重度**：高\n- **描述**：示例。\n- **证据**：示例。\n- **建议修法**：示例。\n",
            )

    monkeypatch.setattr(
        "pizhi.services.provider_execution.build_provider_adapter",
        lambda *_: RecordingReviewAdapter(),
    )

    paths = project_paths(initialized_project)
    store = ChapterIndexStore(paths.chapter_index_file)
    store.upsert(
        {
            "n": 7,
            "title": "第007章",
            "vol": 1,
            "status": "drafted",
            "summary": "",
            "updated": "2026-04-18",
        }
    )

    chapter_dir = paths.chapter_dir(7)
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "text.md").write_text("", encoding="utf-8")
    (chapter_dir / "characters.md").write_text("   \n", encoding="utf-8")

    notes_path = chapter_dir / "notes.md"
    runs_dir = initialized_project / ".pizhi" / "cache" / "runs"

    exit_code = main(["review", "--chapter", "7", "--execute"])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "Traceback" not in captured.err
    assert "chapter 7" in captured.err.lower()
    assert "required files" in captured.err.lower()
    assert "text.md" in captured.err
    assert "characters.md" in captured.err
    assert "relationships.md" in captured.err
    assert "meta.json" in captured.err
    assert provider_calls == []
    assert not notes_path.exists()
    assert not runs_dir.exists()


def test_review_command_full_execute_failure_keeps_summary_and_maintenance(
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
    apply_chapter_response(initialized_project, 6, fixture_text("ch001_response.md"))

    exit_code = main(["review", "--full", "--execute"])
    output = capsys.readouterr().out
    report_path = initialized_project / ".pizhi" / "cache" / "review_full.md"

    assert exit_code != 0
    assert "Run ID:" in output
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "# Review Full" in report_text
    assert "## Summary" in report_text
    assert "## A 类结构检查" in report_text
    assert "## Maintenance" in report_text
    assert "## B 类 AI 审查" in report_text
    assert re.search(r"^## Global issues:$", report_text, re.MULTILINE) is None
    assert re.search(r"^## ch\d{3}$", report_text, re.MULTILINE) is None
    assert "AI 审查执行失败" in report_text


def test_review_command_full_execute_records_registry_load_failure_without_losing_builtin_sections(
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
    monkeypatch.setattr(
        "pizhi.commands.review_cmd.load_agent_registry",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid agent config")),
    )

    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 6, fixture_text("ch001_response.md"))

    exit_code = main(["review", "--full", "--execute"])
    output = capsys.readouterr().out
    report_path = initialized_project / ".pizhi" / "cache" / "review_full.md"

    assert exit_code == 0
    assert "Run ID:" in output
    report_text = report_path.read_text(encoding="utf-8")
    assert "# Review Full" in report_text
    assert "## Summary" in report_text
    assert "## A 类结构检查" in report_text
    assert "## Maintenance" in report_text
    assert "## B 类 AI 审查" in report_text
    assert "## Review Agent extension.setup" in report_text
    assert "invalid agent config" in report_text


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
    report_text = report_path.read_text(encoding="utf-8")
    assert "# Review Full" in report_text
    assert "## Summary" in report_text
    assert "## A 类结构检查" in report_text
    assert "## Maintenance" in report_text
    assert "## B 类 AI 审查" in report_text
    assert re.search(r"^## Global issues:$", report_text, re.MULTILINE) is None
    assert re.search(r"^## ch\d{3}$", report_text, re.MULTILINE) is None
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
