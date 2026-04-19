from __future__ import annotations

from dataclasses import dataclass
import re


ALLOWED_REVIEW_CATEGORIES = {
    "人物一致性",
    "时间线合理性",
    "世界设定一致性",
    "因果一致性",
    "资源一致性",
    "Synopsis 覆盖性",
}
ALLOWED_REVIEW_SEVERITIES = {"高", "中", "低"}


@dataclass(frozen=True, slots=True)
class AIReviewIssue:
    category: str
    severity: str
    description: str
    evidence: str
    suggestion: str


ISSUE_HEADING_RE = re.compile(r"^###\s+问题\s+\d+\s*$", re.MULTILINE)
FIELD_RE = {
    "category": re.compile(r"^- \*\*类别\*\*：(?P<value>.+)$"),
    "severity": re.compile(r"^- \*\*严重度\*\*：(?P<value>.+)$"),
    "description": re.compile(r"^- \*\*描述\*\*：(?P<value>.+)$"),
    "evidence": re.compile(r"^- \*\*证据\*\*：(?P<value>.+)$"),
    "suggestion": re.compile(r"^- \*\*建议修法\*\*：(?P<value>.+)$"),
}


def parse_ai_review_issues(raw: str) -> list[AIReviewIssue]:
    trimmed = raw.strip()
    if not trimmed:
        raise ValueError("ai review markdown cannot be empty")

    if not trimmed.startswith("### 问题"):
        raise ValueError("ai review markdown must start with an issue block")

    matches = list(ISSUE_HEADING_RE.finditer(trimmed))
    if not matches:
        raise ValueError("missing ai review issue blocks")

    issues: list[AIReviewIssue] = []
    for index, match in enumerate(matches):
        block_start = match.end()
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(trimmed)
        block = trimmed[block_start:block_end]
        issues.append(_parse_issue_block(block))

    return issues


def _parse_issue_block(raw_block: str) -> AIReviewIssue:
    lines = [line.strip() for line in raw_block.splitlines() if line.strip()]
    if len(lines) != 5:
        raise ValueError("malformed ai review issue block")

    fields: dict[str, str] = {}
    for line in lines:
        matched_name = None
        matched_value = None
        for field_name, pattern in FIELD_RE.items():
            match = pattern.fullmatch(line)
            if match is not None:
                matched_name = field_name
                matched_value = match.group("value").strip()
                break
        if matched_name is None or matched_value is None:
            raise ValueError(f"malformed ai review field: {line}")
        if matched_name in fields:
            raise ValueError(f"duplicate ai review field: {matched_name}")
        fields[matched_name] = matched_value

    missing_fields = [name for name in FIELD_RE if name not in fields]
    if missing_fields:
        raise ValueError(f"missing ai review fields: {', '.join(missing_fields)}")

    category = fields["category"]
    if category not in ALLOWED_REVIEW_CATEGORIES:
        raise ValueError(f"unknown review category: {category}")

    severity = fields["severity"]
    if severity not in ALLOWED_REVIEW_SEVERITIES:
        raise ValueError(f"unknown review severity: {severity}")

    return AIReviewIssue(
        category=category,
        severity=severity,
        description=fields["description"],
        evidence=fields["evidence"],
        suggestion=fields["suggestion"],
    )
