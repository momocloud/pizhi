from __future__ import annotations

from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.consistency.structural import run_structural_review
from pizhi.services.maintenance import run_full_maintenance
from pizhi.services.ai_review_context import build_chapter_ai_review_context
from pizhi.services.ai_review_context import build_full_ai_review_context


def test_build_chapter_ai_review_context_includes_target_previous_and_globals(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    report = run_structural_review(initialized_project, chapter_number=2)
    context = build_chapter_ai_review_context(initialized_project, 2, report.chapter_issues[2])

    assert "当前章节正文" in context.prompt_context
    assert "上一章正文" in context.prompt_context
    assert "世界观" in context.prompt_context
    assert "A 类结构问题" in context.prompt_context


def test_build_full_ai_review_context_compresses_project_snapshot(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))
    apply_chapter_response(initialized_project, 2, fixture_text("ch002_response.md"))

    report = run_structural_review(initialized_project, full=True)
    maintenance_result = run_full_maintenance(initialized_project)
    context = build_full_ai_review_context(initialized_project, report, maintenance_result)

    assert "活跃伏笔" in context.prompt_context
    assert "重大转折" in context.prompt_context
    assert "Maintenance" in context.prompt_context
