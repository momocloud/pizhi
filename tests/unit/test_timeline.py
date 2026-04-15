from pizhi.domain.timeline import append_timeline_events


def test_append_timeline_events_writes_structured_event_blocks():
    current = "# 时间线\n\n"
    events = [
        {
            "at": "1986-03-14 夜",
            "event": "沈轩抵达码头三号仓",
            "is_flashback": False,
            "is_major_turning_point": False,
        }
    ]

    updated = append_timeline_events(current, chapter_number=1, events=events)

    assert "## T001-01" in updated
    assert "沈轩抵达码头三号仓" in updated
