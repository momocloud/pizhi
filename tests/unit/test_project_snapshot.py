from pizhi.services.chapter_writer import apply_chapter_response
from pizhi.services.project_snapshot import load_project_snapshot


def test_load_project_snapshot_for_initialized_project(initialized_project):
    snapshot = load_project_snapshot(initialized_project)

    assert snapshot.project_name == "Test Novel"
    assert snapshot.latest_chapter is None
    assert snapshot.next_chapter == 1
    assert snapshot.chapters == {}


def test_load_project_snapshot_tracks_chapter_artifacts(initialized_project, fixture_text):
    apply_chapter_response(initialized_project, 1, fixture_text("ch001_response.md"))

    snapshot = load_project_snapshot(initialized_project)

    assert snapshot.latest_chapter == 1
    assert snapshot.chapters[1].artifacts.text_exists is True
    assert snapshot.chapters[1].artifacts.meta_exists is True
