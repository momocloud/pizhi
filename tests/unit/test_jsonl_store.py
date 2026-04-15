from pizhi.core.jsonl_store import ChapterIndexStore


def test_chapter_index_store_upserts_record(tmp_path):
    store = ChapterIndexStore(tmp_path / "index.jsonl")

    store.upsert(
        {
            "n": 1,
            "title": "雨夜访客",
            "vol": 1,
            "status": "outlined",
            "summary": "",
            "updated": "2026-04-15",
        }
    )
    store.upsert(
        {
            "n": 1,
            "title": "雨夜访客",
            "vol": 1,
            "status": "drafted",
            "summary": "摘要",
            "updated": "2026-04-16",
        }
    )

    assert store.read_all() == [
        {
            "n": 1,
            "title": "雨夜访客",
            "vol": 1,
            "status": "drafted",
            "summary": "摘要",
            "updated": "2026-04-16",
        }
    ]
