import pytest

from pizhi.services.prompt_budget import (
    OutlineBatchPlanner,
    PromptBudgetError,
    ensure_write_prompt_within_budget,
    estimate_prompt_size,
)


def test_estimate_prompt_size_uses_character_count():
    assert estimate_prompt_size("abc") == 3


def test_outline_budget_splits_three_chapter_request_into_two_plus_one():
    planner = OutlineBatchPlanner(max_prompt_chars=100)
    prompts = {
        11: "x" * 40,
        12: "x" * 40,
        13: "x" * 40,
    }

    batches = planner.plan([11, 12, 13], lambda n: prompts[n])

    assert batches == [(11, 12), (13, 13)]


def test_outline_budget_keeps_three_chapter_batch_when_it_fits():
    planner = OutlineBatchPlanner(max_prompt_chars=200)
    prompts = {
        11: "x" * 40,
        12: "x" * 40,
        13: "x" * 40,
    }

    batches = planner.plan([11, 12, 13], lambda n: prompts[n])

    assert batches == [(11, 13)]


def test_write_budget_rejects_single_chapter_prompt_that_exceeds_limit():
    with pytest.raises(PromptBudgetError, match="ch011"):
        ensure_write_prompt_within_budget(
            chapter_number=11,
            prompt_text="x" * 1001,
            max_prompt_chars=1000,
        )
