from pizhi.domain.foreshadowing import parse_planned_payoff
from pizhi.domain.foreshadowing import parse_tracker_entries
from pizhi.domain.foreshadowing import update_foreshadowing_tracker


def test_foreshadowing_tracker_adds_introduced_item_to_active_section():
    current = "# Foreshadowing Tracker\n\n## Active\n\n## Referenced\n\n## Resolved\n\n## Abandoned\n"
    operations = {
        "introduced": [
            {
                "id": "F001",
                "desc": "码头血衣的来源",
                "planned_payoff": "ch005",
                "priority": "high",
                "related_characters": ["沈轩"],
            }
        ],
        "referenced": [],
        "resolved": [],
    }

    updated = update_foreshadowing_tracker(current, operations)

    assert "### F001 | Priority: high" in updated
    assert "码头血衣的来源" in updated


def test_foreshadowing_tracker_writes_resolved_in_for_resolved_items():
    current = "# Foreshadowing Tracker\n\n## Active\n\n## Referenced\n\n## Resolved\n\n## Abandoned\n"
    operations = {
        "introduced": [],
        "referenced": [],
        "resolved": [
            {
                "id": "F002",
                "resolution": "真相已经揭露",
            }
        ],
    }

    updated = update_foreshadowing_tracker(current, operations, chapter_number=12)

    assert "### F002" in updated
    assert "- **Resolution**: 真相已经揭露" in updated
    assert "- **Resolved In**: ch012" in updated


def test_parse_planned_payoff_range():
    payoff = parse_planned_payoff("ch010-ch015")

    assert payoff.start_chapter == 10
    assert payoff.end_chapter == 15
    assert payoff.open_ended is False


def test_parse_planned_payoff_single_chapter():
    payoff = parse_planned_payoff("ch018")

    assert payoff.start_chapter == 18
    assert payoff.end_chapter == 18
    assert payoff.open_ended is False


def test_parse_planned_payoff_open_ended():
    payoff = parse_planned_payoff("ch030+")

    assert payoff.start_chapter == 30
    assert payoff.end_chapter is None
    assert payoff.open_ended is True


def test_parse_tracker_entries_returns_active_entry():
    text = """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 码头血衣的来源
- **Planned Payoff**: ch005
- **Related Characters**: 沈轩

## Referenced

## Resolved

## Abandoned
"""

    entries = parse_tracker_entries(text)

    assert entries[0].entry_id == "F001"
    assert entries[0].section == "Active"
    assert entries[0].planned_payoff.start_chapter == 5


def test_parse_tracker_entries_reads_all_sections():
    text = """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 码头血衣的来源
- **Planned Payoff**: ch010-ch015
- **Related Characters**: 沈轩, 阿坤

## Referenced
### F002
- **Referenced**: true

## Resolved
### F003
- **Resolution**: 真相已经揭露

## Abandoned
### F004 | Priority: low
- **Description**: 被废弃的支线
- **Planned Payoff**: ch030+
- **Related Characters**: 雷老板
"""

    entries = parse_tracker_entries(text)

    assert [entry.entry_id for entry in entries] == ["F001", "F002", "F003", "F004"]
    assert entries[0].priority == "high"
    assert entries[0].related_characters == ["沈轩", "阿坤"]
    assert entries[0].planned_payoff.start_chapter == 10
    assert entries[0].planned_payoff.end_chapter == 15
    assert entries[1].section == "Referenced"
    assert entries[1].referenced is True
    assert entries[2].section == "Resolved"
    assert entries[2].resolution == "真相已经揭露"
    assert entries[3].section == "Abandoned"
    assert entries[3].planned_payoff.open_ended is True


def test_parse_tracker_entries_reads_resolved_in_and_abandoned_in():
    text = """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 码头血衣的来源
- **Planned Payoff**: ch005
- **Related Characters**: 沈轩

## Referenced

## Resolved
### F002
- **Resolution**: 真相已经揭露
- **Resolved In**: ch005

## Abandoned
### F003 | Priority: low
- **Description**: 被废弃的支线
- **Planned Payoff**: ch030+
- **Related Characters**: 雷老板
- **Abandoned In**: ch010
"""

    entries = parse_tracker_entries(text)

    assert entries[1].closed_in_chapter == 5
    assert entries[2].closed_in_chapter == 10


def test_parse_tracker_entries_skips_invalid_entry_and_keeps_valid_entries():
    text = """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 合法伏笔
- **Planned Payoff**: ch005
- **Related Characters**: 沈轩

### F002 | Priority: medium
- **Description**: 坏掉的伏笔
- **Planned Payoff**: someday
- **Related Characters**: 阿坤

## Referenced
### F003
- **Referenced**: true

## Resolved

## Abandoned
"""

    entries = parse_tracker_entries(text)

    assert [entry.entry_id for entry in entries] == ["F001", "F003"]


def test_parse_tracker_entries_skips_invalid_header_block_and_keeps_neighbors():
    text = """# Foreshadowing Tracker

## Active
### F001 | Priority: high
- **Description**: 合法伏笔一
- **Planned Payoff**: ch005
- **Related Characters**: 沈轩

### BROKEN
- **Description**: 坏掉的头部
- **Planned Payoff**: ch999

### F003 | Priority: low
- **Description**: 合法伏笔二
- **Planned Payoff**: ch018
- **Related Characters**: 阿坤

## Referenced

## Resolved

## Abandoned
"""

    entries = parse_tracker_entries(text)

    assert [entry.entry_id for entry in entries] == ["F001", "F003"]
    assert entries[0].description == "合法伏笔一"
    assert entries[0].planned_payoff.start_chapter == 5
    assert entries[1].description == "合法伏笔二"
