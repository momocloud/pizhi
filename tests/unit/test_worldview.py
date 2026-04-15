from pizhi.domain.worldview import apply_worldview_patch


def test_worldview_patch_modifies_existing_bold_title():
    current = "## 势力\n- **雷老板势力范围**：深水埗至旺角\n"
    patch = "# 第十章世界观变更\n\n## Modified\n- **雷老板势力范围**：深水埗至湾仔\n"

    updated = apply_worldview_patch(current, patch)

    assert "深水埗至湾仔" in updated
