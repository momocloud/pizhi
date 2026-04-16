from pizhi.adapters.base import PromptRequest
from pizhi.adapters.prompt_only import PromptOnlyAdapter


def test_prompt_only_adapter_writes_prompt_packet(initialized_project):
    adapter = PromptOnlyAdapter(initialized_project)
    request = PromptRequest(
        command_name="write",
        prompt_text="Write chapter 1",
        metadata={"chapter": 1},
        referenced_files=[".pizhi/global/synopsis.md"],
    )

    result = adapter.prepare(request)

    assert result.prompt_path.exists()
    assert result.manifest_path.exists()
    assert "Write chapter 1" in result.prompt_path.read_text(encoding="utf-8")
