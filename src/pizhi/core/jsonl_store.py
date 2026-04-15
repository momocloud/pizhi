from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ChapterIndexStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def upsert(self, record: dict[str, Any]) -> None:
        records = self.read_all()
        by_number = {item["n"]: item for item in records}
        by_number[record["n"]] = record
        ordered = [by_number[key] for key in sorted(by_number)]

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8", newline="\n") as handle:
            for item in ordered:
                handle.write(json.dumps(item, ensure_ascii=False))
                handle.write("\n")
