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
