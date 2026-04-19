from __future__ import annotations


class PromptBudgetError(ValueError):
    pass


def estimate_prompt_size(prompt_text: str) -> int:
    return len(prompt_text)


def ensure_write_prompt_within_budget(*, chapter_number: int, prompt_text: str, max_prompt_chars: int) -> None:
    if estimate_prompt_size(prompt_text) > max_prompt_chars:
        raise PromptBudgetError(f"write prompt exceeds budget for ch{chapter_number:03d}")


class OutlineBatchPlanner:
    def __init__(self, max_prompt_chars: int) -> None:
        self.max_prompt_chars = max_prompt_chars

    def plan(self, chapter_numbers: list[int], prompt_for_chapter) -> list[tuple[int, int]]:
        if not chapter_numbers:
            return []
        batches: list[list[int]]
        if self._batch_fits(chapter_numbers, prompt_for_chapter):
            batches = [chapter_numbers]
        elif len(chapter_numbers) == 3:
            first_two = chapter_numbers[:2]
            last_one = chapter_numbers[2:]
            if self._batch_fits(first_two, prompt_for_chapter) and self._batch_fits(last_one, prompt_for_chapter):
                batches = [first_two, last_one]
            else:
                batches = [[chapter_number] for chapter_number in chapter_numbers]
        else:
            batches = [[chapter_number] for chapter_number in chapter_numbers]
        self._ensure_batches_fit(batches, prompt_for_chapter)
        return [(batch[0], batch[-1]) for batch in batches]

    def _batch_fits(self, chapter_numbers: list[int], prompt_for_chapter) -> bool:
        total_size = sum(estimate_prompt_size(prompt_for_chapter(chapter_number)) for chapter_number in chapter_numbers)
        return total_size <= self.max_prompt_chars

    def _ensure_batches_fit(self, batches: list[list[int]], prompt_for_chapter) -> None:
        for batch in batches:
            if not self._batch_fits(batch, prompt_for_chapter):
                raise PromptBudgetError(f"outline prompt exceeds budget for {self._format_batch_label(batch)}")

    def _format_batch_label(self, chapter_numbers: list[int]) -> str:
        start = chapter_numbers[0]
        end = chapter_numbers[-1]
        if start == end:
            return f"ch{start:03d}"
        return f"ch{start:03d}-ch{end:03d}"
