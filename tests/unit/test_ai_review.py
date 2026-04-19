from __future__ import annotations

import pytest

from pizhi.domain.ai_review import parse_ai_review_issues


def test_parse_ai_review_markdown_returns_valid_issue_blocks():
    raw = """
### 问题 1
- **类别**：人物一致性
- **严重度**：高
- **描述**：沈轩前后动机冲突。
- **证据**：ch010 表示他要隐瞒，ch011 却直接摊牌。
- **建议修法**：改成试探式对话。
"""

    issues = parse_ai_review_issues(raw)

    assert len(issues) == 1
    assert issues[0].category == "人物一致性"
    assert issues[0].severity == "高"
    assert issues[0].description == "沈轩前后动机冲突。"
    assert issues[0].evidence == "ch010 表示他要隐瞒，ch011 却直接摊牌。"
    assert issues[0].suggestion == "改成试探式对话。"


def test_parse_ai_review_markdown_rejects_unknown_category():
    raw = """
### 问题 1
- **类别**：风格问题
- **严重度**：高
- **描述**：不应接受未列入白名单的类别。
- **证据**：示例。
- **建议修法**：示例。
"""

    with pytest.raises(ValueError, match="unknown review category"):
        parse_ai_review_issues(raw)

