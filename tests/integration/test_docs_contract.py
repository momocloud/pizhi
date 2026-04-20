def test_public_docs_surface_excludes_internal_process_docs(project_root):
    assert not (project_root / "docs" / "superpowers").exists()
    assert (project_root / "meta" / "specs").exists()
    assert (project_root / "meta" / "plans").exists()
